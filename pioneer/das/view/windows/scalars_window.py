from pioneer.das.view.windows import Window

from PyQt5.QtCore import QObject

import numpy as np

class ScalarsWindow(Window):

    def __init__(self, window, platform, synchronized, ds_name):
        super(ScalarsWindow, self).__init__(window, platform)
        self.window.setTitle(ds_name)
        self.synchronized = synchronized
        self.ds_name = ds_name

        self.backend = self.window.findChild(QObject, "figure")
        self.ax = self.backend.getFigure().add_subplot(111)
        self.datasource = self.platform[self.ds_name]
        self.image = None
        
        raw_0 = self.datasource[0].raw
        if type(raw_0) == dict:
            self.raw_is_dict = True
            raw_0 = raw_0['data']
        else:
            self.raw_is_dict = False

        if raw_0.dtype.names is not None:
            self.columns = list(raw_0.dtype.names)
        else:
            self.columns = list(range(raw_0.size))

        self.window.columnNames = self.columns

        show_column = {c:False for c in self.columns}
        show_column[self.columns[0]] = True
        self.window.showColumn = show_column

        self.colors = {c:f'C{i}' for i,c in enumerate(self.columns)}


    def connect(self):
        self.add_connection(self.window.cursorChanged.connect(self._update))
        self.add_connection(self.window.showColumnChanged.connect(self._update))
        self.add_connection(self.window.markersChanged.connect(self._update))
        self.add_connection(self.window.startTimeChanged.connect(self._update))
        self.add_connection(self.window.endTimeChanged.connect(self._update))
        self._update()
    
    def _update(self):

        cursor = int(self.window['cursor'])
        sample = self.datasource[cursor]
        
        try:
            indices = self.datasource.get_timestamp_slice(
                sample.timestamp, 
                (int(float(self.window.startTime)*1e6), int(float(self.window.endTime)*1e6))
            )
        except:
            return

        del self.ax.lines[:]

        show_column = self.window.showColumn
        markers = 'o' if self.window.markers else ''
        
        min_y = np.finfo('f4').max
        max_y = np.finfo('f4').min
        has_legend = False
        for column_name, show in show_column.items():
            if show:                
                scalar_samples = self.datasource[indices]
                if self.raw_is_dict: #TODO: this is a missed abstraction opportunity for this type of Sample
                    scalars = np.array([s.raw['data'][column_name] for s in scalar_samples])
                else:
                    scalars = np.array([s.raw[column_name] for s in scalar_samples])
                min_y = min(min_y, scalars.min())
                max_y = max(max_y, scalars.max())
                times = (self.datasource.timestamps[indices].astype('f8') - sample.timestamp)/1e6
                self.ax.plot(times, scalars, marker=markers, label=column_name, color=self.colors[column_name])
                has_legend = True
        
        self.ax.set_ylim([min_y,max_y])
        self.ax.set_xlim([times.min(),times.max()])
        if has_legend:
            self.ax.legend()

        self.ax.set_xlabel('relative time [s]')

        self.backend.draw()