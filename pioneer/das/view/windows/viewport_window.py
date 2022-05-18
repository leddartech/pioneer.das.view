from pioneer.common import linalg, clouds
from pioneer.common import platform as platform_utils
from pioneer.common.gui import CustomActors, utils
from pioneer.common.video import VideoRecorder, RecordableInterface
from pioneer.das.api import categories, lane_types
from pioneer.das.api.samples import Echo
from pioneer.das.api.samples.annotations.box_3d import Box3d
from pioneer.das.api.samples.point_cloud import PointCloud
from pioneer.das.api.samples.sample import Sample
from pioneer.das.view.windows import Window

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QColor

import numpy as np


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
        """Overrided"""
        self.viewport.set_render_to_texture_attachment(1)

    def get_frame(self):
        """Overrided"""
        QApplication.processEvents()  # make sure frame is current
        arr = self.viewport.get_render_to_texture_array()
        return arr.ndarray

    def connect(self):

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
        self.add_connection(self.controls.categoryFilterChanged.connect(self._update))

        self._update()

    def _update(self):

        cursor = int(self.window['cursor'])

        self.sample:Sample = self.platform[self.ds_name][cursor]

        self._draw_frustrum()
        self._draw_clouds_actors()
        self._draw_sementic_segmentation_actors()
        self._draw_bounding_box_actors()
        self._draw_lane_actors()

        # video feed (must be done last)
        self.video_recorder.record(self.controls.video and self.viewport.renderer is not None)

    def _get_sample(self, ds_name):
        if ds_name == self.ds_name:
            return self.sample
        else:
            return self.platform[ds_name].get_at_timestamp(self.sample.timestamp)

    def _draw_frustrum(self):

        _, _, ds_type = platform_utils.parse_datasource_name(self.ds_name)

        self.sample = self._get_sample(self.ds_name)

        if 'ech' in ds_type and not hasattr(self, 'frustrum'):

            lcax = self.sample.datasource.sensor
            specs = self.sample.specs

            if lcax.angle_chart:
                cache = self.sample.cache()
                correct_v_angles = lcax.get_corrected_projection_data(self.sample.timestamp, cache, 'angles')

                v_cell_size, h_cell_size = clouds.v_h_cell_size_rad(specs)

                i, v = clouds.frustrum(clouds.custom_frustrum_directions(correct_v_angles, v_cell_size, h_cell_size, dtype=np.float64), 40)
            else:
                i, v = clouds.frustrum(clouds.frustrum_directions(specs['v_fov'], specs['h_fov'], dtype=np.float64))

            if self.sample.orientation is not None:
                v = (self.sample.orientation @ v.T).T
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

            sample:PointCloud = self._get_sample(datasource)

            cloud.undistortRefTs = int(self.sample.timestamp)

            cloud.sample.variant = sample

            if '-rgb' in datasource: #TODO: generalize how colors are obtained from the sample
                colors = np.ones((sample.size,4))
                colors[:,0] = sample.get_field('r')/255
                colors[:,1] = sample.get_field('g')/255
                colors[:,2] = sample.get_field('b')/255
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
                cloud.method = 'get_point_cloud'

            elif f'{ds_name}_{pos}_xyzvcfar' in self.viewport.pclActors:
                pcl_ds = f'{ds_name}_{pos}_xyzvcfar'
                cloud.method = 'get_point_cloud'
            elif f'{ds_name}_{pos}_xyzvi' in self.viewport.pclActors:
                pcl_ds = f'{ds_name}_{pos}_xyzvi'
                cloud.method = 'get_point_cloud'

            pcl_sample = self._get_sample(pcl_ds)
            seg_sample = self._get_sample(datasource)

            len_seg3d = seg_sample.raw['data'].shape[0]
            len_pcl = pcl_sample.masked['data'].shape[0]
            if len_seg3d != len_pcl:
                print(f'Warning. The length ({len_seg3d}) of the segmentation 3D data'
                      + f'does not match the length ({len_pcl}) of the point cloud.')

            # TODO: categoryFilter is not applied to segmentation3d here

            cloud.undistortRefTs = int(self.sample.timestamp)

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

        for ds_name, actors in self.viewport.bboxActors.items():
            actors['actor'].clearActors()
            if not self.controls.showBBox3D[ds_name]: continue

            box_source = categories.get_source(platform_utils.parse_datasource_name(ds_name)[2])
            box3d_sample:Box3d = self.platform[ds_name].get_at_timestamp(self.sample.timestamp)
            if np.abs(float(box3d_sample.timestamp) - float(self.sample.timestamp)) > 1e6: continue
            box3d = box3d_sample.set_referential(self.ds_name, ignore_orientation=True)
            category_numbers = box3d.get_category_numbers()

            for box_index in range(len(box3d)):

                center = box3d.get_centers()[box_index]
                dimension = box3d.get_dimensions()[box_index]
                rotation = box3d.get_rotations()[box_index]
                confidence = box3d.get_confidences()[box_index]
                category_name, color = categories.get_name_color(box_source, category_numbers[box_index])
                id = box3d.get_ids()[box_index]

                if confidence:
                    if confidence < int(self.controls.confThreshold) / 100.0: continue

                if self.controls.categoryFilter is not '':
                    if category_name not in self.controls.categoryFilter: continue

                color = QColor.fromRgb(*color)
                text_color = QColor('white')
                if self.controls.useBoxColors:
                    text_color = color = QColor(self.controls.box3DColors[ds_name])

                bbox_actor, text_anchor = CustomActors.bbox(center, dimension, rotation, color=color, return_anchor=True)
                bbox_actor.effect.lineWidth = 2

                tf = linalg.tf_from_pos_euler(text_anchor)

                actors['actor'].addActor(bbox_actor)

                if self.controls.boxLabelsSize > 0:
                    text_label = category_name
                    if id: text_label += f" {id}"
                    if confidence: text_label += f" ({int(confidence)}%)"
                    text_actor = CustomActors.text(text_label,
                        color=text_color,
                        origin=[0, 0, 0], v=[0, -1, 0],
                        matrix=utils.from_numpy(tf),
                        scale=0.1,
                        font_size=self.controls.boxLabelsSize,
                        line_width=3,
                        is_billboard=True,
                    )

                    actors['actor'].addActor(text_actor)


    def _draw_lane_actors(self):

        for datasource, actors in self.viewport.laneActors.items():
            actors['actor'].clearActors()
            if not self.controls.showLanes[datasource]:
                continue

            sample = self._get_sample(datasource)

            for lane in sample.raw['data']:
                infos = lane_types.LANE_TYPES[lane['type']]
                vertices = sample.transform(lane['vertices'], self.ds_name)
                lane_actor = CustomActors.lane(vertices, color=QColor.fromRgb(*infos['color']),
                                               double=infos['double'], dashed=infos['dashed'])
                actors['actor'].addActor(lane_actor)
