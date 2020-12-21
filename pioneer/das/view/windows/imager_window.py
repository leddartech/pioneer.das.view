from pioneer.common import linalg
from pioneer.common.platform import parse_datasource_name
from pioneer.common.gui import utils
from pioneer.common.video import VideoRecorder, RecordableInterface
from pioneer.das.api import categories, lane_types
from pioneer.das.api.platform import Platform
from pioneer.das.api.samples import ImageFisheye, ImageCylinder, Echo
from pioneer.das.api.sensors import Sensor
from pioneer.das.api.datasources.virtual_datasources.voxel_map import VoxelMap
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

        if self.platform.is_live():
            self.platform[self.datasource].ds.connect(self.update)    
        else:
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
        self.add_connection(controls.submitVoxelMapMemory.clicked.connect(self.update_voxel_map))
        self.add_connection(controls.voxelSizeChanged.connect(self.update_voxel_map))

        self.update()

    def update(self):
        if not self.window.isVisible():
            return

        self.__read_qml_properties()

        cursor = -1 if self.platform.is_live() else int(self.cursor)

        sample = self.platform[self.datasource][cursor]
        if self.undistortimage:
            image = sample.undistort_image()
        else:
            image = sample.raw_image()

        self.__update_actors(sample, image)

        box = None
        self.__update_box2D(sample, image, box)
        self.__update_seg_2d(sample, image)
        self.__update_bbox_3d(sample, image, box)
        self.__update_lanes(sample, image)

        self.__draw(image)
        self.video_recorder.record(self.is_recording)

    def update_aspect_ratio(self):
        im = self.ax.get_images()
        extent =  im[0].get_extent()
        self.ax.set_aspect(abs((extent[1]-extent[0])/(extent[3]-extent[2]))/self.aspect_ratio)
        self.update()

    def update_voxel_map(self):
        datasources = [ds_name for ds_name, show in dict(self.show_actor, **dict(self.show_seg_3d)).items() if show]
        for datasource in datasources:
            if isinstance(self.platform[datasource], VoxelMap):
                self.platform[datasource].clear_cache()
                self.platform[datasource].memory = int(self.window.controls.voxelMapMemory)
                self.platform[datasource].skip = int(self.window.controls.voxelMapSkip)
                self.platform[datasource].voxel_size = 10**float(self.window.controls.voxelSize)
                self.window.controls.voxelSizeText = f'{self.platform[datasource].voxel_size:.2f}'
                self.platform[datasource].invalidate_caches()
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
                rgb_colors = np.ones((cloud_sample.raw.shape[0],4))
                rgb_colors[:,0] = cloud_sample.raw['r']/255
                rgb_colors[:,1] = cloud_sample.raw['g']/255
                rgb_colors[:,2] = cloud_sample.raw['b']/255
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

        try: #remove all previous 2D and 3D boxes
            [p.remove() for p in reversed(self.ax.patches)]
            [p.remove() for p in reversed(self.ax.texts)]
        except:
            pass


    def __update_box2D(self, sample, image, box):
        datasources = [ds_name for ds_name, show in self.show_bbox_2d.items() if show]
        for ds_name in datasources:
            _, _, ds_type = parse_datasource_name(ds_name)
            box_source = categories.get_source(ds_type)

            box2d_sample = self.platform[ds_name].get_at_timestamp(sample.timestamp)
            if np.abs(np.int64(sample.timestamp) - box2d_sample.timestamp) <= 1e6:
                raw = box2d_sample.raw
                if 'confidence' in raw:
                    mask = (raw['confidence'] > self.conf_threshold)
                    box2d = raw['data'][mask]
                else:
                    box2d = raw['data']
                if len(box2d) > 0:
                    for i, box in enumerate(box2d):
                        top = (box['x']-box['h']/2)*image.shape[0]
                        left = (box['y']-box['w']/2)*image.shape[1]
                        name, color = categories.get_name_color(box_source,box['classes'])
                        if self.category_filter is not '':
                            if name not in self.category_filter:
                                continue
                        color = np.array(color)/255
                        if self.use_box_colors:
                            color = utils.to_numpy(QColor(self.box_2d_colors[ds_name]))[:3]
                        if 'confidence' in raw:
                            conf = raw['confidence'][mask][i]
                            name = f"{name}({conf:.3f})"
                        rect = Rectangle((left,top),box['w']*image.shape[1],box['h']*image.shape[0],linewidth=1,edgecolor=color,facecolor=list(color)+[0.15]) 
                        self.ax.add_patch(rect)
                        if self.box_labels_size > 0:
                            txt = self.ax.text(left,top,name+':'+str(box['id']),color='w',fontweight='bold', fontsize=self.box_labels_size, clip_on=True)
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


    def __update_bbox_3d(self, sample, image, box):
        datasources = [ds_name for ds_name, show in self.show_bbox_3d.items() if show]
        for ds_name in datasources:
            _, _, ds_type = parse_datasource_name(ds_name)
            box_source = categories.get_source(ds_type)
            if box_source not in categories.CATEGORIES: #FIXME: this should not be here
                box_source = 'deepen'

            box3d_sample = self.platform[ds_name].get_at_timestamp(sample.timestamp)
            if np.abs(np.int64(sample.timestamp) - box3d_sample.timestamp) <= 1e6:
                raw = box3d_sample.raw
                box3d = box3d_sample.mapto(self.datasource, ignore_orientation=True)
                mask = (box3d['flags'] >= 0)

                if 'confidence' in raw:
                    mask = mask & (raw['confidence'] > self.conf_threshold)

                if len(box3d[mask]) > 0:
                    for i, box in enumerate(box3d[mask]):

                        name, color = categories.get_name_color(box_source, box['classes'])
                        if self.category_filter is not '' and name not in self.category_filter:
                            break

                        color = np.array(color)/255
                        if self.use_box_colors:
                            color = utils.to_numpy(QColor(self.box_3d_colors[ds_name]))[:3]

                        if 'confidence' in raw:
                            conf = raw['confidence'][mask][i]
                            name = f"{name}({conf:.3f})"

                        vertices = linalg.bbox_to_8coordinates(box['c'],box['d'],box['r'])
                        p, mask_fov = sample.project_pts(vertices, mask_fov=False, output_mask=True, undistorted=self.undistortimage, margin=300)

                        if p[mask_fov].shape[0] < 8:
                            continue
                        
                        faces = [[0,1,3,2],[0,1,5,4],[0,2,6,4],[7,3,1,5],[7,5,4,6],[7,6,2,3]]
                        for face in faces:
                            poly = np.vstack([p[face[0]],p[face[1]],p[face[2]],p[face[3]],p[face[0]]])
                            patch = Polygon(poly, closed=True,linewidth=1,edgecolor=color,facecolor=list(color)+[0.075])
                            self.ax.add_patch(patch)

                        if self.box_labels_size > 0:
                            txt = self.ax.text(p[:,0].min(),p[:,1].min(),name+':'+str(box['id']),color='w',fontweight='bold', fontsize=self.box_labels_size, clip_on=True)
                            txt.set_path_effects([PathEffects.withStroke(linewidth=1, foreground='k')])


    def __update_lanes(self, sample, image):

        # Remove all previous lines
        [p.remove() for p in reversed(self.ax.lines)]

        datasources = [ds_name for ds_name, show in self.show_lanes.items() if show]
        for ds_name in datasources:
            lane_sample = self.platform[ds_name].get_at_timestamp(sample.timestamp)

            for lane in lane_sample.raw:

                vertices = lane_sample.transform(lane['vertices'], self.datasource, ignore_orientation=True)
                projected_lane = sample.project_pts(vertices, undistorted=self.undistortimage, mask_fov=True, margin=300) 
                
                infos = lane_types.LANE_TYPES[lane['type']]

                color = np.array(infos['color'])/255

                width = 5
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
        self.ax.collections = []


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
        self.show_IoU              = bool(  controls.showIoU)
        self.ref_ds_IoU            = str(   controls.refdsIoU)
        self.category_filter       = str(   controls.categoryFilter)
        self.aspect_ratio          = float( controls.aspectRatio)
        self.crops                 =       [controls.cropLeft, 
                                            controls.cropRight, 
                                            controls.cropTop, 
                                            controls.cropBottom]
    