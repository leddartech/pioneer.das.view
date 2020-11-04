from pioneer.common.logging_manager import LoggingManager
from pioneer.common.gui.Table import DataFrameModel
from pioneer.das.api.categories import get_category_number
from pioneer.das.api.datasources import VirtualDatasource
from pioneer.das.tests import validate_imu_flow as vif
from pioneer.das.view.windows import Window

from PyQt5.QtQml import QQmlComponent, QQmlProperty, QQmlEngine
from PyQt5.QtCore import QObject
from tqdm import tqdm

import copy
import datetime
import numpy as np
import os
import pandas as pd
pd.options.mode.chained_assignment = None
import glob
import shutil
import yaml

CHECK_SYNC_AVAILABLE = True
# Find the proper place for this utility function
def timestamp_shifting(sync, reference):
    shifts = {}
    ref_ts = sync.platform[reference].timestamps[sync.sync_indices[:,sync.sync_labels.index(reference)]].astype('f8')
    for datasource in sync.sync_labels:
        if reference == datasource:
            continue
        if isinstance(sync.platform[datasource], VirtualDatasource):
            continue
        ds_ts = sync.platform[datasource].timestamps[sync.sync_indices[:,sync.sync_labels.index(datasource)]].astype('f8')
        shifts[f'{datasource} - {reference}'] = (ds_ts - ref_ts)
    return shifts

class MetadataWindow(Window):
    def __init__(self, window, synchronized):
        super(MetadataWindow, self).__init__(window, synchronized.platform)
        self.synchronized = synchronized
        self.backend = self.window.findChild(QObject, "figure")
        self.ax = self.backend.getFigure().add_subplot(111)
        
        if self.platform.metadata is not None:
            if len(self.platform.metadata) != len(self.synchronized):
                LoggingManager.instance().warning(f'The current synchronized platform has a number of frames different than what is contained in the metadata file. ')
                self.metadata_dirty = pd.DataFrame(index=range(len(self.synchronized)))
            else:
                self.metadata_dirty = copy.deepcopy(self.platform.metadata)
        else:
            self.metadata_dirty = pd.DataFrame(index=range(len(self.synchronized)))

        self.window.columnNames = list(self.metadata_dirty.columns)
        self.window.showColumn = {c:False for c in self.window.columnNames}

        #Dummy table to avoid a few warnings
        self.table_model = DataFrameModel(self.metadata_dirty)

        with open(f'{os.path.dirname(os.path.abspath(__file__))}/../metadata.yml', 'r') as f:
            self.standard_entries = yaml.safe_load(f)

        self.window.entries.model = list(self.standard_entries.keys())
        self.window.entries.currentIndex = 0
        self.window.entryDescription.text = self.get_entry_description()
        self.window.input.model = list(self.standard_entries[self.get_entry()]['values'])
        self.window.input.currentIndex = 0

        self._select_all_frames()
        self.last_cursor_value = int(self.window.playerCursor)
        self.window.isDirty = False

        self.window.addSyncQualityData.visible = CHECK_SYNC_AVAILABLE
        self.window.addIMUQualityData.visible = 'sbgekinox_bcc_navposvel' in self.synchronized.platform.datasource_names()
        self.window.addObjectQuantityData.visible = 'flir_bfc_box2d-detectron-cyl' in self.synchronized.platform.datasource_names()


    def _select_all_frames(self):
        self.window.firstFrameSelection = 0
        self.window.lastFrameSelection = len(self.synchronized)
        self._update_frame_selection()

    def _current_first_frame(self):
        self.window.firstFrameSelection = int(self.window.playerCursor)
        self._update_frame_selection()
    def _current_last_frame(self):
        self.window.lastFrameSelection = int(self.window.playerCursor)
        self._update_frame_selection()

    def _next_first_frame(self):
        self.window.firstFrameSelection = int(self.window.lastFrameSelection)
        self._update_frame_selection()
    def _last_last_frame(self):
        self.window.lastFrameSelection = len(self.synchronized)
        self._update_frame_selection()

    def _snap_frame_selection(self):
        delta = int(self.window.playerCursor) - self.last_cursor_value
        if self.window.snapFirstFrame.checked:
            self.window.firstFrameSelection = int(self.window.firstFrameSelection) + delta
        if self.window.snapLastFrame.checked:
            self.window.lastFrameSelection = int(self.window.lastFrameSelection) + delta
        self.last_cursor_value = int(self.window.playerCursor)
        self._update_frame_selection()

    def _fastbackward_first_frame(self):
        self.window.firstFrameSelection = int(self.window.firstFrameSelection) -10
        self._update_frame_selection()
    def _backward_first_frame(self):
        self.window.firstFrameSelection = int(self.window.firstFrameSelection) -1
        self._update_frame_selection()
    def _forward_first_frame(self):
        self.window.firstFrameSelection = int(self.window.firstFrameSelection) +1
        self._update_frame_selection()
    def _fastforward_first_frame(self):
        self.window.firstFrameSelection = int(self.window.firstFrameSelection) +10
        self._update_frame_selection()
    def _fastbackward_last_frame(self):
        self.window.lastFrameSelection = int(self.window.lastFrameSelection) -10
        self._update_frame_selection()
    def _backward_last_frame(self):
        self.window.lastFrameSelection = int(self.window.lastFrameSelection) -1
        self._update_frame_selection()
    def _forward_last_frame(self):
        self.window.lastFrameSelection = int(self.window.lastFrameSelection) +1
        self._update_frame_selection()
    def _fastforward_last_frame(self):
        self.window.lastFrameSelection = int(self.window.lastFrameSelection) +10
        self._update_frame_selection()

    def _update_frame_selection(self):
        try:
            first_frame = int(self.window.firstFrameSelection)
        except: return
        first_frame = max(0, first_frame)
        first_frame = min(first_frame, len(self.synchronized)-1)
        self.window.firstFrameSelection = first_frame
        try:
            last_frame = int(self.window.lastFrameSelection)
            last_frame = max(0, last_frame)
            last_frame = min(last_frame, len(self.synchronized)-1)
            self.window.lastFrameSelection = last_frame
        except: return
        self.frame_selection = list(range(first_frame, last_frame+1))


    def _update(self):
        if self.window.visible and self.metadata_dirty.size > 0:
            self.table_model = DataFrameModel(self.metadata_dirty)
            self.window.tableView.model = self.table_model
            self._update_plot()


    def _update_plot(self):
        self.ax.clear()
        has_legend = False
        for column_name, show in self.window.showColumn.items():
            if show:
                try:
                    self.ax.plot(self.metadata_dirty[column_name], label=f'{column_name}')
                except: pass
                has_legend = True
        if has_legend:
            self.ax.legend()
        self.backend.draw()


    def get_entry(self):
        return self.window.entries.model[self.window.entries.currentIndex]

    def get_entry_description(self):
        return self.standard_entries[self.get_entry()]['description']


    def _commit_input(self):
        entry = self.get_entry()
        if 'default' in self.standard_entries[entry]:
            default = self.standard_entries[entry]['default']
        else:
            default = None
        if entry == 'keywords':
            self._add_column(entry, default_value=np.empty((len(self.metadata_dirty), 0)).tolist())
            for frame in self.frame_selection:
                self.metadata_dirty[entry][frame] += [self.window.keyword_input.text]
        else:
            self._add_column(entry, default_value=default)
            self.metadata_dirty[entry][self.frame_selection] = self.standard_entries[entry]['values'][self.window.input.currentIndex]
        self.window.isDirty = True
        self._update()


    def _add_synchronization_data(self):
        for ds in self.synchronized.sync_labels:
            if isinstance(self.platform[ds], VirtualDatasource):
                continue
            metadata_entry = f'index_{ds}'
            self._add_column(metadata_entry)
            index_in_sync_labels = self.synchronized.sync_labels.index(ds)
            sync_indices = self.synchronized.sync_indices[self.frame_selection,index_in_sync_labels]
            self.metadata_dirty[metadata_entry][self.frame_selection] = sync_indices
        self.window.isDirty = True
        self._update()


    def _add_sync_quality_data(self):
        if CHECK_SYNC_AVAILABLE:
            for ds in self.synchronized.sync_labels:
                if isinstance(self.platform[ds], VirtualDatasource):
                    continue
                shifts = timestamp_shifting(self.synchronized, reference=ds)
                shifts = np.vstack([shifts[i] for i in shifts])
                shifts = np.mean(shifts, axis=0)
                metadata_entry = f'desync_{ds}'
                self._add_column(metadata_entry)
                self.metadata_dirty[metadata_entry][self.frame_selection] = shifts[self.frame_selection]//1
            self.window.isDirty = True
            self._update()


    def _add_imu_quality_data(self):
        try:
            metadata_entry = 'IMU_step_ratio'
            ratio_ = vif.get_trajectory_step_ratio(self.synchronized, 
                                                'flir_bfc_img',
                                                'sbgekinox_bcc_navposvel',
                                                traj_min_epsilon_precision=1e-3)
                                            
            self._add_column(metadata_entry)
            self.metadata_dirty[metadata_entry][self.frame_selection] = ratio_[self.frame_selection]
        except Exception as e:
            LoggingManager.instance().warning(str(e))
        
        try:
            metadata_entry = 'IMU_standard_score'
            ratio_ = vif.get_trajectory_standard_score(self.synchronized, 
                                                'flir_bfc_img',
                                                'sbgekinox_bcc_navposvel',
                                                traj_seq_memory=200)
            
            self._add_column(metadata_entry)
            self.metadata_dirty[metadata_entry][self.frame_selection] = ratio_[self.frame_selection]
        except Exception as e:
            LoggingManager.instance().warning(str(e))

        self.window.isDirty = True
        self._update()


    def _add_object_quantity_data(self):
        objects_to_look_for = ['person','bicycle','car','motorcycle','bus','truck']
        [self._add_column(name) for name in objects_to_look_for]
        category_numbers_to_look_for = [get_category_number('detectron', name) for name in objects_to_look_for]

        for frame in self.frame_selection:
            ts = self.synchronized[frame]['flir_bfc_img'].timestamp
            box2d_sample = self.synchronized.platform['flir_bfc_box2d-detectron-cyl'].get_at_timestamp(ts)
            if abs(float(ts)-float(box2d_sample.timestamp)) > 1e5:
                continue
            category_numbers = box2d_sample.raw['data']['classes']

            for number, name in zip(category_numbers_to_look_for, objects_to_look_for):
                self.metadata_dirty[name][frame] = len(np.where(category_numbers == number)[0])

        self.window.isDirty = True
        self._update()


    def _add_column(self, column, default_value=None):
        if column not in self.metadata_dirty.columns:
            self.metadata_dirty[column] = default_value
            self.window.columnNames += [column]
            self.window.showColumn[column] = False


    def handle_entry_changed(self):
        self.window.entryDescription.text = self.get_entry_description()
        if 'values' in self.standard_entries[self.get_entry()]:
            self.window.input.visible = True
            self.window.input.model = list(self.standard_entries[self.get_entry()]['values'])
            self.window.input.currentIndex = 0
        else:
            self.window.input.visible = False
        self.window.keyword_input.visible = not self.window.input.visible



    def handle_save(self):

        if self.metadata_dirty.equals(self.platform.metadata):
            print('Nothing new to save.')
            return

        elif os.path.exists(self.platform.metadata_path):
            try:
                backup_directory = f'{self.platform.dataset}/backup_metadata'
                if not os.path.isdir(backup_directory):
                    os.mkdir(backup_directory)
                current_time = datetime.datetime.today().strftime("%Y_%m_%d_%H_%M_%S")
                backup_file = f'{backup_directory}/metadata_{current_time}.csv'
                shutil.move(f'{self.platform.metadata_path}', backup_file)
                print(f'Backed up previous metadata file to: {backup_file}')
            except:
                print('Something went wrong when trying to back up already existing metadata file. Not saving.')
                return

        self.metadata_dirty.to_csv(self.platform.metadata_path)
        self.platform.metadata = copy.deepcopy(self.metadata_dirty)
        self.window.isDirty = False
        print(f'Saved metadata to: {self.platform.metadata_path}')



    def connect(self):

        self.add_connection(self.window.firstFrameSelectionChanged.connect(self._update_frame_selection))
        self.add_connection(self.window.lastFrameSelectionChanged.connect(self._update_frame_selection))
        self.add_connection(self.window.currentFirstFrame.clicked.connect(self._current_first_frame))
        self.add_connection(self.window.currentLastFrame.clicked.connect(self._current_last_frame))
        self.add_connection(self.window.nextFirstFrame.clicked.connect(self._next_first_frame))
        self.add_connection(self.window.lastLastFrame.clicked.connect(self._last_last_frame))
        self.add_connection(self.window.snapFirstFrame.clicked.connect(self._snap_frame_selection))
        self.add_connection(self.window.snapLastFrame.clicked.connect(self._snap_frame_selection))
        self.add_connection(self.window.playerCursorChanged.connect(self._snap_frame_selection))
        self.add_connection(self.window.selectAllFrames.clicked.connect(self._select_all_frames))

        self.add_connection(self.window.fastbackwardFirstFrame.clicked.connect(self._fastbackward_first_frame))
        self.add_connection(self.window.backwardFirstFrame.clicked.connect(self._backward_first_frame))
        self.add_connection(self.window.forwardFirstFrame.clicked.connect(self._forward_first_frame))
        self.add_connection(self.window.fastforwardFirstFrame.clicked.connect(self._fastforward_first_frame))
        self.add_connection(self.window.fastbackwardLastFrame.clicked.connect(self._fastbackward_last_frame))
        self.add_connection(self.window.backwardLastFrame.clicked.connect(self._backward_last_frame))
        self.add_connection(self.window.forwardLastFrame.clicked.connect(self._forward_last_frame))
        self.add_connection(self.window.fastforwardLastFrame.clicked.connect(self._fastforward_last_frame))
        
        self.add_connection(self.window.entries.currentIndexChanged.connect(self.handle_entry_changed))

        self.add_connection(self.window.commitInput.clicked.connect(self._commit_input))

        self.add_connection(self.window.addSynchronizationData.clicked.connect(self._add_synchronization_data))
        self.add_connection(self.window.addSyncQualityData.clicked.connect(self._add_sync_quality_data))
        self.add_connection(self.window.addIMUQualityData.clicked.connect(self._add_imu_quality_data))
        self.add_connection(self.window.addObjectQuantityData.clicked.connect(self._add_object_quantity_data))

        self.add_connection(self.window.showColumnChanged.connect(self._update_plot))

        self.add_connection(self.window.save.clicked.connect(self.handle_save))

        self._update()
