from pioneer.common import platform as platform_utils
from pioneer.common.trace_processing import TraceProcessingCollection, Smooth, Clip, ZeroBaseline, Realign, RemoveStaticNoise, Desaturate
from pioneer.common import clouds
from pioneer.das.api.samples import FastTrace, Echo
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

        sensor_name, sensor_pos, trr_ds_type = platform_utils.parse_datasource_name(self.ds_name)
        self.ech_ds_name = f'{sensor_name}_{sensor_pos}_ech'
        self.has_echoes = self.ech_ds_name in self.platform.datasource_names()
        self.virtual_ech_ds_name = f'{sensor_name}_{sensor_pos}_ech-{trr_ds_type}'
        self.has_virtual_echoes = self.virtual_ech_ds_name in self.platform.datasource_names()
        if self.has_virtual_echoes:
            self.window.useVirtualEchoes.visible = True

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
        self.add_connection(self.window.addToSelectionSubmit.clicked.connect(self._add_to_selection))
        self.add_connection(self.window.useVirtualEchoes.clicked.connect(self._update))
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

        if self.window.useVirtualEchoes.checked:
            self.echo_sample = self.platform[self.virtual_ech_ds_name].get_at_timestamp(self.trace_sample.timestamp)
        elif self.has_echoes:
            self.echo_sample = self.platform[self.ech_ds_name].get_at_timestamp(self.trace_sample.timestamp)
        else:
            self.echo_sample = self._placeholder_echo_sample()

        if self.window.imageType == 'distance':
            image = self.echo_sample.distance_img(options='max_amplitude')
        elif self.window.imageType == 'width':
            image = self.echo_sample.other_field_img('widths')
        elif self.window.imageType == 'skew':
            image = self.echo_sample.other_field_img('skews')
        else:
            image = self.echo_sample.amplitude_img()

        if self.image is None:
            self.image = self.ax[0].imshow(image, extent=[0, image.shape[1], image.shape[0], 0])
        else:
            self.image.set_data(image)
            self.image.set_clim(image.min(), image.max())

        if self.helper is None: 
            self.helper = backend_qtquick5.MPLImageHelper(image, self.ax[0], offset = 0)
            self.helper.image_coord_to_channel_index = self.echo_sample.image_coord_to_channel_index
            self.helper.channel_index_to_image_coord = self.echo_sample.channel_index_to_image_coord


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

            # Amplitude and distance of echo in hovered channel
            ech_idx = np.where(self.echo_sample.indices == index)[0]
            self.ax[0].set_title(f'amp:{self.echo_sample.amplitudes[ech_idx]}, dst:{self.echo_sample.distances[ech_idx]}')

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
            self.ax[0].set_title(f'')
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

    def _add_to_selection(self):
        try:
            channel = int(self.window.addToSelection)
            row, col = self.helper.channel_index_to_image_coord(channel)
            self.selection.append([row, col])
            self.window.selection = self.selection
        except: pass
        self._update_plots()


    def draw_traces(self, index, color):

        if self.window.showRaw:

            if isinstance(self.trace_sample, FastTrace):
                if self.window.showHighFastTrace:
                    trace_high = self.trace_sample.raw['high']['data'][index]
                    self.ax[1].plot(trace_high, color=color, label=f'Raw(High): {index}')
                    self.drawn_traces.append(trace_high)

                if self.window.showLowFastTrace:
                    trace_low = self.trace_sample.raw['low']['data'][index]
                    self.ax[1].plot(trace_low, color=color, ls=':', label=f'Raw(Low): {index}')
                    self.drawn_traces.append(trace_low)
            else:
                trace_raw = self.trace_sample.raw['data'][index]
                self.ax[1].plot(trace_raw, color=color, label=f'Raw: {index}')
                self.drawn_traces.append(trace_raw)


        if self.window.traceProcessing:

            if isinstance(self.trace_sample, FastTrace):
                if self.window.showHighFastTrace:
                    trace_processed_high = self.trace_processed['high']['data'][index]
                    self.ax[1].plot(trace_processed_high, color=color, ls='--', label=f'Processed(High): {index}')
                    self.drawn_traces.append(trace_processed_high)

                if self.window.showLowFastTrace:
                    trace_processed_low = self.trace_processed['low']['data'][index]
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



    def _placeholder_echo_sample(self):

        if isinstance(self.trace_sample, FastTrace):
            traces_raw = self.trace_sample.raw['high']
        else:
            traces_raw = self.trace_sample.raw

        v, h = self.trace_sample.specs['v'], self.trace_sample.specs['h']
        vv, hh = np.mgrid[0:v, 0:h]
        coords_img = np.stack((vv,hh, np.arange(0, v*h).reshape(v, h)), axis=2)[...,2]
        coords_img_tf = np.flipud(coords_img)
        indices = coords_img_tf.flatten()
        amplitudes = np.max(traces_raw['data'], axis=1)[indices]
        distances = np.argmax(traces_raw['data'], axis=1)[indices]*traces_raw['distance_scaling']
        try:
            distances += traces_raw['time_base_delays'][indices]
        except:
            distances += traces_raw['time_base_delays']

        raw = clouds.to_echo_package(
            indices = np.array(indices, 'u4'), 
            distances = np.array(distances, 'f4'), 
            amplitudes = np.array(amplitudes, 'f4'),
            timestamp = self.trace_sample.timestamp,
            specs = self.trace_sample.specs
        )

        return Echo(self.trace_sample.index, self.trace_sample.datasource, raw, self.trace_sample.timestamp)