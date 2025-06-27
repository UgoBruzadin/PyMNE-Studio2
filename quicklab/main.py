"""Main PyMNE Studio application entry point."""

import sys
import logging
from typing import Optional, List
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from .core.data_manager import DataManager
from .core.event_system import EventSystem, EventType
from .core.session_manager import SessionManager
from .ui.main_window import MainWindow
from .utils.logger import get_logger, setup_file_logging

logger = get_logger(__name__)


class PyMNEStudioIDE:
    """Main PyMNE Studio IDE application.
    
    This class manages the overall application lifecycle, initializes core
    systems, and provides the main entry point for the PyMNE Studio IDE.
    
    Parameters
    ----------
    app_args : list, optional
        Command line arguments to pass to QApplication.
    """
    
    def __init__(self, app_args: Optional[List[str]] = None):
        """Initialize the PyMNE Studio IDE."""
        # Initialize Qt application
        if app_args is None:
            app_args = sys.argv
        
        # Check if QApplication already exists
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(app_args)
        
        # Set application properties
        self.app.setApplicationName("PyMNE Studio")
        self.app.setApplicationVersion("0.1.0")
        self.app.setOrganizationName("Ugo Bruzadin")
        self.app.setOrganizationDomain("github.com/UgoBruzadin")
        
        # Initialize core systems
        self.event_system = EventSystem()
        self.data_manager = DataManager()
        self.session_manager = SessionManager()
        
        # Connect core systems
        self._connect_core_systems()
        
        # Initialize main window
        self.main_window = MainWindow(
            data_manager=self.data_manager,
            event_system=self.event_system,
            session_manager=self.session_manager
        )
        
        # Set up logging
        self._setup_logging()
        
        logger.info("PyMNE Studio IDE initialized")
    
    def _connect_core_systems(self) -> None:
        """Connect core systems together."""
        # Connect data manager signals to event system
        self.data_manager.data_loaded.connect(
            lambda data_id, data_obj: self.event_system.publish_simple(
                EventType.DATA_LOADED, 
                "DataManager", 
                data_id=data_id, 
                data_type=type(data_obj).__name__
            )
        )
        
        self.data_manager.data_changed.connect(
            lambda data_id, data_obj: self.event_system.publish_simple(
                EventType.DATA_CHANGED,
                "DataManager",
                data_id=data_id,
                data_type=type(data_obj).__name__
            )
        )
        
        self.data_manager.data_removed.connect(
            lambda data_id: self.event_system.publish_simple(
                EventType.DATA_REMOVED,
                "DataManager",
                data_id=data_id
            )
        )
        
        self.data_manager.active_data_changed.connect(
            lambda data_id: self.event_system.publish_simple(
                EventType.ACTIVE_DATA_CHANGED,
                "DataManager",
                data_id=data_id
            )
        )
    
    def _setup_logging(self) -> None:
        """Set up application logging."""
        try:
            # Create logs directory in user's home
            log_dir = Path.home() / ".pymne-studio" / "logs"
            setup_file_logging(log_dir)
            logger.info(f"File logging set up in: {log_dir}")
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")
    
    def load_data(self, file_path: str, data_id: Optional[str] = None) -> str:
        """Load data into the application.
        
        Parameters
        ----------
        file_path : str
            Path to the data file to load.
        data_id : str, optional
            Unique identifier for the data.
            
        Returns
        -------
        str
            The data identifier for the loaded data.
        """
        return self.data_manager.load_data(file_path, data_id)
    
    def show(self) -> None:
        """Show the main application window."""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        
        logger.info("PyMNE Studio main window shown")
    
    def run(self) -> int:
        """Run the application event loop.
        
        Returns
        -------
        int
            Application exit code.
        """
        self.show()
        return self.app.exec()
    
    def quit(self) -> None:
        """Quit the application."""
        logger.info("Quitting PyMNE Studio")
        self.app.quit()


def main() -> int:
    """Main entry point for PyMNE Studio.
    
    Returns
    -------
    int
        Application exit code.
    """
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(
        description="PyMNE Studio: Advanced EEG/MEG Analysis IDE",
        prog="pymne-studio"
    )
    
    parser.add_argument(
        "data_file",
        nargs="?",
        help="Data file to load on startup"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="PyMNE Studio 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Set up logging level
    if args.debug:
        logging.getLogger('quicklab').setLevel(logging.DEBUG)
    
    try:
        # Initialize and run application
        app = PyMNEStudioIDE()
        
        # Load data file if provided
        if args.data_file:
            try:
                app.load_data(args.data_file)
                logger.info(f"Loaded data file: {args.data_file}")
            except Exception as e:
                logger.error(f"Failed to load data file {args.data_file}: {e}")
        
        return app.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())