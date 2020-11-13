from pioneer.common import platform as platform_utils
from pioneer.common.gui import interactive, CustomActors, utils
from pioneer.common.gui.qml import backend_qtquick5
from pioneer.das.api.platform import Platform
from pioneer.das.view import QMLDIR
from pioneer.das.view.windows import PlayerWindow, CalibWindow, MetadataWindow, ViewportWindow, ImagerWindow, TracesWindow, ScalarsWindow

from PyQt5.QtQml import QQmlProperty
from PyQt5.QtWidgets import QApplication

import os
import os.path

DEFAULT_SYNC_LABELS = ['*ech*', '*_img*', '*_flimg*', '*_trr*', '*_trf*', '*_ftrr*']
DEFAULT_INTERP_LABELS = ['*_xyzit*', '*_xyzvcfar*', 'sbgekinox_*', 'peakcan_*', '*temp', '*_pos*', '*_agc*', '*_rpm', '*_ago']

DEFAULT_IGNORE_LABELS = ['radarTI_bfc_rtr', 'radarTI_bfc_rec']
DEFAULT_TOLERANCE = 2e3 #2 ms

class DasCallback(utils.ContextCallback):

    def __init__(self, window, pf,  ds = None):
        super(DasCallback, self).__init__()
        self.pf = pf
        self.ds = ds
        self.window = window

    def wrap_callback(self, callback):
        self._callback = callback
        return self.callback

class Viewer(object):

    def __init__(self, path, platform = None, synchronized = None, include=None, ignore=[], add_sync=None, video_fps=None):
        self.video_fps = video_fps
        if path is None and platform is None:
            self.pf = synchronized.platform
        else:
            extra_ignore_labels = DEFAULT_IGNORE_LABELS
            ignore.extend(extra_ignore_labels)
            self.pf = Platform(dataset = path, include=include) if platform is None else platform

        self.synchronized = synchronized

        if not self.pf.is_live():

            if add_sync is not None:
                sync_labels += add_sync

            if self.synchronized is None:
                if 'synchronization' in self.pf.yml:
                    self.synchronized = self.pf.synchronized()
                else:
                    self.synchronized = self.pf.synchronized(
                        sync_labels=DEFAULT_SYNC_LABELS, 
                        interp_labels=DEFAULT_INTERP_LABELS, 
                        tolerance_us=DEFAULT_TOLERANCE
                    )
        else:
            self.synchronized = self.pf.synchronized([])

        self.callbacks = {}
        self.connections = []
        self.videos_to_close = []
        self.record = False
        self._create_vp()


    def wait_key(self, wait_key = ' '):
        self.leddar_vp.wait_key(wait_key)

    def run(self):
        self.leddar_vp.run()

    def populate_datasources(self):
        self.sensors = {}
        self.datasources = {}
        for sensor_name in self.pf.sensors:
            sensor = self.pf.sensors[sensor_name]
            ds_names = list(sensor.keys())
            ds_dict = {}
            for ds_name in ds_names:
                full_ds_name = f'{sensor_name}_{ds_name}'
                self.datasources[full_ds_name] = ds_dict[ds_name] =\
                { 'sensor_name': sensor_name
                , 'ds_name': ds_name
                , 'full_ds_name': full_ds_name
                , 'size': len(sensor[ds_name])
                }
            self.sensors[sensor_name] = ds_dict

    def _create_vp(self):

        self.populate_datasources()
        
        if self.pf.is_live():
            self.record = True

        self.leddar_vp = interactive.multi_windows_vp('root_das.qml', [backend_qtquick5.QMLDIR, QMLDIR], [("mplIcons", backend_qtquick5.MatplotlibIconProvider())]
        , rgb = sorted(self.pf.expand_wildcards(['*_img*', '*_flimg*']))
        , bboxes2D = sorted(self.pf.expand_wildcards(['*_box2d*']))
        , seg2D = sorted(self.pf.expand_wildcards(['*_poly2d-*','*_seg2d-*','*_seg2dimg-*']))
        , bboxes3D = sorted(self.pf.expand_wildcards(['*_box3d*']))
        , seg3D = sorted(self.pf.expand_wildcards(['*_seg3d-*']))
        , lanes = sorted(self.pf.expand_wildcards(['*_lane-*']))
        , viewports = sorted(self.pf.expand_wildcards(['*_ech*', '*_xyzit', '*xyzit-*', '*_xyzvcfar*']))
        , scalars = sorted(self.pf.expand_wildcards(['sbgekinox_*', 'peakcan_*','encoder_*','mti_*','carlagps_*', 'carlaimu_*']))
        , traces = sorted(self.pf.expand_wildcards(['*_trr*', '*_trf*','*_ftrr*']))
        , sensors = self.sensors
        , datasources = self.datasources
        , synchDatasources = self.synchronized.keys()
        , nIndices = len(self.synchronized)
        , isLive = self.record)

        root = self.leddar_vp.root_wrapper()

        self.callbacks = {"scalars_windows":{}, "traces_windows": {}, "viewport_windows":{},"custom_viewport_windows": {}}
        
        self.all_windows = {}

        self._connect_scalars_windows()
        self._connect_traces_windows()
        self._connect_viewport_windows()
        self._connect_imager_windows()
        self.custom_viewport_windows = {}

        self.metadata_window = MetadataWindow(self.leddar_vp.root_wrapper().metadataWindow, self.synchronized)

        self.player_window = PlayerWindow(self.leddar_vp.root, self.pf, self._all_windows(), self.synchronized, self)

        self.calib_window = CalibWindow(self.leddar_vp.root_wrapper().calibWindow, self.pf)

        QQmlProperty.write(self.leddar_vp.root, "title", os.path.abspath(self.pf.dataset))


    def get_intervals(self):
        cursors = QQmlProperty.read(self.leddar_vp.root, "cursors").toVariant()
        intervals = []
        for i in range(len(cursors)//2):
            intervals.append((int(cursors[i*2]), int(cursors[i*2+1])))
        
        return intervals

    def set_custom_viewports(self, ds_names, callbacks):

        QQmlProperty.write(self.leddar_vp.root, "customViewports", ds_names)
        
        self.custom_viewport_windows = {}
        
        while not all(k in self.custom_viewport_windows for k in ds_names) :
            QApplication.processEvents()
            self.custom_viewport_windows = QQmlProperty.read(self.leddar_vp.root, "customViewportWindows").toVariant()
            
        self.custom_datasources = {}

        for i, ds in enumerate(ds_names):
            w = self.custom_viewport_windows[ds]
            cb = DasCallback(w, self.pf, ds)
            cb.vp = QQmlProperty.read(w, "viewport")
            cb.cursor_callback = callbacks[i]
            def update(context):
                cursor = int(QQmlProperty.read(context.window, "cursor"))
                context.cursor_callback(cursor, context)

            cb.wrap_callback(update)
            cb.callback()
            cb.connect_to(w.cursorChanged)
            cb.connect_to(w.visibleChanged)    
            self.callbacks["custom_viewport_windows"][ds] = cb

            sensor_type, position, datasource = platform_utils.parse_datasource_name(ds)

            self.custom_datasources[ds] = { 
              'sensor_name' : f"{sensor_type}_{position}"
            , 'ds_name'     : datasource
            , 'full_ds_name': ds
            , 'size'        : len(self.synchronized)}

        QQmlProperty.write(self.leddar_vp.root, "customDatasources", self.custom_datasources)

        return self.callbacks["custom_viewport_windows"]


    def _connect_scalars_windows(self):

        self.scalars_windows = QQmlProperty.read(self.leddar_vp.root, "scalarsWindows").toVariant()
        self._scalars_windows = []
        for ds_name, window in self.scalars_windows.items():
            self._scalars_windows.append(ScalarsWindow(utils.QmlWrapper(window), self.pf, self.synchronized, ds_name))


    def _connect_traces_windows(self):

        self.traces_windows = QQmlProperty.read(self.leddar_vp.root, "tracesWindows").toVariant()
        self._traces_windows = []
        for ds_name, window in self.traces_windows.items():
            self._traces_windows.append(TracesWindow(utils.QmlWrapper(window), self.pf, self.synchronized, ds_name))

    def _connect_viewport_windows(self):

        self.viewport_windows = self.leddar_vp.root_wrapper().viewportWindows
        self._viewport_windows = []
        for ds_name, window in self.viewport_windows.items():
            self._viewport_windows.append(ViewportWindow(utils.QmlWrapper(window), self.pf, self.synchronized, ds_name, self.video_fps))

    
    def _connect_imager_windows(self):
        self.imager_windows = self.leddar_vp.root_wrapper().rgbWindows
        self._imager_windows = []
        for ds_name, window in self.imager_windows.items():
            self._imager_windows.append(ImagerWindow(utils.QmlWrapper(window), self.pf, self.synchronized, ds_name, self.video_fps))


    def _all_windows(self):
        return {**self.imager_windows, **self.scalars_windows, **self.viewport_windows, **self.traces_windows, **self.custom_viewport_windows, 'metadata':self.metadata_window}
            
