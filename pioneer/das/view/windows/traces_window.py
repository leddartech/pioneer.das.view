from pioneer.common import platform as platform_utils
from pioneer.common.trace_processing import TraceProcessingCollection, Smooth, Clip, ZeroBaseline, Realign, RemoveStaticNoise, Desaturate
from pioneer.das.api.platform import Platform
from pioneer.das.api.samples import FastTrace
from pioneer.das.view.windows import Window

from pioneer.common.gui.qml import backend_qtquick5

from enum import Enum
from PyQt5.QtCore import QObject

import copy
import matplotlib.pyplot as plt
import numpy as np

COLORS = plt.cm.rainbow(np.linspace(0,1,20))

class TracesWindow(Window):

    def __init__(self, window, platform, synchronized, ds_name):
        super(TracesWindow, self).__init__(window, platform)
        self.window.setTitle(ds_name)
        self.synchronized = synchronized
        self.viewport = self.window.viewport
        self.controls = self.window.controls
        self.ds_name = ds_name

        self.backend = self.window.findChild(QObject, "figure")
        self.figure = self.backend.getFigure()
        self.ax = [self.figure.add_subplot(s) for s in [211, 212]]
        self.datasource = self.platform[self.ds_name]
        self.helper = None
        self.image = None
        self.hover_coords = None
        self.hovering = False
        self.selection = []
        self.trace_processing = None
        self.drawn_traces = []

        if self.datasource.sensor.static_noise is None or self.datasource.sensor.static_noise == 0:
            self.window.removeStaticVisible = False


    def connect(self):
        self.add_connection(self.window.cursorChanged.connect(self._update))
        self.add_connection(self.window.selectionChanged.connect(self._update))
        self.add_connection(self.window.imageTypeChanged.connect(self._update))
        self.add_connection(self.window.showRawChanged.connect(self._update))
        self.add_connection(self.window.showHighFastTraceChanged.connect(self._update))
        self.add_connection(self.window.showLowFastTraceChanged.connect(self._update))
        self.add_connection(self.window.traceProcessingChanged.connect(self._update))
        self.add_connection(self.window.desaturateChanged.connect(self._update_trace_processing))
        self.add_connection(self.window.removeStaticChanged.connect(self._update_trace_processing))
        self.add_connection(self.window.realignChanged.connect(self._update_trace_processing))
        self.add_connection(self.window.zeroBaselineChanged.connect(self._update_trace_processing))
        self.add_connection(self.window.cutoffChanged.connect(self._update_trace_processing))
        self.add_connection(self.window.smoothTraceChanged.connect(self._update_trace_processing))

        self.backend.canvas.mpl_connect('motion_notify_event', self._on_hover)
        self.backend.canvas.mpl_connect('button_press_event', self._on_click)

        self._update_trace_processing()
        self._update()


    def _update(self):

        cursor = int(self.window['cursor'])
        self.trace_sample = self.datasource[cursor]

        if self.window.traceProcessing:
            self.trace_processed = self.trace_sample.processed(self.trace_processing)

        self.selection = self.window.selection

        if isinstance(self.trace_sample, FastTrace):
            self.window.fastTraceSelectionVisible = True
        self.window.traceProcessingVisible = self.window.traceProcessing

        self._update_image()
        self._update_plots()
        self.backend.draw()


    def _update_image(self):

        sensor_type, position, trr_ds_type = platform_utils.parse_datasource_name(self.ds_name)
        echo_ds_name = f"{sensor_type}_{position}_ech-{trr_ds_type}"
        echo_sample = self.platform[echo_ds_name].get_at_timestamp(self.trace_sample.timestamp)

        if self.window.imageType == 'distance':
            image = echo_sample.distance_img(options='max_amplitude')
        elif self.window.imageType == 'width':
            image = echo_sample.other_field_img('widths')
        elif self.window.imageType == 'skew':
            image = echo_sample.other_field_img('skews')
        else:
            image = echo_sample.amplitude_img()

        if self.image is None:
            self.image = self.ax[0].imshow(image, extent=[0, image.shape[1], image.shape[0], 0])
        else:
            self.image.set_data(image)
            self.image.set_clim(image.min(), image.max())

        if self.helper is None: 
            self.helper = backend_qtquick5.MPLImageHelper(image, self.ax[0], offset = 0)
            self.helper.image_coord_to_channel_index = echo_sample.image_coord_to_channel_index


    def _update_plots(self):
        self._clear_plots()
        if len(self.selection) > 0:
            for coords in self.selection:
                row, col = coords
                index = self.helper.image_coord_to_channel_index(row, col)
                color = COLORS[index%len(COLORS)]
                marker_style = dict(color=color, marker='s', markersize=4, markerfacecolor=color, markeredgecolor = 'white')
                self.ax[0].plot(col+.5, row+.5, **marker_style)
                self.draw_traces(index, color)
            self._update_plot_range()
            self._update_legend()
            self.backend.draw()


    def _update_legend(self):
        try: self.ax[1].get_legend().remove()
        except: pass
        if len(self.drawn_traces) > 0:
            self.ax[1].legend()
            

    def _update_plot_range(self):
        if len(self.drawn_traces) > 0:
            plot_range_min = min([trace.min() for trace in self.drawn_traces])
            plot_range_max = max([trace.max() for trace in self.drawn_traces])
            if plot_range_max <= plot_range_min:
                return self.ax[1].set_ylim(-0.1,1.1)
            diff = float(plot_range_max) - float(plot_range_min)
            plot_range_min -= diff*0.1
            plot_range_max += diff*0.1
            self.ax[1].set_ylim(plot_range_min, plot_range_max)
            

    def _update_trace_processing(self):
        list_trace_processing = []
        if self.window.desaturate:
            list_trace_processing.append(Desaturate(self.datasource.sensor.saturation_calibration))
        if self.window.removeStatic:
            list_trace_processing.append(RemoveStaticNoise(self.datasource.sensor.static_noise))
        if self.window.realign:
            list_trace_processing.append(Realign())
        if self.window.zeroBaseline:
            list_trace_processing.append(ZeroBaseline())
        if self.window.cutoff:
            list_trace_processing.append(Clip())
        if self.window.smoothTrace:
            list_trace_processing.append(Smooth())
        self.trace_processing = TraceProcessingCollection(list_trace_processing)
        self._update()


    def _on_hover(self, event):
        if event.inaxes == self.ax[0]:
            try: col, row = self.helper.to_indices(event.xdata, event.ydata)
            except: 
                self.hover_coords = None
                return 0

            index = self.helper.image_coord_to_channel_index(row, col)
            if [row, col] == self.hover_coords:
                return 0
            self.hover_coords = [row, col]
            self.hovering = True

            # Marker on the currently hovered channel
            color = 'r'
            marker_style = dict(color=color, marker='o', markersize=4, markerfacecolor=color, markeredgecolor = 'white')
            self.ax[0].plot(col+.5, row+.5, **marker_style)

            len_drawn_traces = len(self.drawn_traces)

            self.draw_traces(index, color)
            self._update_plot_range()
            self._update_legend()
            self.backend.draw()

            del self.ax[0].lines[-1]
            for _ in self.drawn_traces[len_drawn_traces:]:
                del self.ax[1].lines[-1]
            self.drawn_traces = self.drawn_traces[:len_drawn_traces]
        elif self.hovering:
            self._update_plot_range()
            self._update_legend()
            self.backend.draw()
            self.hover_coords = None
        else:
            self.hover_coords = None


    def _on_click(self, event):
        if self.hover_coords is not None:
            if self.hover_coords not in self.selection:
                self.selection.append(self.hover_coords)
            else:
                self.selection.remove(self.hover_coords)
            self.window.selection = self.selection
            # self.hover_coords = None
            self._update_plots()


    def draw_traces(self, index, color):

        if self.window.showRaw:

            if isinstance(self.trace_sample, FastTrace):
                if self.window.showHighFastTrace:
                    trace_high = self.trace_sample.raw[self.datasource.sensor.FastTraceType.MidRange]['data'][index]
                    self.ax[1].plot(trace_high, color=color, label=f'Raw(High): {index}')
                    self.drawn_traces.append(trace_high)

                if self.window.showLowFastTrace:
                    trace_low = self.trace_sample.raw[self.datasource.sensor.FastTraceType.LowRange]['data'][index]
                    self.ax[1].plot(trace_low, color=color, ls=':', label=f'Raw(Low): {index}')
                    self.drawn_traces.append(trace_low)
            else:
                trace_raw = self.trace_sample.raw['data'][index]
                self.ax[1].plot(trace_raw, color=color, label=f'Raw: {index}')
                self.drawn_traces.append(trace_raw)


        if self.window.traceProcessing:

            if isinstance(self.trace_sample, FastTrace):
                if self.window.showHighFastTrace:
                    trace_processed_high = self.trace_processed[self.datasource.sensor.FastTraceType.MidRange]['data'][index]
                    self.ax[1].plot(trace_processed_high, color=color, ls='--', label=f'Processed(High): {index}')
                    self.drawn_traces.append(trace_processed_high)

                if self.window.showLowFastTrace:
                    trace_processed_low = self.trace_processed[self.datasource.sensor.FastTraceType.LowRange]['data'][index]
                    self.ax[1].plot(trace_processed_low, color=color, ls='-.', label=f'Processed(Low): {index}')
                    self.drawn_traces.append(trace_processed_low)
            else:
                trace_processed = self.trace_processed['data'][index]
                self.ax[1].plot(trace_processed, color=color, ls='--', label=f'Processed: {index}')
                self.drawn_traces.append(trace_processed)


    def _clear_plots(self):
        for ax in self.ax:
            del ax.lines[:]
        self.drawn_traces = []
        self._update_legend()

