from pioneer.das.api.platform import Platform
from pioneer.das.view.windows import Window

from PyQt5.QtQml import QQmlComponent, QQmlProperty, QQmlEngine

import glob
import os
import random

class PlayerWindow(Window):

    def __init__(self, window, platform, all_windows, synchronized, viewer):
        super(PlayerWindow, self).__init__(window, platform)
        
        self.all_windows = all_windows
        self.synchronized = synchronized
        self.viewer = viewer

        self._setup_properties(self.window)
        self._load_most_recent_slices()

    def connect(self):
        self.add_connection(self.window.cursorChanged.connect(self._update_seeds))
        self.add_connection(self.window.cursorChanged.connect(self._update_cursor))
        self.add_connection(self.window.recordingChanged.connect(self._update_recording))
        self.add_connection(self.window.clicked.connect(self._save_slices))
        

    def _load_most_recent_slices(self):
        if self.platform.dataset is not None:
            files = glob.glob(os.path.join(self.platform.dataset, 'slices_*.txt'))
            if len(files) > 0:
                files.sort(key=os.path.getmtime)

                with open(files[-1], 'r') as f:
                    cursors = f.read()
                    cursors = eval(cursors)
                    self.write_properties['cursors']([item for sublist in cursors for item in sublist])
   
    def _update_seeds(self):
        random.seed(42)
        new_seed = int(random.random()*1e9)
        data_labels = self.platform.datasource_names()
        for ds in data_labels:
            if 'aug' in ds:
                try:
                    self.platform[ds].set_seed(new_seed)
                except:
                    pass

    # TODO: Think of a better way to do this, the player window should not update all windows.
    def _update_cursor(self):
        cursor = self.read_properties['cursor']()
        self.all_windows['metadata'].window.playerCursor = cursor
        try:
            data_labels = self.synchronized.keys()
            data_indices = self.synchronized.indices(cursor)
            for i in range(len(data_labels)):
                ds = data_labels[i]
                ind = data_indices[i]
                if ds in self.all_windows:
                    w = self.all_windows[ds]
                    w.setProperty("playerCursor", int(cursor)) #setProperty does not remove bindings
                    w.setProperty("synchronizedCursor", int(ind)) #setProperty does not remove bindings
            for ds, cb_ in context.callbacks["custom_viewport_windows"].items():
                cb_.window.setProperty("playerCursor", int(cursor)) #setProperty does not remove bindings
                cb_.window.setProperty("synchronizedCursor", cursor)
            
        except:
            pass #traceback.print_exc()

    def _update_recording(self):
        recording = self.read_properties['recording']()
        for ds_name in self.platform.datasource_names():
            self.platform[ds_name].ds.is_recording = recording

    def _update_dataset_path(self):
        dataset_path = self.read_properties['datasetPath']()
        if dataset_path is not None:
            self.viewer.pf = Platform(dataset = dataset_path.path(), ignore=['radarTI_bfc'])
            
    def _save_slices(self):
        slices = self.read_properties['cursors']()
        n = len(slices)
        slices = [[int(slices[i*2]), int(slices[i*2+1])] for i in range(n//2)]
        path = self.platform.dataset

        with open(os.path.join(path, f"slices_{str(slices)}.txt"), 'w') as f:
            f.write(str(slices))

    # ********************************************
    # Properties
    # ********************************************
    def _setup_properties(self, window):
        self.read_properties = \
            { 'cursor': lambda: int(QQmlProperty.read(window, "cursor"))
            , 'recording': lambda: bool(QQmlProperty.read(window, "recording"))
            , 'cursors': lambda: QQmlProperty.read(window, "cursors").toVariant()
            , 'datasetPath': lambda: QQmlProperty.read(window, "datasetPath")
            }

        self.write_properties = \
            {
                'cursors': lambda value: QQmlProperty.write(window, "cursors", value)
            }

        #TODO: Investigate, for some reason signals won't trigger if we don't read properties beforehand.
        for _, property in self.read_properties.items():
            property()