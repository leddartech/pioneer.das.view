from pioneer.common import linalg, clouds
from pioneer.common import platform as platform_utils
from pioneer.common.gui import CustomActors, utils
from pioneer.common.video import VideoRecorder, RecordableInterface
from pioneer.das.api import categories, lane_types, platform
from pioneer.das.api.samples import Echo, XYZIT
from pioneer.das.api.datasources.virtual_datasources import VoxelMap, VirtualDatasource
from pioneer.das.view.windows import Window

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

import copy
import glob
import numpy as np
import os
import pickle
import random
import time


class ViewportWindow(Window, RecordableInterface):

    def __init__(self, window, platform, synchronized, ds_name, video_fps):
        super(ViewportWindow, self).__init__(window, platform)
        self.window.setTitle(ds_name)
        self.synchronized = synchronized
        self.viewport = self.window.viewport
        self.controls = self.window.controls
        self.ds_name = ds_name
        self.video_recorder = VideoRecorder.create(self, ds_name, platform, synchronized, video_fps)

    def on_video_created(self):
        """
        Overrided
        """
        self.viewport.set_render_to_texture_attachment(1)

    def get_frame(self):
        """
        Overrided
        """
        QApplication.processEvents()  # make sure frame is current
        arr = self.viewport.get_render_to_texture_array()
        return arr.ndarray

    def connect(self):

        if self.platform.is_live():
            if not isinstance(self.platform[self.ds_name], VirtualDatasource):
                self.platform[self.ds_name].ds.connect(self._update)
            else:
                self.platform[self.platform[self.ds_name].dependencies[0]].ds.connect(self._update)
        else:
            self.add_connection(self.window.cursorChanged.connect(self._update))

        self.add_connection(self.window.visibleChanged.connect(self._update))
        self.add_connection(self.controls.showActorChanged.connect(self._update))
        self.add_connection(self.controls.showBBox3DChanged.connect(self._update))
        self.add_connection(self.controls.showSeg3DChanged.connect(self._update))
        self.add_connection(self.controls.showLanesChanged.connect(self._update))
        self.add_connection(self.controls.useBoxColorsChanged.connect(self._update))
        self.add_connection(self.controls.boxLabelsSizeChanged.connect(self._update))
        self.add_connection(self.controls.videoChanged.connect(self._update))
        self.add_connection(self.controls.confThresholdChanged.connect(self._update))
        self.add_connection(self.controls.showIoUChanged.connect(self._update))
        self.add_connection(self.controls.categoryFilterChanged.connect(self._update))
        self.add_connection(self.controls.submitVoxelMapMemory.clicked.connect(self._update_voxel_map))
        self.add_connection(self.controls.voxelSizeChanged.connect(self._update_voxel_map))
        self.add_connection(self.controls.amplitudeTypeChanged.connect(self._update_amplitude_type))

        sensor_type, pos, ds_type = platform_utils.parse_datasource_name(self.ds_name)

        if ds_type.startswith('ech'):
            lcax = self.platform[f'{sensor_type}_{pos}']

            # load actual values in UI
            self.controls.distIntervals = [i for sub in lcax.config['dist_reject_intervals'] for i in sub]
            self.controls.ampIntervals = [i for sub in lcax.config['amp_reject_intervals'] for i in sub]

            self.add_connection(self.controls.distIntervalsChanged.connect(self._update_intervals))
            self.add_connection(self.controls.ampIntervalsChanged.connect(self._update_intervals))

        if ds_type.startswith('xyzit-voxmap'):
            # load actual values in UI
            self.controls.voxelMapMemory = str(self.platform[self.ds_name].memory)
            self.controls.voxelMapSkip = str(self.platform[self.ds_name].skip)
            self.controls.voxelSizeText = str(self.platform[self.ds_name].voxel_size)
            self.controls.voxelSize = float(np.log10(self.platform[self.ds_name].voxel_size))

        if 'radarTI_bfc' in self.platform._sensors.keys():
            self.controls.amplitudeTypeVisible = True

        self._update()

    def _update(self):

        cursor = -1 if self.platform.is_live() else int(self.window['cursor'])

        self._ds_name_sample = self.platform[self.ds_name][cursor]

        self._draw_frustrum()

        self._draw_clouds_actors()

        self._draw_sementic_segmentation_actors()

        self._draw_bounding_box_actors()

        self._draw_lane_actors()

        # video feed (must be done last)
        self.video_recorder.record(self.controls.video and self.viewport.renderer is not None)

    def _update_intervals(self):

        sensor_type, pos, ds_type = platform_utils.parse_datasource_name(self.ds_name)

        lcax = self.platform[f'{sensor_type}_{pos}']

        def to_intervals(slices):
            return [[(slices[i * 2]), (slices[i * 2 + 1])] for i in range(len(slices) // 2)]

        lcax.config['dist_reject_intervals'] = to_intervals(self.controls.distIntervals)
        lcax.config['amp_reject_intervals'] = to_intervals(self.controls.ampIntervals)

        lcax[ds_type].invalidate_caches()

        self._update()

    def _update_voxel_map(self):
        for datasource, actor in self.viewport.pclActors.items():
            if not self.controls.showActor[datasource]:
                continue
            if isinstance(self.platform[datasource], VoxelMap):
                self.platform[datasource].clear_cache()
                self.platform[datasource].memory = int(self.window.controls.voxelMapMemory)
                self.platform[datasource].skip = int(self.window.controls.voxelMapSkip)
                vxs = 10 ** float(self.window.controls.voxelSize)
                self.platform[datasource].voxel_size = vxs if vxs > 0.01 else 0
                self.window.controls.voxelSizeText = f'{self.platform[datasource].voxel_size:.2f}'
                self.platform[datasource].invalidate_caches()
        self._update()

    def _update_amplitude_type(self):
        self.platform['radarTI_bfc'].amplitude_type = self.window.controls.amplitudeType
        self._update()

    def _get_sample(self, ds_name):
        if ds_name == self.ds_name:
            return self._ds_name_sample
        else:
            return self.platform[ds_name].get_at_timestamp(self._ds_name_sample.timestamp)

    def _draw_frustrum(self):

        _, _, ds_type = platform_utils.parse_datasource_name(self.ds_name)

        self._ds_name_sample = self._get_sample(self.ds_name)

        if 'ech' in ds_type and not hasattr(self, 'frustrum'):

            lcax = self._ds_name_sample.datasource.sensor
            specs = self._ds_name_sample.specs

            if lcax.angle_chart:
                cache = self._ds_name_sample.cache()
                correct_v_angles = lcax.get_corrected_projection_data(self._ds_name_sample.timestamp, cache, 'angles')

                v_cell_size, h_cell_size = clouds.v_h_cell_size_rad(specs)

                i, v = clouds.frustrum(clouds.custom_frustrum_directions(correct_v_angles, v_cell_size, h_cell_size, dtype=np.float64), 40)
            else:
                i, v = clouds.frustrum(clouds.frustrum_directions(specs['v_fov'], specs['h_fov'], dtype=np.float64))

            if self._ds_name_sample.orientation is not None:
                v = (self._ds_name_sample.orientation @ v.T).T
            frustrum = CustomActors.lines(i, v, color=QColor("lightgray"))
            self.frustrum = self.viewport.actors.addActor(frustrum)

    def _draw_clouds_actors(self):

        # point cloud actors:
        for datasource, actor in self.viewport.pclActors.items():

            if not self.controls.showActor[datasource]:
                continue

            package = actor['packages']
            cloud = actor['cloud']
            sensor = self.platform.sensors[platform_utils.extract_sensor_id(datasource)]
            sensor.extrinsics_dirty.connect(cloud.makeDirty)
            if datasource != self.ds_name:
                ref_sensor = self.platform.sensors[platform_utils.extract_sensor_id(self.ds_name)]
                ref_sensor.extrinsics_dirty.connect(sensor.extrinsics_dirty)

            sample = self._get_sample(datasource)

            cloud.undistortRefTs = int(self._ds_name_sample.timestamp)

            cloud.sample.variant = sample

            if '-rgb' in datasource: #TODO: generalize how colors are obtained from the sample
                data = sample.raw
                colors = np.ones((data.shape[0],4))
                colors[:,0] = data['r']/255
                colors[:,1] = data['g']/255
                colors[:,2] = data['b']/255
                cloud._colors.set_ndarray(colors)

            if isinstance(sample, Echo):
                package.variant = sample.masked  # FIXME: port 2d viewers to das.api too

    def _draw_sementic_segmentation_actors(self):

        # segmentation 3d actors:
        seg_actors = self.viewport.segActors
        for datasource, actor in seg_actors.items():

            if not self.controls.showSeg3D[datasource]:
                continue

            package = actor['packages']
            cloud = actor['cloud']

            ds_name, pos, _ = platform_utils.parse_datasource_name(datasource)

            if f'{ds_name}_{pos}_ech' in self.viewport.pclActors:
                pcl_ds = f'{ds_name}_{pos}_ech'
                cloud.method = 'quad_cloud'

            elif f'{ds_name}_{pos}_xyzit' in self.viewport.pclActors:
                pcl_ds = f'{ds_name}_{pos}_xyzit'
                cloud.method = 'point_cloud'

            elif f'{ds_name}_{pos}_xyzvcfar' in self.viewport.pclActors:
                pcl_ds = f'{ds_name}_{pos}_xyzvcfar'
                cloud.method = 'point_cloud'

            pcl_sample = self._get_sample(pcl_ds)
            seg_sample = self._get_sample(datasource)

            len_seg3d = seg_sample.raw['data'].shape[0]
            len_pcl = pcl_sample.masked['data'].shape[0]
            if len_seg3d != len_pcl:
                print(f'Warning. The length ({len_seg3d}) of the segmentation 3D data'
                      + f'does not match the length ({len_pcl}) of the point cloud.')

            # TODO: categoryFilter is not applied to segmentation3d here

            cloud.undistortRefTs = int(self._ds_name_sample.timestamp)

            cloud.sample.variant = pcl_sample
            cloud.seg3DSample.variant = seg_sample

            if isinstance(pcl_sample, Echo):
                package.variant = pcl_sample.masked

    def _update_cursor(self, cursor, attributes):
        def _update():
            cursor.setProperty('visible', True)
            try:
                occlusion = attributes['occlusions'] 
                truncation = attributes['truncations']
                on_the_road = attributes['on the road']
                vehicle_activity = attributes['vehicle activities']
                human_activity = attributes['human activities']

                cursor.setProperty('occlusion', f'{occlusion}')
                cursor.setProperty('truncation', f'{truncation}')
                cursor.setProperty('onTheRoad', f'{on_the_road}')
                cursor.setProperty('vehicleActivity', f'{vehicle_activity}')
                cursor.setProperty('humanActivity', f'{human_activity}')
            except:
                pass
        
        return _update

    def _draw_bounding_box_actors(self):
        ## Attemp to add Box in Viewer API
        ## WIP to have a better implementation

        for datasource, actors in self.viewport.bboxActors.items():

            actors['actor'].clearActors()
            if not self.controls.showBBox3D[datasource]:
                continue

            sample = self._get_sample(datasource)

            if np.abs(np.int64(self._ds_name_sample.timestamp) - sample.timestamp) <= 1e6:

                _, _, ds_type = platform_utils.parse_datasource_name(datasource)
                box_source = categories.get_source(ds_type)

                raw = sample.raw
                bbox = sample.mapto(self.ds_name, ignore_orientation=True)

                mask = (bbox['flags'] >= 0)

                if 'confidence' in raw:
                    mask = mask & (sample.raw['confidence'] > int(self.controls.confThreshold) / 100.0)

                    if (self.controls.showIoU) and (self.controls.refdsIoU is not ''):
                        scores_iou = sample.compute_iou(box=self._get_sample(self.controls.refdsIoU),
                                                        return_max=True, map2yaw=None)

                if len(bbox[mask]) > 0:
                    for i, box in enumerate(bbox[mask]):

                        c = box['c']
                        d = box['d']
                        r = box['r']

                        has_attributes = 'attributes' in raw
                        if has_attributes:
                            attributes = raw['attributes'][mask][i]

                        name, color = categories.get_name_color(box_source, box['classes'])
                        if self.controls.categoryFilter is not '':
                            if name not in self.controls.categoryFilter:
                                continue
                        color = QColor.fromRgb(*color)
                        text_color = QColor('white')
                        if self.controls.useBoxColors:
                            text_color = color = QColor(self.controls.box3DColors[datasource])

                        if 'confidence' in raw:
                            conf = raw['confidence'][mask][i]
                            name = f'{name}({conf:.3f})'

                            if (self.controls.showIoU) and (self.controls.refdsIoU is not ''):
                                name = f'{name}[IoU={scores_iou[mask][i]:.3f}]'

                        bbox_actor, text_anchor = CustomActors.bbox(c, d, r, color=color, return_anchor=True)
                        bbox_actor.effect.lineWidth = 2

                        if has_attributes:
                            bbox_actor.hovered.connect(self._update_cursor(actors['cursor'], attributes))

                        tf = linalg.tf_from_pos_euler(text_anchor)

                        actors['actor'].addActor(bbox_actor)

                        if self.controls.boxLabelsSize > 0:
                            text_actor = CustomActors.text(name
                                                           , color=text_color
                                                           , origin=[0, 0, 0], v=[0, -1, 0]
                                                           , matrix=utils.from_numpy(tf)
                                                           , scale=0.1
                                                           , font_size=self.controls.boxLabelsSize
                                                           , line_width=3
                                                           , is_billboard=True)

                            actors['actor'].addActor(text_actor)

    def _draw_lane_actors(self):

        # TODO: transform to referential

        for datasource, actors in self.viewport.laneActors.items():
            actors['actor'].clearActors()
            if not self.controls.showLanes[datasource]:
                continue

            sample = self._get_sample(datasource)
            for lane in sample.raw:
                infos = lane_types.LANE_TYPES[lane['type']]
                lane_actor = CustomActors.lane(lane['vertices'], color=QColor.fromRgb(*infos['color']),
                                               double=infos['double'], dashed=infos['dashed'])
                actors['actor'].addActor(lane_actor)
