"""Interactive matplotlib canvas for EEG visualization with advanced interaction capabilities."""

import numpy as np
from typing import Optional, List, Dict, Any, Tuple
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.widgets import SpanSelector
import matplotlib.patches as mpatches

from PyQt6.QtWidgets import QWidget, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QMouseEvent, QKeyEvent, QWheelEvent, QAction

import mne

from ..common.plot_utils import PlotUtilities
from ..common.colormaps import EEGColormaps
from ...utils.logger import get_logger

logger = get_logger(__name__)


class InteractiveEEGCanvas(FigureCanvas):
    """Interactive matplotlib canvas optimized for EEG/MEG visualization.
    
    This canvas provides advanced interaction capabilities including:
    - Time range selection
    - Channel selection and highlighting
    - Zoom and pan operations
    - Annotation creation
    - Event navigation
    - Context menus for advanced operations
    
    Signals
    -------
    time_selection_changed : tuple
        Emitted when time selection changes (start_time, end_time).
    channel_selection_changed : list
        Emitted when channel selection changes (channel_names).
    annotation_added : dict
        Emitted when annotation is created.
    view_changed : dict
        Emitted when view parameters change.
    """
    
    # Qt signals
    time_selection_changed = pyqtSignal(tuple)
    channel_selection_changed = pyqtSignal(list)
    annotation_added = pyqtSignal(dict)
    view_changed = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None, plot_type: str = 'detail'):
        """Initialize the InteractiveEEGCanvas.
        
        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        plot_type : str
            Type of plot ('overview' or 'detail').
        """
        # Create figure and canvas
        self.fig = Figure(figsize=(12, 8), dpi=100, facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.plot_type = plot_type
        
        # Create main axes
        self.ax = self.fig.add_subplot(111)
        
        # Data attributes
        self.data: Optional[np.ndarray] = None
        self.times: Optional[np.ndarray] = None
        self.channel_names: List[str] = []
        self.events: Optional[np.ndarray] = None
        self.bad_channels: List[str] = []
        
        # Plot elements
        self.lines: List = []
        self.event_markers: List = []
        self.bad_channel_overlays: List = []
        self.annotations_patches: List = []
        
        # Interaction state
        self.selection_mode = 'time'  # 'time', 'channel', 'annotation'
        self.selected_channels: List[str] = []
        self.selection_rectangle: Optional[Rectangle] = None
        self.time_span_selector: Optional[SpanSelector] = None
        
        # View state
        self.y_positions: Optional[np.ndarray] = None
        self.spacing: float = 1.0
        self.scaling: float = 1.0
        
        # Navigation state
        self.pan_active = False
        self.zoom_active = False
        self.last_mouse_pos: Optional[QPointF] = None
        
        self._setup_canvas()
        self._setup_interactions()
        
        logger.debug(f"InteractiveEEGCanvas initialized ({plot_type})")
    
    def _setup_canvas(self) -> None:
        """Set up the canvas appearance and layout."""
        self.fig.patch.set_facecolor('white')
        self.ax.set_facecolor('white')
        
        # Adjust layout
        self.fig.subplots_adjust(left=0.1, right=0.95, top=0.95, bottom=0.1)
        
        # Set up axes styling
        self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        self.ax.set_xlabel('Time (s)', fontsize=10)
        self.ax.set_ylabel('Channels', fontsize=10)
        
        # Enable navigation toolbar features
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _setup_interactions(self) -> None:
        """Set up mouse and keyboard interactions."""
        # Connect matplotlib events
        self.mpl_connect('button_press_event', self._on_mouse_press)
        self.mpl_connect('button_release_event', self._on_mouse_release)
        self.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.mpl_connect('key_press_event', self._on_key_press)
        self.mpl_connect('scroll_event', self._on_scroll)
        
        # Set up time span selector for overview plots
        if self.plot_type == 'overview':
            self.time_span_selector = SpanSelector(
                self.ax, self._on_time_span_select,
                direction='horizontal',
                useblit=True,
                props=dict(alpha=0.3, facecolor='blue'),
                interactive=True
            )
    
    def update_plot(self, 
                   data: np.ndarray,
                   times: np.ndarray,
                   channel_names: List[str],
                   scaling: float = 1.0,
                   events: Optional[np.ndarray] = None,
                   bad_channels: Optional[List[str]] = None) -> None:
        """Update the plot with new data.
        
        Parameters
        ----------
        data : np.ndarray
            Data array (n_channels, n_times).
        times : np.ndarray
            Time points for x-axis.
        channel_names : list
            Channel names for y-axis.
        scaling : float
            Amplitude scaling factor.
        events : np.ndarray, optional
            Events array for marking.
        bad_channels : list, optional
            List of bad channel names.
        """
        try:
            # Store data
            self.data = data
            self.times = times
            self.channel_names = channel_names
            self.scaling = scaling
            self.events = events
            self.bad_channels = bad_channels or []
            
            # Clear previous plot
            self._clear_plot()
            
            # Set up axes for EEG data
            config = PlotUtilities.setup_eeg_axes(
                self.ax, len(channel_names), channel_names, self.spacing
            )
            self.y_positions = config['y_positions']
            
            # Plot EEG data
            self._plot_eeg_data()
            
            # Add overlays
            self._plot_bad_channels()
            self._plot_events()
            self._plot_annotations()
            
            # Update view
            self._update_view()
            self.draw()
            
        except Exception as e:
            logger.error(f"Failed to update plot: {e}")
    
    def _clear_plot(self) -> None:
        """Clear all plot elements."""
        self.ax.clear()
        self.lines.clear()
        self.event_markers.clear()
        self.bad_channel_overlays.clear()
        self.annotations_patches.clear()
    
    def _plot_eeg_data(self) -> None:
        """Plot the EEG/MEG data traces."""
        if self.data is None or self.times is None or self.y_positions is None:
            return
        
        n_channels = min(len(self.channel_names), self.data.shape[0], len(self.y_positions))
        
        for ch_idx in range(n_channels):
            # Get channel color
            ch_name = self.channel_names[ch_idx]
            color = self._get_channel_color(ch_name)
            
            # Scale and offset data
            y_data = self.data[ch_idx] * self.scaling + self.y_positions[ch_idx]
            
            # Plot line
            line = self.ax.plot(self.times, y_data, 
                               color=color, alpha=0.8, linewidth=0.8,
                               picker=True, pickradius=5)[0]
            line.set_label(ch_name)  # For identification
            self.lines.append(line)
        
        # Update axes limits
        self.ax.set_xlim(self.times[0], self.times[-1])
        self.ax.set_ylim(-self.spacing/2, (n_channels-1)*self.spacing + self.spacing/2)
    
    def _get_channel_color(self, ch_name: str) -> str:
        """Get appropriate color for a channel."""
        # Check if channel is selected
        if ch_name in self.selected_channels:
            return EEGColormaps.get_selection_color()
        
        # Check if channel is bad
        if ch_name in self.bad_channels:
            return EEGColormaps.get_bad_channel_color()
        
        # Determine channel type
        ch_type = 'eeg'  # Default
        if 'EOG' in ch_name.upper():
            ch_type = 'eog'
        elif 'ECG' in ch_name.upper():
            ch_type = 'ecg'
        elif 'EMG' in ch_name.upper():
            ch_type = 'emg'
        
        return EEGColormaps.get_channel_color(ch_type, ch_name)
    
    def _plot_bad_channels(self) -> None:
        """Add overlays for bad channels."""
        if not self.bad_channels or self.y_positions is None:
            return
        
        self.bad_channel_overlays = PlotUtilities.add_bad_channels_overlay(
            self.ax, self.bad_channels, self.channel_names, self.y_positions
        )
    
    def _plot_events(self) -> None:
        """Add event markers to the plot."""
        if self.events is None or len(self.events) == 0:
            return
        
        # Convert events for plotting (assuming they're already in time units)
        event_times = self.events[:, 0] / 1000.0  # Convert to seconds if needed
        event_ids = self.events[:, 2]
        
        # Create color map for events
        unique_ids = np.unique(event_ids)
        event_colors = {}
        for event_id in unique_ids:
            event_colors[event_id] = EEGColormaps.get_event_color(event_id)
        
        # Plot vertical lines
        y_limits = self.ax.get_ylim()
        for event_time, event_id in zip(event_times, event_ids):
            if self.times[0] <= event_time <= self.times[-1]:
                color = event_colors[event_id]
                line = self.ax.axvline(x=event_time, color=color, alpha=0.7,
                                     linewidth=2, linestyle='--',
                                     label=f'Event {event_id}')
                self.event_markers.append(line)
    
    def _plot_annotations(self) -> None:
        """Plot annotations if present."""
        # This would plot MNE annotations
        # Implementation depends on how annotations are handled
        pass
    
    def _update_view(self) -> None:
        """Update view-specific settings."""
        if self.plot_type == 'overview':
            # Overview-specific styling
            self.ax.tick_params(axis='y', labelsize=8)
            self.ax.tick_params(axis='x', labelsize=8)
        else:
            # Detail view styling
            self.ax.tick_params(axis='y', labelsize=9)
            self.ax.tick_params(axis='x', labelsize=9)
        
        # Adjust grid
        self.ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    
    # Event handlers
    def _on_mouse_press(self, event) -> None:
        """Handle mouse press events."""
        if event.inaxes != self.ax:
            return
        
        self.last_mouse_pos = QPointF(event.x, event.y)
        
        if event.button == 1:  # Left click
            if self.selection_mode == 'channel':
                self._start_channel_selection(event)
            elif self.selection_mode == 'annotation':
                self._start_annotation_creation(event)
        elif event.button == 2:  # Middle click
            self.pan_active = True
        elif event.button == 3:  # Right click
            self._show_context_menu(event)
    
    def _on_mouse_release(self, event) -> None:
        """Handle mouse release events."""
        if event.inaxes != self.ax:
            return
        
        if event.button == 2:  # Middle click release
            self.pan_active = False
        
        # Finalize selection if active
        if self.selection_rectangle is not None:
            self._finalize_selection(event)
    
    def _on_mouse_move(self, event) -> None:
        """Handle mouse move events."""
        if event.inaxes != self.ax:
            return
        
        if self.pan_active and self.last_mouse_pos is not None:
            # Implement panning
            dx = event.x - self.last_mouse_pos.x()
            dy = event.y - self.last_mouse_pos.y()
            self._pan_view(dx, dy)
            self.last_mouse_pos = QPointF(event.x, event.y)
        
        # Update selection rectangle if active
        if self.selection_rectangle is not None:
            self._update_selection_rectangle(event)
    
    def _on_key_press(self, event) -> None:
        """Handle key press events."""
        if event.key == 'ctrl+a':
            # Select all channels
            self.selected_channels = self.channel_names.copy()
            self._update_channel_colors()
            self.channel_selection_changed.emit(self.selected_channels)
        elif event.key == 'escape':
            # Clear selection
            self.selected_channels.clear()
            self._update_channel_colors()
            self.channel_selection_changed.emit(self.selected_channels)
        elif event.key == 't':
            # Switch to time selection mode
            self.selection_mode = 'time'
        elif event.key == 'c':
            # Switch to channel selection mode
            self.selection_mode = 'channel'
        elif event.key == 'a':
            # Switch to annotation mode
            self.selection_mode = 'annotation'
        elif event.key == 'r':
            # Reset view
            self._reset_view()
    
    def _on_scroll(self, event) -> None:
        """Handle scroll events for zooming."""
        if event.inaxes != self.ax:
            return
        
        # Zoom in/out
        scale_factor = 1.1 if event.step > 0 else 1/1.1
        self._zoom_view(scale_factor, event.xdata, event.ydata)
    
    def _on_time_span_select(self, xmin: float, xmax: float) -> None:
        """Handle time span selection in overview plot."""
        if self.plot_type == 'overview':
            self.time_selection_changed.emit((xmin, xmax))
    
    # Selection methods
    def _start_channel_selection(self, event) -> None:
        """Start channel selection with rectangle."""
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        
        self.selection_rectangle = Rectangle(
            (x, y), 0, 0, 
            linewidth=1, edgecolor='red', facecolor='red', alpha=0.2
        )
        self.ax.add_patch(self.selection_rectangle)
        self.draw()
    
    def _update_selection_rectangle(self, event) -> None:
        """Update selection rectangle during drag."""
        if self.selection_rectangle is None:
            return
        
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        
        # Update rectangle
        x0, y0 = self.selection_rectangle.get_xy()
        width = x - x0
        height = y - y0
        
        self.selection_rectangle.set_width(width)
        self.selection_rectangle.set_height(height)
        self.draw()
    
    def _finalize_selection(self, event) -> None:
        """Finalize channel selection."""
        if self.selection_rectangle is None:
            return
        
        # Get selection bounds
        x0, y0 = self.selection_rectangle.get_xy()
        width = self.selection_rectangle.get_width()
        height = self.selection_rectangle.get_height()
        
        x1, y1 = x0 + width, y0 + height
        
        # Find channels in selection
        if self.y_positions is not None:
            selected_indices = []
            for i, y_pos in enumerate(self.y_positions):
                if min(y0, y1) <= y_pos <= max(y0, y1):
                    selected_indices.append(i)
            
            # Update selected channels
            new_selection = [self.channel_names[i] for i in selected_indices 
                           if i < len(self.channel_names)]
            
            # Toggle selection (add/remove)
            for ch in new_selection:
                if ch in self.selected_channels:
                    self.selected_channels.remove(ch)
                else:
                    self.selected_channels.append(ch)
        
        # Remove rectangle
        self.selection_rectangle.remove()
        self.selection_rectangle = None
        
        # Update display
        self._update_channel_colors()
        self.channel_selection_changed.emit(self.selected_channels)
        self.draw()
    
    def _start_annotation_creation(self, event) -> None:
        """Start creating an annotation."""
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        
        # For now, create a simple point annotation
        annotation = {
            'onset': x,
            'duration': 0.0,
            'description': 'manual_annotation',
            'channels': self.selected_channels if self.selected_channels else None
        }
        
        self.annotation_added.emit(annotation)
    
    def _update_channel_colors(self) -> None:
        """Update line colors based on selection."""
        for i, line in enumerate(self.lines):
            if i < len(self.channel_names):
                ch_name = self.channel_names[i]
                color = self._get_channel_color(ch_name)
                line.set_color(color)
        
        self.draw()
    
    # Navigation methods
    def _pan_view(self, dx: float, dy: float) -> None:
        """Pan the view by given pixel offset."""
        # Convert pixel offset to data coordinates
        bbox = self.ax.get_window_extent()
        dx_data = dx / bbox.width * (self.ax.get_xlim()[1] - self.ax.get_xlim()[0])
        dy_data = dy / bbox.height * (self.ax.get_ylim()[1] - self.ax.get_ylim()[0])
        
        # Update limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        self.ax.set_xlim(xlim[0] - dx_data, xlim[1] - dx_data)
        self.ax.set_ylim(ylim[0] - dy_data, ylim[1] - dy_data)
        
        self.draw()
    
    def _zoom_view(self, scale_factor: float, center_x: float, center_y: float) -> None:
        """Zoom the view around a center point."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Calculate new limits
        x_range = (xlim[1] - xlim[0]) / scale_factor
        y_range = (ylim[1] - ylim[0]) / scale_factor
        
        new_xlim = (center_x - x_range/2, center_x + x_range/2)
        new_ylim = (center_y - y_range/2, center_y + y_range/2)
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        
        self.draw()
    
    def _reset_view(self) -> None:
        """Reset view to show all data."""
        if self.times is not None and self.y_positions is not None:
            self.ax.set_xlim(self.times[0], self.times[-1])
            self.ax.set_ylim(-self.spacing/2, (len(self.y_positions)-1)*self.spacing + self.spacing/2)
            self.draw()
    
    def _show_context_menu(self, event) -> None:
        """Show context menu at mouse position."""
        # Context menu would be implemented here
        # For now, just log the action
        logger.debug(f"Context menu requested at ({event.xdata:.2f}, {event.ydata:.2f})")
    
    # Export methods
    def export_plot(self, filename: str, format: str = 'png') -> None:
        """Export the current plot to file.
        
        Parameters
        ----------
        filename : str
            Output filename.
        format : str
            Export format ('png', 'svg', 'pdf').
        """
        try:
            self.fig.savefig(filename, format=format, dpi=300, bbox_inches='tight')
            logger.info(f"Plot exported to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to export plot: {e}")
            raise
    
    def get_view_state(self) -> Dict[str, Any]:
        """Get current view state for saving/restoring.
        
        Returns
        -------
        dict
            View state information.
        """
        return {
            'xlim': self.ax.get_xlim(),
            'ylim': self.ax.get_ylim(),
            'selected_channels': self.selected_channels.copy(),
            'selection_mode': self.selection_mode,
            'scaling': self.scaling
        }
    
    def set_view_state(self, state: Dict[str, Any]) -> None:
        """Restore view state.
        
        Parameters
        ----------
        state : dict
            View state to restore.
        """
        try:
            if 'xlim' in state:
                self.ax.set_xlim(state['xlim'])
            if 'ylim' in state:
                self.ax.set_ylim(state['ylim'])
            if 'selected_channels' in state:
                self.selected_channels = state['selected_channels']
                self._update_channel_colors()
            if 'selection_mode' in state:
                self.selection_mode = state['selection_mode']
            if 'scaling' in state:
                self.scaling = state['scaling']
            
            self.draw()
            
        except Exception as e:
            logger.error(f"Failed to restore view state: {e}")