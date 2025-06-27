"""Advanced EEG plotting widget - the heart of PyMNE-Studio visualization.

This module implements eegplot_adv, an enhanced version of EEGLAB's eegplot
specifically designed for MNE-Python data structures.
"""

import numpy as np
from typing import Optional, Dict, List, Tuple, Any, Union
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QSlider, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QScrollArea, QFrame, QButtonGroup, QRadioButton, QToolButton,
    QMenu, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QAction

import mne
from scipy import signal

from .interactive_canvas import InteractiveEEGCanvas
from ..common.plot_utils import PlotUtilities
from ..common.colormaps import EEGColormaps
from ...core.event_system import EventMixin, EventType
from ...utils.logger import get_logger

logger = get_logger(__name__)


class FilterPreviewThread(QThread):
    """Background thread for real-time filter preview computation."""
    
    filter_computed = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, data: np.ndarray, sfreq: float, 
                 l_freq: Optional[float], h_freq: Optional[float]):
        super().__init__()
        self.data = data
        self.sfreq = sfreq
        self.l_freq = l_freq
        self.h_freq = h_freq
        
    def run(self):
        """Run filter computation in background."""
        try:
            if self.l_freq is not None or self.h_freq is not None:
                # Apply filter
                filtered_data = mne.filter.filter_data(
                    self.data, self.sfreq, 
                    l_freq=self.l_freq, h_freq=self.h_freq,
                    verbose=False
                )
                self.filter_computed.emit(filtered_data)
            else:
                # No filter - return original data
                self.filter_computed.emit(self.data)
                
        except Exception as e:
            self.error_occurred.emit(str(e))


class EEGPlotAdvanced(QWidget, EventMixin):
    """Advanced EEG plotting widget with multi-scale viewing and interactive features.
    
    This widget provides enhanced continuous EEG/MEG data visualization with:
    - Multi-scale time window display (overview + detail)
    - Interactive channel selection and grouping
    - Real-time filter preview
    - Custom annotation layers
    - Event markers and navigation
    - Spectral overlay capabilities
    
    Signals
    -------
    time_selection_changed : tuple
        Emitted when time selection changes (start_time, end_time).
    channel_selection_changed : list
        Emitted when channel selection changes (selected_channels).
    annotation_added : dict
        Emitted when annotation is added.
    view_changed : dict
        Emitted when view parameters change.
    """
    
    # Qt signals
    time_selection_changed = pyqtSignal(tuple)
    channel_selection_changed = pyqtSignal(list)
    annotation_added = pyqtSignal(dict)
    view_changed = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the EEGPlotAdvanced widget."""
        super().__init__(parent)
        EventMixin.__init__(self)
        
        # Data attributes
        self.raw_data: Optional[mne.io.Raw] = None
        self.filtered_data: Optional[np.ndarray] = None
        self.current_data: Optional[np.ndarray] = None
        self.times: Optional[np.ndarray] = None
        
        # View parameters
        self.time_window = 10.0  # seconds
        self.current_time = 0.0  # current time position
        self.n_channels_displayed = 20
        self.channel_offset = 0
        self.amplitude_scaling = 1.0
        self.show_events = True
        self.show_bad_channels = True
        
        # Channel management
        self.selected_channels: List[str] = []
        self.channel_groups: Dict[str, List[str]] = {}
        self.bad_channels: List[str] = []
        
        # Filter parameters
        self.filter_preview_active = False
        self.l_freq: Optional[float] = None
        self.h_freq: Optional[float] = None
        self.filter_thread: Optional[FilterPreviewThread] = None
        
        # UI components
        self.overview_canvas: Optional[InteractiveEEGCanvas] = None
        self.detail_canvas: Optional[InteractiveEEGCanvas] = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Register custom colormaps
        EEGColormaps.register_custom_colormaps()
        
        logger.info("EEGPlotAdvanced widget initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        # Control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Main plotting area with splitter
        plot_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Overview plot (top)
        overview_group = QGroupBox("Overview")
        overview_layout = QVBoxLayout(overview_group)
        self.overview_canvas = InteractiveEEGCanvas(parent=self, plot_type='overview')
        overview_layout.addWidget(self.overview_canvas)
        plot_splitter.addWidget(overview_group)
        
        # Detail plot (bottom)
        detail_group = QGroupBox("Detail View")
        detail_layout = QVBoxLayout(detail_group)
        self.detail_canvas = InteractiveEEGCanvas(parent=self, plot_type='detail')
        detail_layout.addWidget(self.detail_canvas)
        plot_splitter.addWidget(detail_group)
        
        # Set splitter proportions (1:3 for overview:detail)
        plot_splitter.setSizes([200, 600])
        layout.addWidget(plot_splitter)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.status_label = QLabel("No data loaded")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)
    
    def _create_control_panel(self) -> QWidget:
        """Create the control panel with all interactive controls."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(panel)
        
        # Time navigation group
        time_group = QGroupBox("Time Navigation")
        time_layout = QHBoxLayout(time_group)
        
        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(100)
        self.time_slider.valueChanged.connect(self._on_time_slider_changed)
        time_layout.addWidget(QLabel("Time:"))
        time_layout.addWidget(self.time_slider)
        
        self.time_window_spin = QSpinBox()
        self.time_window_spin.setRange(1, 60)
        self.time_window_spin.setValue(int(self.time_window))
        self.time_window_spin.setSuffix(" s")
        self.time_window_spin.valueChanged.connect(self._on_time_window_changed)
        time_layout.addWidget(QLabel("Window:"))
        time_layout.addWidget(self.time_window_spin)
        
        layout.addWidget(time_group)
        
        # Channel controls group
        channel_group = QGroupBox("Channels")
        channel_layout = QHBoxLayout(channel_group)
        
        self.n_channels_spin = QSpinBox()
        self.n_channels_spin.setRange(1, 200)
        self.n_channels_spin.setValue(self.n_channels_displayed)
        self.n_channels_spin.valueChanged.connect(self._on_n_channels_changed)
        channel_layout.addWidget(QLabel("Show:"))
        channel_layout.addWidget(self.n_channels_spin)
        
        self.channel_offset_spin = QSpinBox()
        self.channel_offset_spin.setRange(0, 0)
        self.channel_offset_spin.valueChanged.connect(self._on_channel_offset_changed)
        channel_layout.addWidget(QLabel("Offset:"))
        channel_layout.addWidget(self.channel_offset_spin)
        
        self.channel_group_combo = QComboBox()
        self.channel_group_combo.addItem("All Channels")
        self.channel_group_combo.currentTextChanged.connect(self._on_channel_group_changed)
        channel_layout.addWidget(QLabel("Group:"))
        channel_layout.addWidget(self.channel_group_combo)
        
        layout.addWidget(channel_group)
        
        # Amplitude controls group
        amplitude_group = QGroupBox("Amplitude")
        amplitude_layout = QHBoxLayout(amplitude_group)
        
        self.amplitude_slider = QSlider(Qt.Orientation.Horizontal)
        self.amplitude_slider.setRange(1, 100)
        self.amplitude_slider.setValue(50)
        self.amplitude_slider.valueChanged.connect(self._on_amplitude_changed)
        amplitude_layout.addWidget(QLabel("Scale:"))
        amplitude_layout.addWidget(self.amplitude_slider)
        
        self.auto_scale_btn = QPushButton("Auto")
        self.auto_scale_btn.clicked.connect(self._auto_scale)
        amplitude_layout.addWidget(self.auto_scale_btn)
        
        layout.addWidget(amplitude_group)
        
        # Filter controls group
        filter_group = QGroupBox("Real-time Filter Preview")
        filter_layout = QHBoxLayout(filter_group)
        
        self.filter_enable_cb = QCheckBox("Enable")
        self.filter_enable_cb.toggled.connect(self._on_filter_enable_toggled)
        filter_layout.addWidget(self.filter_enable_cb)
        
        self.high_pass_spin = QSpinBox()
        self.high_pass_spin.setRange(0, 100)
        self.high_pass_spin.setSuffix(" Hz")
        self.high_pass_spin.valueChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(QLabel("HP:"))
        filter_layout.addWidget(self.high_pass_spin)
        
        self.low_pass_spin = QSpinBox()
        self.low_pass_spin.setRange(1, 1000)
        self.low_pass_spin.setValue(100)
        self.low_pass_spin.setSuffix(" Hz")
        self.low_pass_spin.valueChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(QLabel("LP:"))
        filter_layout.addWidget(self.low_pass_spin)
        
        layout.addWidget(filter_group)
        
        # Display options group
        display_group = QGroupBox("Display")
        display_layout = QHBoxLayout(display_group)
        
        self.show_events_cb = QCheckBox("Events")
        self.show_events_cb.setChecked(True)
        self.show_events_cb.toggled.connect(self._on_display_option_changed)
        display_layout.addWidget(self.show_events_cb)
        
        self.show_bad_cb = QCheckBox("Bad Channels")
        self.show_bad_cb.setChecked(True)
        self.show_bad_cb.toggled.connect(self._on_display_option_changed)
        display_layout.addWidget(self.show_bad_cb)
        
        self.show_annotations_cb = QCheckBox("Annotations")
        self.show_annotations_cb.setChecked(True)
        self.show_annotations_cb.toggled.connect(self._on_display_option_changed)
        display_layout.addWidget(self.show_annotations_cb)
        
        layout.addWidget(display_group)
        
        return panel
    
    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        # Connect canvas signals
        if self.overview_canvas:
            self.overview_canvas.time_selection_changed.connect(self._on_overview_selection)
            self.overview_canvas.view_changed.connect(self._sync_overview_to_detail)
        
        if self.detail_canvas:
            self.detail_canvas.channel_selection_changed.connect(self._on_channel_selection)
            self.detail_canvas.annotation_added.connect(self._on_annotation_added)
    
    def load_data(self, raw: mne.io.Raw) -> None:
        """Load raw EEG/MEG data into the viewer.
        
        Parameters
        ----------
        raw : mne.io.Raw
            Raw data object to visualize.
        """
        try:
            self.raw_data = raw
            
            # Update UI limits and defaults
            self._update_ui_for_new_data()
            
            # Create channel groups
            self.channel_groups = PlotUtilities.create_channel_groups(
                raw.ch_names, raw.get_montage()
            )
            self._update_channel_group_combo()
            
            # Load initial data segment
            self._load_data_segment()
            
            # Update plots
            self._update_plots()
            
            # Update status
            duration = raw.n_times / raw.info['sfreq']
            self.status_label.setText(
                f"Loaded: {len(raw.ch_names)} channels, "
                f"{duration:.1f}s, {raw.info['sfreq']:.0f} Hz"
            )
            
            # Emit event
            self.emit_event(EventType.DATA_LOADED, 
                          data_type='Raw', 
                          n_channels=len(raw.ch_names),
                          duration=duration)
            
            logger.info(f"Loaded raw data: {len(raw.ch_names)} channels, {duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{e}")
    
    def _update_ui_for_new_data(self) -> None:
        """Update UI controls based on newly loaded data."""
        if self.raw_data is None:
            return
        
        # Update time slider
        duration = self.raw_data.n_times / self.raw_data.info['sfreq']
        self.time_slider.setMaximum(int(duration - self.time_window))
        
        # Update channel controls
        n_channels = len(self.raw_data.ch_names)
        self.n_channels_spin.setMaximum(n_channels)
        self.channel_offset_spin.setMaximum(max(0, n_channels - self.n_channels_displayed))
        
        # Update filter controls based on sampling rate
        nyquist = self.raw_data.info['sfreq'] / 2
        self.low_pass_spin.setMaximum(int(nyquist))
        
        # Reset view parameters
        self.current_time = 0.0
        self.channel_offset = 0
        
        # Get bad channels from data
        self.bad_channels = self.raw_data.info.get('bads', [])
    
    def _update_channel_group_combo(self) -> None:
        """Update the channel group combo box."""
        self.channel_group_combo.clear()
        self.channel_group_combo.addItem("All Channels")
        
        for group_name in self.channel_groups.keys():
            self.channel_group_combo.addItem(group_name)
    
    def _load_data_segment(self) -> None:
        """Load the current data segment for visualization."""
        if self.raw_data is None:
            return
        
        try:
            # Calculate time range
            start_time = self.current_time
            end_time = min(start_time + self.time_window, 
                          self.raw_data.n_times / self.raw_data.info['sfreq'])
            
            # Convert to samples
            start_sample = int(start_time * self.raw_data.info['sfreq'])
            end_sample = int(end_time * self.raw_data.info['sfreq'])
            
            # Load data segment
            data, times = self.raw_data[:, start_sample:end_sample]
            self.times = times / self.raw_data.info['sfreq'] + start_time
            
            # Apply filter preview if enabled
            if self.filter_preview_active and (self.l_freq is not None or self.h_freq is not None):
                self._apply_filter_preview(data)
            else:
                self.current_data = data
                self._update_plots()
            
        except Exception as e:
            logger.error(f"Failed to load data segment: {e}")
    
    def _apply_filter_preview(self, data: np.ndarray) -> None:
        """Apply filter preview in background thread."""
        if self.filter_thread is not None and self.filter_thread.isRunning():
            self.filter_thread.quit()
            self.filter_thread.wait()
        
        self.filter_thread = FilterPreviewThread(
            data, self.raw_data.info['sfreq'], self.l_freq, self.h_freq
        )
        self.filter_thread.filter_computed.connect(self._on_filter_computed)
        self.filter_thread.error_occurred.connect(self._on_filter_error)
        
        self.progress_bar.setVisible(True)
        self.filter_thread.start()
    
    @pyqtSlot(np.ndarray)
    def _on_filter_computed(self, filtered_data: np.ndarray) -> None:
        """Handle computed filter results."""
        self.current_data = filtered_data
        self.progress_bar.setVisible(False)
        self._update_plots()
    
    @pyqtSlot(str)
    def _on_filter_error(self, error_msg: str) -> None:
        """Handle filter computation error."""
        self.progress_bar.setVisible(False)
        logger.warning(f"Filter preview error: {error_msg}")
        # Fall back to unfiltered data
        if hasattr(self, '_last_unfiltered_data'):
            self.current_data = self._last_unfiltered_data
            self._update_plots()
    
    def _update_plots(self) -> None:
        """Update both overview and detail plots."""
        if self.current_data is None or self.times is None:
            return
        
        try:
            # Get channels to display
            channels_to_show = self._get_channels_to_display()
            
            # Update overview plot (all time, subset of channels)
            if self.overview_canvas:
                overview_data = self.current_data[channels_to_show[:10]]  # Show max 10 channels
                self.overview_canvas.update_plot(
                    overview_data, self.times, 
                    [self.raw_data.ch_names[i] for i in channels_to_show[:10]],
                    scaling=self.amplitude_scaling * 0.5  # Smaller scale for overview
                )
            
            # Update detail plot (current window, selected channels)
            if self.detail_canvas:
                detail_data = self.current_data[channels_to_show]
                channel_names = [self.raw_data.ch_names[i] for i in channels_to_show]
                
                self.detail_canvas.update_plot(
                    detail_data, self.times, channel_names,
                    scaling=self.amplitude_scaling,
                    events=self._get_events_in_window() if self.show_events else None,
                    bad_channels=self.bad_channels if self.show_bad_channels else None
                )
            
        except Exception as e:
            logger.error(f"Failed to update plots: {e}")
    
    def _get_channels_to_display(self) -> List[int]:
        """Get indices of channels to display based on current settings."""
        if self.raw_data is None:
            return []
        
        # Get current channel group
        current_group = self.channel_group_combo.currentText()
        
        if current_group == "All Channels":
            all_channels = list(range(len(self.raw_data.ch_names)))
        else:
            # Get channels in selected group
            group_channels = self.channel_groups.get(current_group, [])
            all_channels = [i for i, ch in enumerate(self.raw_data.ch_names) 
                          if ch in group_channels]
        
        # Apply offset and limit
        start_idx = self.channel_offset
        end_idx = min(start_idx + self.n_channels_displayed, len(all_channels))
        
        return all_channels[start_idx:end_idx]
    
    def _get_events_in_window(self) -> Optional[np.ndarray]:
        """Get events that fall within the current time window."""
        if self.raw_data is None or not hasattr(self.raw_data, 'annotations'):
            return None
        
        # Convert annotations to events
        try:
            events, _ = mne.events_from_annotations(self.raw_data)
            if len(events) == 0:
                return None
            
            # Filter events in current time window
            start_sample = int(self.current_time * self.raw_data.info['sfreq'])
            end_sample = int((self.current_time + self.time_window) * self.raw_data.info['sfreq'])
            
            mask = (events[:, 0] >= start_sample) & (events[:, 0] <= end_sample)
            windowed_events = events[mask]
            
            return windowed_events if len(windowed_events) > 0 else None
            
        except Exception as e:
            logger.debug(f"Could not extract events: {e}")
            return None
    
    def _auto_scale(self) -> None:
        """Automatically scale amplitude for optimal viewing."""
        if self.current_data is None:
            return
        
        try:
            channels_to_show = self._get_channels_to_display()
            data_subset = self.current_data[channels_to_show]
            
            optimal_scaling = PlotUtilities.calculate_optimal_scaling(
                data_subset, spacing=1.0, percentile=95.0
            )
            
            # Update slider position
            slider_value = int(optimal_scaling * 50)  # Scale to slider range
            self.amplitude_slider.setValue(max(1, min(100, slider_value)))
            
        except Exception as e:
            logger.error(f"Auto scaling failed: {e}")
    
    # Event handlers for UI controls
    def _on_time_slider_changed(self, value: int) -> None:
        """Handle time slider changes."""
        if self.raw_data is None:
            return
        
        duration = self.raw_data.n_times / self.raw_data.info['sfreq']
        self.current_time = (value / 100) * (duration - self.time_window)
        self._load_data_segment()
    
    def _on_time_window_changed(self, value: int) -> None:
        """Handle time window size changes."""
        self.time_window = float(value)
        self._load_data_segment()
    
    def _on_n_channels_changed(self, value: int) -> None:
        """Handle number of channels to display changes."""
        self.n_channels_displayed = value
        
        # Update channel offset limits
        if self.raw_data:
            max_offset = max(0, len(self.raw_data.ch_names) - value)
            self.channel_offset_spin.setMaximum(max_offset)
            self.channel_offset = min(self.channel_offset, max_offset)
        
        self._update_plots()
    
    def _on_channel_offset_changed(self, value: int) -> None:
        """Handle channel offset changes."""
        self.channel_offset = value
        self._update_plots()
    
    def _on_channel_group_changed(self, group_name: str) -> None:
        """Handle channel group selection changes."""
        # Reset offset when changing groups
        self.channel_offset = 0
        self.channel_offset_spin.setValue(0)
        
        # Update offset limits
        if group_name == "All Channels" and self.raw_data:
            max_channels = len(self.raw_data.ch_names)
        else:
            group_channels = self.channel_groups.get(group_name, [])
            max_channels = len(group_channels)
        
        max_offset = max(0, max_channels - self.n_channels_displayed)
        self.channel_offset_spin.setMaximum(max_offset)
        
        self._update_plots()
    
    def _on_amplitude_changed(self, value: int) -> None:
        """Handle amplitude scaling changes."""
        # Convert slider value to scaling factor
        self.amplitude_scaling = value / 50.0  # 50 = neutral scaling
        self._update_plots()
    
    def _on_filter_enable_toggled(self, enabled: bool) -> None:
        """Handle filter preview enable/disable."""
        self.filter_preview_active = enabled
        self.high_pass_spin.setEnabled(enabled)
        self.low_pass_spin.setEnabled(enabled)
        
        if enabled:
            self._on_filter_changed()
        else:
            # Reset to unfiltered data
            self._load_data_segment()
    
    def _on_filter_changed(self) -> None:
        """Handle filter parameter changes."""
        if not self.filter_preview_active:
            return
        
        # Get filter parameters
        hp_value = self.high_pass_spin.value()
        lp_value = self.low_pass_spin.value()
        
        self.l_freq = hp_value if hp_value > 0 else None
        self.h_freq = lp_value if lp_value < self.low_pass_spin.maximum() else None
        
        # Validate filter parameters
        if self.l_freq is not None and self.h_freq is not None:
            if self.l_freq >= self.h_freq:
                QMessageBox.warning(self, "Invalid Filter", 
                                  "High-pass frequency must be less than low-pass frequency.")
                return
        
        # Reload data with new filter
        self._load_data_segment()
    
    def _on_display_option_changed(self) -> None:
        """Handle display option changes."""
        self.show_events = self.show_events_cb.isChecked()
        self.show_bad_channels = self.show_bad_cb.isChecked()
        self._update_plots()
    
    # Canvas event handlers
    def _on_overview_selection(self, start_time: float, end_time: float) -> None:
        """Handle time selection in overview plot."""
        # Update detail view to show selected time range
        self.current_time = start_time
        self.time_window = min(end_time - start_time, 60.0)  # Max 60s window
        
        # Update UI controls
        duration = self.raw_data.n_times / self.raw_data.info['sfreq']
        slider_value = int((start_time / (duration - self.time_window)) * 100)
        self.time_slider.setValue(slider_value)
        self.time_window_spin.setValue(int(self.time_window))
        
        self._load_data_segment()
        
        # Emit signal
        self.time_selection_changed.emit((start_time, end_time))
    
    def _sync_overview_to_detail(self) -> None:
        """Synchronize overview plot with detail view."""
        # This could be used for cursor synchronization
        pass
    
    def _on_channel_selection(self, selected_channels: List[str]) -> None:
        """Handle channel selection in detail plot."""
        self.selected_channels = selected_channels
        self.channel_selection_changed.emit(selected_channels)
    
    def _on_annotation_added(self, annotation: Dict[str, Any]) -> None:
        """Handle annotation addition."""
        # Add annotation to raw data
        if self.raw_data is not None:
            try:
                onset = annotation['onset']
                duration = annotation.get('duration', 0.0)
                description = annotation.get('description', 'annotation')
                
                # Create MNE annotation
                mne_annotation = mne.Annotations(
                    onset=[onset], 
                    duration=[duration], 
                    description=[description]
                )
                
                # Add to raw data
                if self.raw_data.annotations is None:
                    self.raw_data.set_annotations(mne_annotation)
                else:
                    self.raw_data.annotations.append(mne_annotation)
                
                logger.info(f"Added annotation: {description} at {onset:.2f}s")
                self.annotation_added.emit(annotation)
                
            except Exception as e:
                logger.error(f"Failed to add annotation: {e}")
    
    def export_view(self, filename: str, format: str = 'png') -> None:
        """Export current view to file.
        
        Parameters
        ----------
        filename : str
            Output filename.
        format : str
            Export format ('png', 'svg', 'pdf').
        """
        try:
            if self.detail_canvas:
                self.detail_canvas.export_plot(filename, format)
                logger.info(f"Exported view to {filename}")
                
        except Exception as e:
            logger.error(f"Failed to export view: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export view:\n{e}")
    
    def get_current_view_info(self) -> Dict[str, Any]:
        """Get information about current view settings.
        
        Returns
        -------
        dict
            View information including time range, channels, scaling, etc.
        """
        return {
            'time_range': (self.current_time, self.current_time + self.time_window),
            'channels_displayed': self._get_channels_to_display(),
            'amplitude_scaling': self.amplitude_scaling,
            'filter_settings': {
                'enabled': self.filter_preview_active,
                'l_freq': self.l_freq,
                'h_freq': self.h_freq
            },
            'display_options': {
                'show_events': self.show_events,
                'show_bad_channels': self.show_bad_channels
            }
        }