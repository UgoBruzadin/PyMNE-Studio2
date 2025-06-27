"""Common plotting utilities for PyMNE-Studio visualization modules."""

import numpy as np
from typing import Optional, Tuple, List, Dict, Any
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import mne

from ...utils.logger import get_logger

logger = get_logger(__name__)


class PlotUtilities:
    """Utility class for common plotting operations in PyMNE-Studio."""
    
    @staticmethod
    def create_mpl_canvas(figsize: Tuple[float, float] = (12, 8), 
                         dpi: int = 100) -> Tuple[Figure, FigureCanvas]:
        """Create a matplotlib figure and canvas for PyQt integration.
        
        Parameters
        ----------
        figsize : tuple
            Figure size in inches (width, height).
        dpi : int
            Dots per inch for the figure.
            
        Returns
        -------
        tuple
            (Figure, FigureCanvas) objects.
        """
        fig = Figure(figsize=figsize, dpi=dpi, facecolor='white')
        canvas = FigureCanvas(fig)
        canvas.setParent(None)
        return fig, canvas
    
    @staticmethod
    def setup_eeg_axes(ax: Axes, 
                      n_channels: int,
                      channel_names: Optional[List[str]] = None,
                      spacing: float = 1.0) -> Dict[str, Any]:
        """Set up axes for EEG/MEG data plotting.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to configure.
        n_channels : int
            Number of channels to display.
        channel_names : list, optional
            Channel names for y-axis labels.
        spacing : float
            Vertical spacing between channels.
            
        Returns
        -------
        dict
            Configuration dictionary with y-positions and limits.
        """
        # Calculate y-positions for channels
        y_positions = np.arange(n_channels) * spacing
        y_positions = y_positions[::-1]  # Reverse for top-to-bottom display
        
        # Set up axes
        ax.set_ylim(-spacing/2, (n_channels-1)*spacing + spacing/2)
        ax.set_xlim(0, 1)  # Will be updated based on data
        
        # Set channel labels
        if channel_names is not None:
            ax.set_yticks(y_positions)
            ax.set_yticklabels(channel_names[:n_channels])
        else:
            ax.set_yticks(y_positions)
            ax.set_yticklabels([f'Ch{i+1}' for i in range(n_channels)])
        
        # Styling
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Channels')
        
        return {
            'y_positions': y_positions,
            'spacing': spacing,
            'n_channels': n_channels
        }
    
    @staticmethod
    def plot_eeg_data(ax: Axes,
                     data: np.ndarray,
                     times: np.ndarray,
                     y_positions: np.ndarray,
                     scaling: float = 1.0,
                     color: str = 'blue',
                     alpha: float = 0.8) -> List:
        """Plot EEG/MEG data on prepared axes.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to plot on.
        data : np.ndarray
            Data array (n_channels, n_times).
        times : np.ndarray
            Time points for x-axis.
        y_positions : np.ndarray
            Y-positions for each channel.
        scaling : float
            Scaling factor for data amplitude.
        color : str
            Line color.
        alpha : float
            Line transparency.
            
        Returns
        -------
        list
            List of line objects.
        """
        lines = []
        n_channels, n_times = data.shape
        
        for ch_idx in range(min(n_channels, len(y_positions))):
            # Scale and offset data
            y_data = data[ch_idx] * scaling + y_positions[ch_idx]
            
            # Plot line
            line = ax.plot(times, y_data, color=color, alpha=alpha, linewidth=0.8)[0]
            lines.append(line)
        
        # Update x-axis limits
        ax.set_xlim(times[0], times[-1])
        
        return lines
    
    @staticmethod
    def add_event_markers(ax: Axes,
                         events: np.ndarray,
                         sfreq: float,
                         event_colors: Optional[Dict[int, str]] = None) -> List:
        """Add event markers to the plot.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to add markers to.
        events : np.ndarray
            MNE events array (n_events, 3).
        sfreq : float
            Sampling frequency.
        event_colors : dict, optional
            Colors for different event types.
            
        Returns
        -------
        list
            List of marker line objects.
        """
        if events is None or len(events) == 0:
            return []
        
        # Convert sample indices to time
        event_times = events[:, 0] / sfreq
        event_ids = events[:, 2]
        
        # Default colors
        if event_colors is None:
            unique_ids = np.unique(event_ids)
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_ids)))
            event_colors = dict(zip(unique_ids, colors))
        
        # Plot vertical lines for events
        markers = []
        y_limits = ax.get_ylim()
        
        for event_time, event_id in zip(event_times, event_ids):
            color = event_colors.get(event_id, 'red')
            line = ax.axvline(x=event_time, color=color, alpha=0.7, 
                            linewidth=2, linestyle='--')
            markers.append(line)
        
        return markers
    
    @staticmethod
    def add_bad_channels_overlay(ax: Axes,
                               bad_channels: List[str],
                               all_channels: List[str],
                               y_positions: np.ndarray,
                               alpha: float = 0.3) -> List:
        """Add overlay for bad channels.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to add overlay to.
        bad_channels : list
            List of bad channel names.
        all_channels : list
            List of all channel names.
        y_positions : np.ndarray
            Y-positions for channels.
        alpha : float
            Overlay transparency.
            
        Returns
        -------
        list
            List of overlay objects.
        """
        overlays = []
        x_limits = ax.get_xlim()
        
        for bad_ch in bad_channels:
            if bad_ch in all_channels:
                ch_idx = all_channels.index(bad_ch)
                if ch_idx < len(y_positions):
                    y_pos = y_positions[ch_idx]
                    # Add red overlay for bad channel
                    overlay = ax.axhspan(y_pos - 0.4, y_pos + 0.4,
                                       xmin=0, xmax=1,
                                       color='red', alpha=alpha)
                    overlays.append(overlay)
        
        return overlays
    
    @staticmethod
    def calculate_optimal_scaling(data: np.ndarray,
                                spacing: float,
                                percentile: float = 95.0) -> float:
        """Calculate optimal scaling for data visualization.
        
        Parameters
        ----------
        data : np.ndarray
            Data array (n_channels, n_times).
        spacing : float
            Vertical spacing between channels.
        percentile : float
            Percentile for amplitude calculation.
            
        Returns
        -------
        float
            Optimal scaling factor.
        """
        # Calculate amplitude range
        data_range = np.percentile(np.abs(data), percentile)
        
        # Scale to fit within spacing
        if data_range > 0:
            scaling = (spacing * 0.8) / data_range
        else:
            scaling = 1.0
        
        return scaling
    
    @staticmethod
    def create_channel_groups(channel_names: List[str],
                            montage: Optional[mne.channels.DigMontage] = None) -> Dict[str, List[str]]:
        """Create channel groups based on naming conventions or montage.
        
        Parameters
        ----------
        channel_names : list
            List of channel names.
        montage : mne.channels.DigMontage, optional
            Channel montage for spatial grouping.
            
        Returns
        -------
        dict
            Dictionary of channel groups.
        """
        groups = {}
        
        # Basic grouping by prefixes
        prefixes = ['Fp', 'F', 'C', 'P', 'O', 'T', 'EOG', 'ECG', 'EMG']
        
        for prefix in prefixes:
            group_channels = [ch for ch in channel_names 
                            if ch.startswith(prefix)]
            if group_channels:
                groups[prefix] = group_channels
        
        # Add ungrouped channels
        grouped_channels = set()
        for group_chs in groups.values():
            grouped_channels.update(group_chs)
        
        ungrouped = [ch for ch in channel_names if ch not in grouped_channels]
        if ungrouped:
            groups['Other'] = ungrouped
        
        return groups
    
    @staticmethod
    def setup_interactive_navigation(canvas: FigureCanvas) -> Dict[str, Any]:
        """Set up interactive navigation for the plot canvas.
        
        Parameters
        ----------
        canvas : FigureCanvas
            The matplotlib canvas.
            
        Returns
        -------
        dict
            Dictionary containing navigation state.
        """
        nav_state = {
            'pan_active': False,
            'zoom_active': False,
            'selection_active': False,
            'last_click': None,
            'zoom_rect': None
        }
        
        def on_key_press(event):
            """Handle key press events."""
            if event.key == 'pan' or event.key == 'p':
                nav_state['pan_active'] = not nav_state['pan_active']
                logger.debug(f"Pan mode: {nav_state['pan_active']}")
            elif event.key == 'zoom' or event.key == 'z':
                nav_state['zoom_active'] = not nav_state['zoom_active']
                logger.debug(f"Zoom mode: {nav_state['zoom_active']}")
        
        canvas.mpl_connect('key_press_event', on_key_press)
        
        return nav_state