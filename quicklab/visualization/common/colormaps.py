"""Custom colormaps optimized for EEG/MEG visualization."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from typing import Dict, List, Tuple, Optional

from ...utils.logger import get_logger

logger = get_logger(__name__)


class EEGColormaps:
    """Custom colormaps and color schemes for EEG/MEG visualization."""
    
    # Default channel colors for different channel types
    CHANNEL_COLORS = {
        'eeg': '#1f77b4',      # Blue
        'meg_mag': '#ff7f0e',   # Orange
        'meg_grad': '#2ca02c',  # Green
        'eog': '#d62728',       # Red
        'ecg': '#9467bd',       # Purple
        'emg': '#8c564b',       # Brown
        'stim': '#e377c2',      # Pink
        'misc': '#7f7f7f',      # Gray
    }
    
    # Event type colors
    EVENT_COLORS = {
        1: '#ff0000',   # Red
        2: '#00ff00',   # Green
        3: '#0000ff',   # Blue
        4: '#ffff00',   # Yellow
        5: '#ff00ff',   # Magenta
        6: '#00ffff',   # Cyan
        7: '#ffa500',   # Orange
        8: '#800080',   # Purple
        9: '#ffc0cb',   # Pink
        10: '#a52a2a',  # Brown
    }
    
    @classmethod
    def get_channel_color(cls, ch_type: str, ch_name: Optional[str] = None) -> str:
        """Get color for a channel based on its type.
        
        Parameters
        ----------
        ch_type : str
            Channel type (e.g., 'eeg', 'meg_mag', 'eog').
        ch_name : str, optional
            Channel name for more specific coloring.
            
        Returns
        -------
        str
            Hex color code.
        """
        # Special cases based on channel name
        if ch_name:
            ch_name_lower = ch_name.lower()
            if 'eog' in ch_name_lower or 'veog' in ch_name_lower or 'heog' in ch_name_lower:
                return cls.CHANNEL_COLORS['eog']
            elif 'ecg' in ch_name_lower:
                return cls.CHANNEL_COLORS['ecg']
            elif 'emg' in ch_name_lower:
                return cls.CHANNEL_COLORS['emg']
        
        return cls.CHANNEL_COLORS.get(ch_type, cls.CHANNEL_COLORS['misc'])
    
    @classmethod
    def get_event_color(cls, event_id: int) -> str:
        """Get color for an event based on its ID.
        
        Parameters
        ----------
        event_id : int
            Event identifier.
            
        Returns
        -------
        str
            Hex color code.
        """
        if event_id in cls.EVENT_COLORS:
            return cls.EVENT_COLORS[event_id]
        
        # Generate color for unknown event IDs
        np.random.seed(event_id)  # Consistent color for same ID
        color = plt.cm.tab20(np.random.rand())
        return f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'
    
    @staticmethod
    def create_eeg_diverging_colormap(name: str = 'eeg_diverging') -> LinearSegmentedColormap:
        """Create a diverging colormap optimized for EEG topographies.
        
        Parameters
        ----------
        name : str
            Name for the colormap.
            
        Returns
        -------
        LinearSegmentedColormap
            Custom colormap.
        """
        colors = ['#053061', '#2166ac', '#4393c3', '#92c5de', '#d1e5f0',
                 '#f7f7f7', '#fdbf6f', '#ff7f00', '#d94801', '#7f2704']
        
        return LinearSegmentedColormap.from_list(name, colors, N=256)
    
    @staticmethod
    def create_spectral_colormap(name: str = 'eeg_spectral') -> LinearSegmentedColormap:
        """Create a colormap optimized for spectral data visualization.
        
        Parameters
        ----------
        name : str
            Name for the colormap.
            
        Returns
        -------
        LinearSegmentedColormap
            Custom colormap.
        """
        colors = ['#000033', '#000055', '#0000ff', '#0055ff', '#00aaff',
                 '#00ffff', '#55ff00', '#aaff00', '#ffff00', '#ff5500',
                 '#ff0000', '#aa0000', '#550000']
        
        return LinearSegmentedColormap.from_list(name, colors, N=256)
    
    @staticmethod
    def create_connectivity_colormap(name: str = 'eeg_connectivity') -> LinearSegmentedColormap:
        """Create a colormap for connectivity visualization.
        
        Parameters
        ----------
        name : str
            Name for the colormap.
            
        Returns
        -------
        LinearSegmentedColormap
            Custom colormap.
        """
        colors = ['#ffffff', '#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4',
                 '#2c7fb8', '#253494', '#081d58']
        
        return LinearSegmentedColormap.from_list(name, colors, N=256)
    
    @classmethod
    def get_channel_group_colors(cls, n_groups: int) -> List[str]:
        """Get distinct colors for channel groups.
        
        Parameters
        ----------
        n_groups : int
            Number of groups to color.
            
        Returns
        -------
        list
            List of hex color codes.
        """
        if n_groups <= 10:
            # Use tab10 colormap for small number of groups
            colors = plt.cm.tab10(np.linspace(0, 1, n_groups))
        elif n_groups <= 20:
            # Use tab20 colormap for medium number of groups
            colors = plt.cm.tab20(np.linspace(0, 1, n_groups))
        else:
            # Use hsv colormap for large number of groups
            colors = plt.cm.hsv(np.linspace(0, 1, n_groups))
        
        # Convert to hex
        hex_colors = []
        for color in colors:
            hex_color = f'#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}'
            hex_colors.append(hex_color)
        
        return hex_colors
    
    @staticmethod
    def get_amplitude_colormap(data_range: Tuple[float, float]) -> Tuple[str, float, float]:
        """Get appropriate colormap and scaling for amplitude data.
        
        Parameters
        ----------
        data_range : tuple
            (min_value, max_value) of the data.
            
        Returns
        -------
        tuple
            (colormap_name, vmin, vmax) for visualization.
        """
        min_val, max_val = data_range
        
        if min_val >= 0:
            # All positive data
            return 'viridis', min_val, max_val
        elif max_val <= 0:
            # All negative data
            return 'viridis_r', min_val, max_val
        else:
            # Bipolar data
            abs_max = max(abs(min_val), abs(max_val))
            return 'RdBu_r', -abs_max, abs_max
    
    @classmethod
    def register_custom_colormaps(cls) -> None:
        """Register custom colormaps with matplotlib."""
        try:
            # Register EEG-specific colormaps
            eeg_diverging = cls.create_eeg_diverging_colormap()
            plt.cm.register_cmap(cmap=eeg_diverging)
            
            eeg_spectral = cls.create_spectral_colormap()
            plt.cm.register_cmap(cmap=eeg_spectral)
            
            eeg_connectivity = cls.create_connectivity_colormap()
            plt.cm.register_cmap(cmap=eeg_connectivity)
            
            logger.info("Custom EEG colormaps registered successfully")
            
        except Exception as e:
            logger.warning(f"Failed to register custom colormaps: {e}")
    
    @staticmethod
    def get_bad_channel_color() -> str:
        """Get color for marking bad channels."""
        return '#ff6b6b'  # Light red
    
    @staticmethod
    def get_selection_color() -> str:
        """Get color for selected regions/channels."""
        return '#4ecdc4'  # Teal
    
    @staticmethod
    def get_annotation_colors() -> Dict[str, str]:
        """Get colors for different annotation types."""
        return {
            'BAD_artifact': '#ff4757',      # Red
            'BAD_muscle': '#ff6348',        # Orange-red
            'BAD_eye': '#ff7675',           # Light red
            'BAD_cardiac': '#fd79a8',       # Pink
            'BAD_line_noise': '#a29bfe',    # Purple
            'EDGE': '#74b9ff',              # Blue
            'artifact': '#ff4757',          # Red (generic)
            'good': '#00b894',              # Green
        }