from pioneer.common import linalg
from pioneer.common.logging_manager import LoggingManager
from pioneer.common import icp_method as icp
from pioneer.das.view.windows import Window

from enum import Enum
from PyQt5.QtQml import QQmlComponent, QQmlProperty, QQmlEngine
from tqdm import tqdm

import copy
import glob
import numpy as np
import os
import pickle
import random
import time

class CalibMode(Enum):
    RELATIVE = 0
    ABSOLUTE = 1

class ICPMode(Enum):
    Point = 0
    Plane = 1

class CalibWindow(Window):
    def __init__(self, window, platform):
        super(CalibWindow, self).__init__(window, platform)
        self.window.sourceComboBox.model = list([sensor_name for sensor_name,targets in self.platform.extrinsics.items() if len(targets) > 0])
        self.window.sourceComboBox.currentIndex = 0
        self.window.calibmodeComboBox.model = list([mu.name for mu in CalibMode])
        self.window.calibmodeComboBox.currentIndex = 0
        self.window.icp.modeComboBox.model = list([mu.name for mu in ICPMode])
        self.window.icp.modeComboBox.currentIndex = 0
        self.src_sensor = None
        self.dst_sensor = None
        self.handle_src_changed()

    def get_current_pose(self):
        return self.window.pose.pose

    def set_current_pose(self, pose_):
        self.window.pose.px = float(pose_['x'])
        self.window.pose.py = float(pose_['y'])
        self.window.pose.pz = float(pose_['z'])
        self.window.pose.rx = float(pose_['rx'])
        self.window.pose.ry = float(pose_['ry'])
        self.window.pose.rz = float(pose_['rz'])

    def pose_to_tr_matrix(self, pose):
        return linalg.tf_from_pos_euler([pose['x'], pose['y'], pose['z']],
                                        [pose['rx'], pose['ry'], pose['rz']])

    def tr_matrix_to_pose(self, tf):
        px_, py_, pz_, rx_, ry_, rz_ = linalg.pos_euler_from_tf(tf)
        return dict(x=px_, y=py_, z=pz_, rx=rx_, ry=ry_, rz=rz_)

    def handle_pose_changed(self):
        pose_ = self.get_current_pose()
        m = self.pose_to_tr_matrix(pose_)
        self.apply_new_extrinsic(m)

    def apply_new_extrinsic(self, tr):
        ''' tr : 4x4 transformation matrix
        '''
        if not self.does_path_exist(False):
            return

        calibmode_ = self.window.calibmodeComboBox.currentIndex
        if calibmode_ == CalibMode.RELATIVE.value:
            orig = self.src_sensor.orig_extrinsics[self.dst_sensor.name]
            adjusted = self.src_sensor.extrinsics[self.dst_sensor.name][...] = orig @ tr
            self.dst_sensor.extrinsics[self.src_sensor.name][...] = linalg.tf_inv(adjusted)
        elif calibmode_ == CalibMode.ABSOLUTE.value:
            self.src_sensor.extrinsics[self.dst_sensor.name][...] = tr
            self.dst_sensor.extrinsics[self.src_sensor.name][...] = linalg.tf_inv(tr)
        self.src_sensor.extrinsics_dirty()
        self.dst_sensor.extrinsics_dirty()

    def handle_save(self):
        n_saved = 0
        ts = int(time.time())
        for (src_sensor, target) in self.platform.extrinsics.items():
            extrinsics_folder_path = self.platform.try_absolute_or_relative(self.platform.yml[src_sensor]['extrinsics'])
            for (dst_sensor, matrix) in target.items():
                # try to find self.name -> target mapping

                matrix_name = f"{src_sensor}-{dst_sensor}.pkl"
                path = os.path.join(extrinsics_folder_path, matrix_name)
                old_dir = os.path.join(extrinsics_folder_path, f"old_{ts}")

                if os.path.exists(path):
                    if not os.path.isdir(old_dir):
                        os.mkdir(old_dir)
                    os.rename(path, os.path.join(old_dir, f"{src_sensor}-{dst_sensor}.pkl"))
                    with open(path, 'wb') as f:
                        print(f"saving matrix {matrix_name} to directory {extrinsics_folder_path}")
                        pickle.dump(matrix.astype('f8'), f)

                    n_saved += 1

        print(f"Saved {n_saved} extrinsics matrices")

    def handle_src_changed(self):
        sensor_name = self.window.sourceComboBox.textAt(self.window.sourceComboBox.currentIndex)
        if sensor_name in self.platform.sensors:
            self.src_sensor = self.platform.sensors[sensor_name]
            self.window.destinationComboBox.model = [k for k in self.src_sensor.extrinsics.keys() if k != sensor_name]
            self.handle_dst_changed()

    def handle_dst_changed(self):
        sensor_name = self.window.destinationComboBox.textAt(self.window.destinationComboBox.currentIndex)
        if sensor_name in self.platform.sensors:
            self.dst_sensor = self.platform.sensors[sensor_name]

        self.cache_origin_extrinsics()
        self.handle_reset()

    def cache_origin_extrinsics(self):
        if not self.does_path_exist():
            return
        if self.src_sensor is not None and not hasattr(self.src_sensor, "orig_extrinsics"):
            self.src_sensor.orig_extrinsics = copy.deepcopy(self.src_sensor.extrinsics)
        if self.dst_sensor is not None and not hasattr(self.dst_sensor, "orig_extrinsics"):
            self.dst_sensor.orig_extrinsics = copy.deepcopy(self.dst_sensor.extrinsics)

    def does_path_exist(self, silent=True):
        exists = self.src_sensor is not None and self.dst_sensor is not None
        if not exists and not silent:
            LoggingManager.instance().warning(f"Undefined extrinsics path: {'undefined sensor' if self.src_sensor is None else self.src_sensor.name} -> \
                {'undefined sensor' if self.dst_sensor is None else self.dst_sensor.name}")
        return exists

    def handle_reset(self):
        calibmode_ = self.window.calibmodeComboBox.currentIndex
        pose_ = self.tr_matrix_to_pose(np.eye(4))
        if calibmode_ == CalibMode.ABSOLUTE.value:
            if self.does_path_exist(False):
                tf_origin = self.src_sensor.orig_extrinsics[self.dst_sensor.name]
                pose_ = self.tr_matrix_to_pose(tf_origin)

        self.set_current_pose(pose_)

    def handle_runicp(self):
        if not self.does_path_exist(False):
            return

        if self.src_sensor.pcl_datasource is None or self.dst_sensor.pcl_datasource is None:
            print(f"Can not compute icp between {self.src_sensor.name} and {self.dst_sensor.name}")
        else:
            src_datasource = self.platform[self.src_sensor.name][self.src_sensor.pcl_datasource]
            dst_datasource = self.platform[self.dst_sensor.name][self.dst_sensor.pcl_datasource]
            max_correspondence_distance = float(self.window.icp.correspDistMax)
            method = ICPMode(self.window.icp.modeComboBox.currentIndex).name
            max_iteration = int(self.window.icp.nbIterMax)
            init_matrix = self.src_sensor.extrinsics[self.dst_sensor.name][...]

            if self.window.icp.allFrames.checked:
                print('Computing ICP on all frames of this dataset...')
                frame = 0
                rotation_quat = icp.Quaternion()
                translation = [0.0,0.0,0.0]
                for src_sample in tqdm(src_datasource):
                    dst_sample = dst_datasource.get_at_timestamp(src_sample.timestamp)
                    pts_src = src_sample.point_cloud()
                    pts_dst = dst_sample.point_cloud()
                    frame += 1
                    quater, transla,_ = icp.icp_routine(pts_src, 
                                                        pts_dst, 
                                                        init_matrix, 
                                                        frame, 
                                                        None, 
                                                        None,
                                                        max_correspondence_distance, 
                                                        method, 
                                                        max_iteration)
                    rotation_quat += quater
                    translation += transla

                tf = np.eye(4)
                tf[:3,:3] = icp.quaternion_R(rotation_quat/frame)
                tf[:3,3] = translation/frame
            else:
                frame_no = int(self.window.icp.sourceFrameNo)
                src_sample = src_datasource[frame_no]
                dst_sample = dst_datasource.get_at_timestamp(src_sample.timestamp)
                pts_src = src_sample.point_cloud()
                pts_dst = dst_sample.point_cloud()
                tf, _ = icp.icp(pts_src,
                                    pts_dst,
                                    init_matrix,
                                    max_correspondence_distance,
                                    method,
                                    max_iteration)

            pose = self.tr_matrix_to_pose(tf)
            self.show_result_icp(pose)

    def show_result_icp(self, pose):
        txt = "{:.4f}"
        self.window.icp.resultx = txt.format(pose['x'])
        self.window.icp.resulty = txt.format(pose['y'])
        self.window.icp.resultz = txt.format(pose['z'])
        self.window.icp.resultrx = txt.format(pose['rx'])
        self.window.icp.resultry = txt.format(pose['ry'])
        self.window.icp.resultrz = txt.format(pose['rz'])

    def get_result_icp(self):
        return dict(x=float(self.window.icp.resultx),
                        y=float(self.window.icp.resulty),
                        z=float(self.window.icp.resultz),
                        rx=float(self.window.icp.resultrx),
                        ry=float(self.window.icp.resultry),
                        rz=float(self.window.icp.resultrz))

    def handle_applyicp(self):
        pose = self.get_result_icp()
        self.set_current_pose(pose)
        self.window.calibmodeComboBox.currentIndex = CalibMode.ABSOLUTE.value
        self.handle_pose_changed()

    def connect(self):
        self.add_connection(self.window.pose.poseChanged.connect(self.handle_pose_changed))
        self.add_connection(self.window.save.clicked.connect(self.handle_save))
        self.add_connection(self.window.reset.clicked.connect(self.handle_reset))
        self.add_connection(self.window.sourceComboBox.currentIndexChanged.connect(self.handle_src_changed))
        self.add_connection(self.window.destinationComboBox.currentIndexChanged.connect(self.handle_dst_changed))
        self.add_connection(self.window.calibmodeComboBox.currentIndexChanged.connect(self.handle_reset))
        self.add_connection(self.window.icp.runicp.clicked.connect(self.handle_runicp))
        self.add_connection(self.window.icp.applyicp.clicked.connect(self.handle_applyicp))

