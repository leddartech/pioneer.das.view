from pioneer.common import linalg
from pioneer.common.platform import parse_datasource_name
from pioneer.common.gui import utils
from pioneer.common.video import VideoRecorder, RecordableInterface
from pioneer.das.api import categories, lane_types
from pioneer.das.api.samples import Echo
from pioneer.das.api.samples.annotations.box_2d import Box2d
from pioneer.das.api.samples.annotations.box_3d import Box3d
from pioneer.das.api.samples.image import Image
from pioneer.das.api.samples.point_cloud import PointCloud
from pioneer.das.api.sensors import Sensor
from pioneer.das.view.windows import Window

from matplotlib.patches import Rectangle, Polygon
from matplotlib.collections import PolyCollection
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QColor
from PyQt5.QtQml import QQmlProperty

import matplotlib
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import numpy as np



class ImagerWindow(Window, RecordableInterface):
    def __init__(self, window, platform, synchronized, datasource, video_fps):
        super(ImagerWindow, self).__init__(window, platform)

        self.synchronized = synchronized
        self.datasource = datasource
        self.backend = self.window.findChild(QObject, "figure")
        self.ax = self.backend.getFigure().add_subplot(111)
        self.image = None
        self.scatter = None
        self.video_recorder = VideoRecorder.create(self, datasource, platform, synchronized, video_fps)

    def get_frame(self):
        """Override"""
        width, height = self.backend.getFigure().get_size_inches() * self.backend.getFigure().get_dpi()
        return np.fromstring(self.backend.tostring_rgb(), dtype='uint8').reshape(int(height),int(width),3)

    def connect(self):

        self.add_connection(self.window.cursorChanged.connect(self.update))
        self.add_connection(self.window.visibleChanged.connect(self.update))

        controls = self.window.controls

        self.add_connection(controls.undistortChanged.connect(self.update))
        self.add_connection(controls.undistortimageChanged.connect(self.update))
        self.add_connection(controls.showActorChanged.connect(self.update))
        self.add_connection(controls.pointSizeChanged.connect(self.update))
        self.add_connection(controls.useColorsChanged.connect(self.update))
        self.add_connection(controls.useBoxColorsChanged.connect(self.update))
        self.add_connection(controls.boxLabelsSizeChanged.connect(self.update))
        self.add_connection(controls.logScaleChanged.connect(self.update))
        self.add_connection(controls.showBBox2DChanged.connect(self.update))
        self.add_connection(controls.showSeg2DChanged.connect(self.update))
        self.add_connection(controls.showBBox3DChanged.connect(self.update))
        self.add_connection(controls.showSeg3DChanged.connect(self.update))
        self.add_connection(controls.showLanesChanged.connect(self.update))
        self.add_connection(controls.confThresholdChanged.connect(self.update))
        self.add_connection(controls.videoChanged.connect(self.update))
        self.add_connection(controls.categoryFilterChanged.connect(self.update))
        self.add_connection(controls.aspectRatioChanged.connect(self.update_aspect_ratio))
        self.add_connection(controls.cropLeftChanged.connect(self.update_aspect_ratio))
        self.add_connection(controls.cropRightChanged.connect(self.update_aspect_ratio))
        self.add_connection(controls.cropTopChanged.connect(self.update_aspect_ratio))
        self.add_connection(controls.cropBottomChanged.connect(self.update_aspect_ratio))

        self.update()

    def update(self):
        if not self.window.isVisible(): return

        self.__read_qml_properties()

        cursor = int(self.cursor)

        sample:Image = self.platform[self.datasource][cursor]
        image = sample.get_image(undistort = self.undistortimage)

        self.__update_actors(sample, image)
        self.__update_box2D(sample, image)
        self.__update_seg_2d(sample, image)
        self.__update_bbox_3d(sample)
        self.__update_lanes(sample, image)

        self.__draw(image)
        self.video_recorder.record(self.is_recording)

    def update_aspect_ratio(self):
        im = self.ax.get_images()
        extent =  im[0].get_extent()
        self.ax.set_aspect(abs((extent[1]-extent[0])/(extent[3]-extent[2]))/self.aspect_ratio)
        self.update()

    
    #===============================================================================
    # Private methods
    # ==============================================================================
    def __get_datasource_to_show_seg3d(self, datasource_name):
        sensor_name, pos, ds_type = parse_datasource_name(datasource_name)
        if f'{sensor_name}_{pos}_ech' in self.show_actor:
            return f'{sensor_name}_{pos}_ech'
        
        if f'{sensor_name}_{pos}_xyzit' in self.show_actor:
            return f'{sensor_name}_{pos}_xyzit'

        #TODO: Edge case, handle this better
        raise Exception('It is impossible to show 3d segmentation if there is not an echo or xyzit datasource in dataset')


    def __get_sample(self, sample, datasource_name):
        if self.synchronized_cursor == self.cursor and self.player_cursor != -1:
            return self.synchronized[self.player_cursor][datasource_name]  
        else:
            return self.platform[datasource_name].get_at_timestamp(sample.timestamp)

    def __filter_indices(self, points_mask, indices):
        if indices.ndim == 2:
            points_mask = np.all(points_mask[indices], axis=1)
        return indices[points_mask]

    def __update_actors(self, sample, image):
        datasources = [ds_name for ds_name, show in dict(self.show_actor, **dict(self.show_seg_3d)).items() if show]

        all_points2D = dict()
        all_colors = dict()
        all_indices = dict()
        for datasource_name in datasources:

            is_seg3D = datasource_name in self.show_seg_3d
            output_ds_name = datasource_name
            if is_seg3D:
                output_ds_name = datasource_name
                datasource_name = self.__get_datasource_to_show_seg3d(datasource_name)

            cloud_sample = self.__get_sample(sample, datasource_name)

            try:

                if isinstance(cloud_sample, PointCloud):

                    points = cloud_sample.get_point_cloud(referential = self.datasource, undistort = self.undistort, reference_ts = int(sample.timestamp), dtype=np.float64)
                    amplitudes = cloud_sample.get_field('i')

                    # FIXME: dirty hack to get a valid field from a PointCloud without 'i' in its fields (radars)
                    if amplitudes is None:
                        amplitudes = np.clip(cloud_sample.get_field(cloud_sample.fields[3]), 0.01, np.inf)

                    indices = np.arange(cloud_sample.size)

                elif isinstance(cloud_sample, Echo):
                    points, amplitudes, indices = cloud_sample.get_cloud(referential = self.datasource, undistort = self.undistort, reference_ts = int(sample.timestamp), dtype=np.float64)           

            except Sensor.NoPathToReferential as e:
                self.has_referential[datasource_name]['hasReferential'] = False
                continue
            
            if points.size == 0:
                continue
            
            self.has_referential[datasource_name]['hasReferential'] = True

            pts2d, points_mask = sample.project_pts(points, mask_fov=False, output_mask=True, undistorted=self.undistortimage)
            all_points2D[output_ds_name] = pts2d

            if is_seg3D:
                seg_sample = self.platform[output_ds_name].get_at_timestamp(cloud_sample.timestamp)
                mode = 'quad_cloud' if isinstance(cloud_sample, Echo) else None
                seg_colors = seg_sample.colors(mode=mode)
                if seg_colors.shape[0] != points.shape[0]:
                    print(f'Warning. The length ({seg_colors.shape[0]}) of the segmentation 3D data' \
                            +f'does not match the length ({points.shape[0]}) of the point cloud.')
                    continue
                all_colors[output_ds_name] = seg_colors

                if self.category_filter is not '':
                    points_mask &= seg_sample.mask_category(self.category_filter)
                
            elif '-rgb' in datasource_name: #TODO: generalize how colors are obtained from the sample
                rgb_colors = np.ones((cloud_sample.size,4))
                rgb_colors[:,0] = cloud_sample.get_field('r')/255
                rgb_colors[:,1] = cloud_sample.get_field('g')/255
                rgb_colors[:,2] = cloud_sample.get_field('b')/255
                all_colors[output_ds_name] = rgb_colors

            else:   
                a_min, a_max = amplitudes.min(), amplitudes.max()
                if self.log_scale:
                    norm = matplotlib.colors.LogNorm(1 + a_min, 1 + a_min + a_max)
                else:
                    norm = matplotlib.colors.Normalize(amplitudes.min(), amplitudes.max())
                
                if self.use_colors:
                    c = np.full((points.shape[0], 4), utils.to_numpy(QColor(self.ds_colors[datasource_name])))
                    c[:,3] = (0.25 + norm(amplitudes + ((1 + a_min) if self.log_scale else 0)))/1.25 #to make sure every point is visible
                    all_colors[output_ds_name] = c
                else:
                    all_colors[output_ds_name] = norm(amplitudes)

            all_indices[output_ds_name] = self.__filter_indices(points_mask, indices)



        self.window.hasReferential = self.has_referential
        self.__clean_plot_canvas()

        for ds_name, indices in all_indices.items():
            points2d = all_points2D[ds_name][indices]
            colors = np.squeeze(all_colors[ds_name][indices[:,0] if indices.ndim>1 else indices]) #all colors are the same in a given triangle
 
            if indices.ndim == 2:
                if colors.ndim == 1:
                    poly_coll = PolyCollection(points2d, array=colors, cmap=plt.cm.viridis, edgecolors=None, alpha=0.7)
                else:
                    poly_coll = PolyCollection(points2d, facecolors=colors, edgecolors=None, alpha=0.7)
                self.ax.add_collection(poly_coll)
                self.ax.figure.canvas.draw()
            else:
                self.scatter = self.ax.scatter(points2d[:, 0], points2d[:, 1], s=self.point_size, c=colors)

        # try: #remove all previous 2D and 3D boxes
        [p.remove() for p in reversed(self.ax.collections)]
        [p.remove() for p in reversed(self.ax.patches)]
        [p.remove() for p in reversed(self.ax.texts)]


    def __update_box2D(self, sample, image):

        for ds_name, show in self.show_bbox_2d.items():
            if not show: continue

            box_source = categories.get_source(parse_datasource_name(ds_name)[2])
            box2d:Box2d = self.platform[ds_name].get_at_timestamp(sample.timestamp)
            if np.abs(float(box2d.timestamp) - float(sample.timestamp)) > 1e6: continue
            category_numbers = box2d.get_category_numbers()

            for box_index in range(len(box2d)):

                center = box2d.get_centers()[box_index]
                dimension = box2d.get_dimensions()[box_index]
                confidence = box2d.get_confidences()[box_index]
                category_name, color = categories.get_name_color(box_source, category_numbers[box_index])
                id = box2d.get_ids()[box_index]

                if confidence:
                    if confidence < self.conf_threshold: continue

                if self.category_filter is not '': 
                    if category_name not in self.category_filter: continue

                color = np.array(color)/255
                if self.use_box_colors:
                    color = utils.to_numpy(QColor(self.box_3d_colors[ds_name]))[:3]

                top = (center[0]-dimension[0]/2)*image.shape[0]
                left = (center[1]-dimension[1]/2)*image.shape[1]

                rect = Rectangle((left,top), dimension[1]*image.shape[1], dimension[0]*image.shape[0], linewidth=1, edgecolor=color, facecolor=list(color)+[0.15]) 
                self.ax.add_patch(rect)

                if self.box_labels_size > 0:
                    text_label = category_name
                    if id: text_label += f" {id}"
                    if confidence: text_label += f" ({int(confidence*100)}%)"
                    txt = self.ax.text(left, top, text_label, color='w', fontweight='bold', fontsize=self.box_labels_size, clip_on=True)
                    txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='k')])


    def __update_seg_2d(self, sample, image):
        datasources = [ds_name for ds_name, show in self.show_seg_2d.items() if show]
        for ds_name in datasources:
            seg_sample = self.platform[ds_name].get_at_timestamp(sample.timestamp)
            _, _, ds_type = parse_datasource_name(ds_name)
            annotation_source = categories.get_source(ds_type)
            if np.abs(np.int64(sample.timestamp) - seg_sample.timestamp) <= 1e6:
                if 'poly2d' in ds_name:
                    raw = seg_sample.raw
                    poly2d = raw['data']
                    if 'confidence' in raw:
                        mask = raw['confidence'] > self.conf_threshold
                        poly2d = poly2d[mask]
                elif 'seg2d' in ds_name:
                    poly2d = seg_sample.poly2d(self.conf_threshold)
                for poly in poly2d:
                    name, color = categories.get_name_color(annotation_source, poly['classes'])
                    if self.category_filter is not '':
                        if name not in self.category_filter:
                            break
                    color = np.array(color)/255
                    patch = Polygon(poly['polygon'], closed=True,linewidth=1,edgecolor=color,facecolor=list(color)+[0.15])
                    self.ax.add_patch(patch)


    def __update_bbox_3d(self, sample:Image):

        for ds_name, show in self.show_bbox_3d.items():
            if not show: continue

            box_source = categories.get_source(parse_datasource_name(ds_name)[2])
            box3d_sample:Box3d = self.platform[ds_name].get_at_timestamp(sample.timestamp)
            if np.abs(float(box3d_sample.timestamp) - float(sample.timestamp)) > 1e6: continue
            box3d = box3d_sample.set_referential(self.datasource, ignore_orientation=True)
            category_numbers = box3d.get_category_numbers()

            poly_collection = []
            color_collection = []

            for box_index in range(len(box3d)):

                center = box3d.get_centers()[box_index]
                dimension = box3d.get_dimensions()[box_index]
                rotation = box3d.get_rotations()[box_index]
                confidence = box3d.get_confidences()[box_index]
                category_name, color = categories.get_name_color(box_source, category_numbers[box_index])
                id = box3d.get_ids()[box_index]

                if confidence:
                    if confidence < self.conf_threshold: continue

                if self.category_filter is not '': 
                    if category_name not in self.category_filter: continue

                color = np.array(color)/255
                if self.use_box_colors:
                    color = utils.to_numpy(QColor(self.box_3d_colors[ds_name]))[:3]

                vertices = linalg.bbox_to_8coordinates(center, dimension, rotation)
                p, mask_fov = sample.project_pts(vertices, mask_fov=False, output_mask=True, undistorted=self.undistortimage, margin=1000)
                if p[mask_fov].shape[0] < 8: continue

                faces = [[0,1,3,2],[0,1,5,4],[0,2,6,4],[7,3,1,5],[7,5,4,6],[7,6,2,3]]
                for face in faces:
                    poly = np.vstack([p[face[0]],p[face[1]],p[face[2]],p[face[3]],p[face[0]]])
                    poly_collection.append(poly)
                    color_collection.append(color)

                if self.box_labels_size > 0:
                    text_label = category_name
                    if id: text_label += f" {id}"
                    if confidence: text_label += f" ({int(confidence*100)}%)"
                    txt = self.ax.text(p[:,0].min(),p[:,1].min(), text_label, color='w', fontweight='bold', fontsize=self.box_labels_size, clip_on=True)
                    txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='k')])

            alpha = 0.05
            facecolors = [list(c)+[alpha] for c in color_collection]
            poly_collection = PolyCollection(poly_collection, linewidths=0.5, edgecolors=color_collection, facecolors=facecolors)
            self.ax.add_collection(poly_collection)


    def __update_lanes(self, sample, image):

        # Remove all previous lines
        [p.remove() for p in reversed(self.ax.lines)]

        datasources = [ds_name for ds_name, show in self.show_lanes.items() if show]
        for ds_name in datasources:
            lane_sample = self.platform[ds_name].get_at_timestamp(sample.timestamp)

            for lane in lane_sample.raw['data']:

                vertices = lane_sample.transform(lane['vertices'], self.datasource, ignore_orientation=True)
                projected_lane = sample.project_pts(vertices, undistorted=self.undistortimage, mask_fov=True, margin=300) 
                
                infos = lane_types.LANE_TYPES[lane['type']]

                color = np.array(infos['color'])/255

                width = 1
                offset = width if infos['double'] else 0
                nb_lanes = 2 if infos['double'] else 1

                for n in range(nb_lanes):

                    ddashed = infos['dashed'][n] if infos['double'] else infos['dashed']
                    ls = '--' if ddashed else '-'
                    
                    self.ax.plot(projected_lane[:,0]-offset, projected_lane[:,1], c=color, lw=width, ls=ls)

                    offset *= -1


    def __clean_plot_canvas(self):
        #TODO: Extract to function
                # if using colors, set_array does not work, it expects a 1D array, probably indexing an hidden color map
                # so we better throw away existing scatter and start over...
        if self.scatter is not None:
            self.scatter.set_offsets(np.empty((0,2), 'f4'))
            self.scatter.set_array(np.empty((0,), 'f4'))
            self.scatter.set_sizes(np.empty((0,), 'f4'))
            self.scatter = None
        for collection in self.ax.collections:
            self.ax.collections.remove(collection)


    def __draw(self, image):

        self.crops = self.__assert_crop_values(image)
        image_cropped = image[self.crops[2]:image.shape[0]-self.crops[3],self.crops[0]:image.shape[1]-self.crops[1]]

        if self.image is None:
            self.image = self.ax.imshow(image_cropped, aspect=self.aspect_ratio)
            self.ax.spines["top"].set_visible(False)
            self.ax.spines["right"].set_visible(False)
            self.ax.spines["bottom"].set_visible(False)
            self.ax.spines["left"].set_visible(False)
        else:
            self.image.set_data(image_cropped)

        self.image.set_extent([self.crops[0],image.shape[1]-self.crops[1],image.shape[0]-self.crops[3],self.crops[2]])

        self.backend.draw()


    def __assert_crop_values(self, image):
        crops = []
        for crop in self.crops:
            try:
                crop = int(crop)
                assert crop > 0
            except:
                crop = 0
            crops.append(crop)
        crops[0] = np.clip(crops[0], 0, int(image.shape[1]/2))
        crops[1] = np.clip(crops[1], 0, int(image.shape[1]/2))
        crops[2] = np.clip(crops[2], 0, int(image.shape[0]/2))
        crops[3] = np.clip(crops[3], 0, int(image.shape[0]/2))
        return crops



    def __read_qml_properties(self):
        controls = self.window.controls

        self.cursor                = int(QQmlProperty.read(self.window.qobject, "cursor"))
        self.synchronized_cursor   = int(self.window.synchronizedCursor)
        self.player_cursor         = int(self.window.playerCursor)

        self.show_actor            =        controls.showActor
        self.show_bbox_2d          =        controls.showBBox2D
        self.show_seg_2d           =        controls.showSeg2D
        self.show_bbox_3d          =        controls.showBBox3D
        self.show_seg_3d           =        controls.showSeg3D
        self.show_lanes            =        controls.showLanes
        self.conf_threshold        = int(   controls.confThreshold)/100.0
        self.undistort             = bool(  controls.undistort)
        self.undistortimage        = bool(  controls.undistortimage)
        self.has_referential       =        controls.hasReferential
        self.point_size            = int(   controls.pointSize)
        self.use_colors            = bool(  controls.useColors)
        self.use_box_colors        = bool(  controls.useBoxColors)
        self.box_labels_size       = int(   controls.boxLabelsSize)
        self.ds_colors             =        controls.dsColors
        self.box_2d_colors         =        controls.box2DColors
        self.box_3d_colors         =        controls.box3DColors
        self.log_scale             = bool(  controls.logScale)
        self.is_recording          = bool(  controls.video)
        self.category_filter       = str(   controls.categoryFilter)
        self.aspect_ratio          = float( controls.aspectRatio)
        self.crops                 =       [controls.cropLeft, 
                                            controls.cropRight, 
                                            controls.cropTop, 
                                            controls.cropBottom]
    