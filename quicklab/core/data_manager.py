"""Data management system for QuickLab.

This module handles loading, saving, and managing MNE-Python data objects
throughout the application lifecycle.
"""

import os
import logging
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path

import mne
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class DataManager(QObject):
    """Manages MNE data objects and their metadata throughout the application.
    
    The DataManager serves as the central hub for all data operations in QuickLab,
    handling loading, saving, and tracking of MNE data objects (Raw, Epochs, Evoked, etc.).
    It provides signals for data change notifications and maintains data provenance.
    
    Signals
    -------
    data_loaded : str, object
        Emitted when new data is loaded (data_id, data_object)
    data_changed : str, object
        Emitted when existing data is modified (data_id, data_object)
    data_removed : str
        Emitted when data is removed (data_id)
    active_data_changed : str
        Emitted when the active data selection changes (data_id)
    """
    
    # Qt signals for data change notifications
    data_loaded = pyqtSignal(str, object)
    data_changed = pyqtSignal(str, object)
    data_removed = pyqtSignal(str)
    active_data_changed = pyqtSignal(str)
    
    def __init__(self) -> None:
        """Initialize the DataManager."""
        super().__init__()
        self._data_objects: Dict[str, Any] = {}
        self._data_metadata: Dict[str, Dict[str, Any]] = {}
        self._active_data_id: Optional[str] = None
        self._data_counter: int = 0
        
        logger.info("DataManager initialized")
    
    def load_data(self, 
                  file_path: Union[str, Path],
                  data_id: Optional[str] = None,
                  preload: bool = True) -> str:
        """Load neurophysiological data from file.
        
        Parameters
        ----------
        file_path : str or Path
            Path to the data file to load.
        data_id : str, optional
            Unique identifier for the data. If None, will be auto-generated.
        preload : bool, optional
            Whether to preload data into memory. Default is True.
            
        Returns
        -------
        str
            The data identifier for the loaded data.
            
        Raises
        ------
        ValueError
            If the file format is not supported or file doesn't exist.
        RuntimeError
            If data loading fails.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        
        if data_id is None:
            data_id = self._generate_data_id(file_path.name)
        
        try:
            # Determine file type and load accordingly
            data_obj = self._load_data_by_extension(file_path, preload)
            
            # Store data and metadata
            self._data_objects[data_id] = data_obj
            self._data_metadata[data_id] = {
                'file_path': str(file_path),
                'data_type': type(data_obj).__name__,
                'loaded_at': np.datetime64('now'),
                'preload': preload,
                'modified': False,
                'history': []
            }
            
            # Set as active if it's the first data loaded
            if self._active_data_id is None:
                self._active_data_id = data_id
                self.active_data_changed.emit(data_id)
            
            logger.info(f"Loaded {type(data_obj).__name__} data: {data_id}")
            self.data_loaded.emit(data_id, data_obj)
            
            return data_id
            
        except Exception as e:
            logger.error(f"Failed to load data from {file_path}: {e}")
            raise RuntimeError(f"Failed to load data: {e}") from e
    
    def _load_data_by_extension(self, file_path: Path, preload: bool) -> Any:
        """Load data based on file extension.
        
        Parameters
        ----------
        file_path : Path
            Path to the data file.
        preload : bool
            Whether to preload data into memory.
            
        Returns
        -------
        Any
            The loaded MNE data object.
        """
        suffix = file_path.suffix.lower()
        
        # Raw data formats
        if suffix == '.fif':
            return mne.io.read_raw_fif(file_path, preload=preload)
        elif suffix == '.edf':
            return mne.io.read_raw_edf(file_path, preload=preload)
        elif suffix == '.bdf':
            return mne.io.read_raw_bdf(file_path, preload=preload)
        elif suffix == '.gdf':
            return mne.io.read_raw_gdf(file_path, preload=preload)
        elif suffix == '.set':
            return mne.io.read_raw_eeglab(file_path, preload=preload)
        elif suffix == '.cnt':
            return mne.io.read_raw_cnt(file_path, preload=preload)
        elif suffix == '.vhdr':
            return mne.io.read_raw_brainvision(file_path, preload=preload)
        
        # Epochs data
        elif suffix == '.fif' and 'epo' in file_path.name:
            return mne.read_epochs(file_path, preload=preload)
        
        # Evoked data
        elif suffix == '.fif' and 'ave' in file_path.name:
            return mne.read_evokeds(file_path)
        
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def get_data(self, data_id: str) -> Any:
        """Get data object by ID.
        
        Parameters
        ----------
        data_id : str
            The data identifier.
            
        Returns
        -------
        Any
            The MNE data object.
            
        Raises
        ------
        KeyError
            If data_id is not found.
        """
        if data_id not in self._data_objects:
            raise KeyError(f"Data ID not found: {data_id}")
        
        return self._data_objects[data_id]
    
    def get_active_data(self) -> Tuple[Optional[str], Optional[Any]]:
        """Get the currently active data.
        
        Returns
        -------
        tuple
            (data_id, data_object) of the active data, or (None, None) if no data.
        """
        if self._active_data_id is None:
            return None, None
        
        return self._active_data_id, self._data_objects[self._active_data_id]
    
    def set_active_data(self, data_id: str) -> None:
        """Set the active data.
        
        Parameters
        ----------
        data_id : str
            The data identifier to set as active.
            
        Raises
        ------
        KeyError
            If data_id is not found.
        """
        if data_id not in self._data_objects:
            raise KeyError(f"Data ID not found: {data_id}")
        
        self._active_data_id = data_id
        self.active_data_changed.emit(data_id)
        logger.info(f"Active data changed to: {data_id}")
    
    def get_data_list(self) -> List[str]:
        """Get list of all loaded data IDs.
        
        Returns
        -------
        list
            List of data identifiers.
        """
        return list(self._data_objects.keys())
    
    def get_data_info(self, data_id: str) -> Dict[str, Any]:
        """Get metadata for a data object.
        
        Parameters
        ----------
        data_id : str
            The data identifier.
            
        Returns
        -------
        dict
            Dictionary containing data metadata.
            
        Raises
        ------
        KeyError
            If data_id is not found.
        """
        if data_id not in self._data_metadata:
            raise KeyError(f"Data ID not found: {data_id}")
        
        # Add runtime information
        data_obj = self._data_objects[data_id]
        info = self._data_metadata[data_id].copy()
        
        if hasattr(data_obj, 'info'):
            info.update({
                'n_channels': data_obj.info['nchan'],
                'sampling_rate': data_obj.info['sfreq'],
                'n_times': getattr(data_obj, 'n_times', None),
            })
        
        return info
    
    def update_data(self, data_id: str, data_obj: Any, operation: str = "modified") -> None:
        """Update existing data object.
        
        Parameters
        ----------
        data_id : str
            The data identifier.
        data_obj : Any
            The updated MNE data object.
        operation : str, optional
            Description of the operation performed. Default is "modified".
            
        Raises
        ------
        KeyError
            If data_id is not found.
        """
        if data_id not in self._data_objects:
            raise KeyError(f"Data ID not found: {data_id}")
        
        self._data_objects[data_id] = data_obj
        self._data_metadata[data_id]['modified'] = True
        self._data_metadata[data_id]['history'].append({
            'operation': operation,
            'timestamp': np.datetime64('now')
        })
        
        logger.info(f"Updated data: {data_id} ({operation})")
        self.data_changed.emit(data_id, data_obj)
    
    def remove_data(self, data_id: str) -> None:
        """Remove data from manager.
        
        Parameters
        ----------
        data_id : str
            The data identifier to remove.
            
        Raises
        ------
        KeyError
            If data_id is not found.
        """
        if data_id not in self._data_objects:
            raise KeyError(f"Data ID not found: {data_id}")
        
        del self._data_objects[data_id]
        del self._data_metadata[data_id]
        
        # Update active data if necessary
        if self._active_data_id == data_id:
            remaining_data = list(self._data_objects.keys())
            self._active_data_id = remaining_data[0] if remaining_data else None
            if self._active_data_id:
                self.active_data_changed.emit(self._active_data_id)
        
        logger.info(f"Removed data: {data_id}")
        self.data_removed.emit(data_id)
    
    def save_data(self, data_id: str, file_path: Union[str, Path], 
                  overwrite: bool = False) -> None:
        """Save data to file.
        
        Parameters
        ----------
        data_id : str
            The data identifier.
        file_path : str or Path
            Path where to save the data.
        overwrite : bool, optional
            Whether to overwrite existing files. Default is False.
            
        Raises
        ------
        KeyError
            If data_id is not found.
        FileExistsError
            If file exists and overwrite is False.
        """
        if data_id not in self._data_objects:
            raise KeyError(f"Data ID not found: {data_id}")
        
        file_path = Path(file_path)
        
        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File exists: {file_path}")
        
        data_obj = self._data_objects[data_id]
        
        try:
            # Save based on data type
            if hasattr(data_obj, 'save'):
                data_obj.save(file_path, overwrite=overwrite)
            else:
                raise ValueError(f"Cannot save data type: {type(data_obj)}")
            
            # Update metadata
            self._data_metadata[data_id]['file_path'] = str(file_path)
            self._data_metadata[data_id]['modified'] = False
            
            logger.info(f"Saved data: {data_id} to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save data {data_id}: {e}")
            raise RuntimeError(f"Failed to save data: {e}") from e
    
    def _generate_data_id(self, filename: str) -> str:
        """Generate a unique data ID.
        
        Parameters
        ----------
        filename : str
            The original filename.
            
        Returns
        -------
        str
            A unique data identifier.
        """
        base_name = Path(filename).stem
        self._data_counter += 1
        
        # Try base name first
        if base_name not in self._data_objects:
            return base_name
        
        # Add counter if name exists
        counter = 1
        while f"{base_name}_{counter}" in self._data_objects:
            counter += 1
        
        return f"{base_name}_{counter}"
    
    def clear_all_data(self) -> None:
        """Remove all data from manager."""
        data_ids = list(self._data_objects.keys())
        
        for data_id in data_ids:
            self.remove_data(data_id)
        
        self._data_counter = 0
        logger.info("Cleared all data from manager")