"""Session management for QuickLab.

This module handles saving and loading of QuickLab sessions, which include
data objects, analysis results, and UI state.
"""

import json
import pickle
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

import h5py
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager(QObject):
    """Manages QuickLab sessions.
    
    The SessionManager handles saving and loading of complete analysis sessions,
    including data objects, preprocessing history, analysis results, and UI state.
    
    Signals
    -------
    session_loaded : str
        Emitted when a session is loaded (session_path)
    session_saved : str
        Emitted when a session is saved (session_path)
    """
    
    # Qt signals
    session_loaded = pyqtSignal(str)
    session_saved = pyqtSignal(str)
    
    def __init__(self) -> None:
        """Initialize the SessionManager."""
        super().__init__()
        self._current_session_path: Optional[Path] = None
        self._session_metadata: Dict[str, Any] = {}
        
        logger.info("SessionManager initialized")
    
    def save_session(self, 
                    session_path: Path,
                    data_manager,
                    ui_state: Optional[Dict[str, Any]] = None) -> None:
        """Save a QuickLab session.
        
        Parameters
        ----------
        session_path : Path
            Path where to save the session.
        data_manager : DataManager
            The data manager containing data objects.
        ui_state : dict, optional
            UI state information to save.
            
        Raises
        ------
        RuntimeError
            If session saving fails.
        """
        session_path = Path(session_path)
        
        try:
            # Create session directory if it doesn't exist
            session_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare session data
            session_data = {
                'metadata': {
                    'quicklab_version': '0.1.0',
                    'created_at': datetime.now().isoformat(),
                    'data_objects': [],
                    'ui_state': ui_state or {}
                },
                'data_objects': {},
                'analysis_results': {}
            }
            
            # Save data objects
            data_list = data_manager.get_data_list()
            for data_id in data_list:
                try:
                    data_obj = data_manager.get_data(data_id)
                    data_info = data_manager.get_data_info(data_id)
                    
                    # Save data object to separate file
                    data_file = session_path.parent / f"{session_path.stem}_{data_id}.fif"
                    data_obj.save(data_file, overwrite=True)
                    
                    # Store reference in session
                    session_data['data_objects'][data_id] = {
                        'file_path': str(data_file),
                        'data_type': data_info['data_type'],
                        'metadata': data_info
                    }
                    
                    session_data['metadata']['data_objects'].append(data_id)
                    
                except Exception as e:
                    logger.warning(f"Failed to save data object {data_id}: {e}")
            
            # Save session file
            with open(session_path, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            self._current_session_path = session_path
            self._session_metadata = session_data['metadata']
            
            logger.info(f"Session saved: {session_path}")
            self.session_saved.emit(str(session_path))
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise RuntimeError(f"Failed to save session: {e}") from e
    
    def load_session(self, 
                    session_path: Path,
                    data_manager) -> Dict[str, Any]:
        """Load a QuickLab session.
        
        Parameters
        ----------
        session_path : Path
            Path to the session file.
        data_manager : DataManager
            The data manager to load data into.
            
        Returns
        -------
        dict
            UI state information from the session.
            
        Raises
        ------
        FileNotFoundError
            If session file doesn't exist.
        RuntimeError
            If session loading fails.
        """
        session_path = Path(session_path)
        
        if not session_path.exists():
            raise FileNotFoundError(f"Session file not found: {session_path}")
        
        try:
            # Load session file
            with open(session_path, 'r') as f:
                session_data = json.load(f)
            
            # Clear existing data
            data_manager.clear_all_data()
            
            # Load data objects
            for data_id, data_info in session_data.get('data_objects', {}).items():
                try:
                    data_file = Path(data_info['file_path'])
                    if data_file.exists():
                        loaded_id = data_manager.load_data(data_file, data_id)
                        logger.debug(f"Loaded data object: {loaded_id}")
                    else:
                        logger.warning(f"Data file not found: {data_file}")
                        
                except Exception as e:
                    logger.warning(f"Failed to load data object {data_id}: {e}")
            
            # Store session info
            self._current_session_path = session_path
            self._session_metadata = session_data.get('metadata', {})
            
            logger.info(f"Session loaded: {session_path}")
            self.session_loaded.emit(str(session_path))
            
            # Return UI state
            return session_data.get('metadata', {}).get('ui_state', {})
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            raise RuntimeError(f"Failed to load session: {e}") from e
    
    def get_current_session_path(self) -> Optional[Path]:
        """Get the path of the currently loaded session.
        
        Returns
        -------
        Path or None
            Path to current session file, or None if no session loaded.
        """
        return self._current_session_path
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get metadata for the current session.
        
        Returns
        -------
        dict
            Session metadata.
        """
        return self._session_metadata.copy()
    
    def export_session_summary(self, output_path: Path) -> None:
        """Export a summary of the current session.
        
        Parameters
        ----------
        output_path : Path
            Path where to save the summary.
        """
        if not self._session_metadata:
            raise RuntimeError("No session loaded")
        
        summary = {
            'session_info': self._session_metadata,
            'export_time': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Session summary exported: {output_path}")