"""Main application window for QuickLab."""

import sys
from typing import Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QMenuBar, QToolBar, QStatusBar, QDockWidget,
    QAction, QFileDialog, QMessageBox, QApplication,
    QSplitter, QTabWidget
)
from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QIcon

from ..core.data_manager import DataManager
from ..core.event_system import EventSystem, EventType, EventMixin
from ..core.session_manager import SessionManager
from .widgets.dock_manager import DockManager
from .widgets.data_browser import DataBrowser
from .widgets.status_widget import StatusWidget
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow, EventMixin):
    """Main application window for QuickLab.
    
    The MainWindow provides the primary interface for QuickLab, managing
    the overall layout, menus, toolbars, and dockable modules.
    
    Parameters
    ----------
    data_manager : DataManager
        The data management system.
    event_system : EventSystem
        The event communication system.
    session_manager : SessionManager
        The session management system.
    parent : QWidget, optional
        Parent widget.
    """
    
    # Signals
    closing = pyqtSignal()
    
    def __init__(self, 
                 data_manager: DataManager,
                 event_system: EventSystem,
                 session_manager: SessionManager,
                 parent: Optional[QWidget] = None):
        """Initialize the MainWindow."""
        super().__init__(parent)
        EventMixin.__init__(self)
        
        # Store core systems
        self.data_manager = data_manager
        self.event_system = event_system
        self.session_manager = session_manager
        self.set_event_system(event_system)
        
        # Window properties
        self.setWindowTitle("QuickLab - EEG/MEG Analysis IDE")
        self.setMinimumSize(1200, 800)
        self.resize(1600, 1000)
        
        # Settings
        self.settings = QSettings()
        
        # Initialize UI components
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbars()
        self._setup_status_bar()
        self._setup_dockable_modules()
        self._connect_signals()
        self._restore_settings()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        # Central widget with splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)
        
        # Data browser on the left
        self.data_browser = DataBrowser(self.data_manager, self.event_system)
        self.main_splitter.addWidget(self.data_browser)
        
        # Main content area (will be populated with dockable modules)
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.main_splitter.addWidget(self.content_area)
        
        # Set initial splitter sizes (20% for browser, 80% for content)
        self.main_splitter.setSizes([200, 800])
        
        # Initialize dock manager
        self.dock_manager = DockManager(self)
    
    def _setup_menus(self) -> None:
        """Set up the application menus."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # Open action
        self.open_action = QAction("&Open Data...", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setStatusTip("Open neurophysiological data file")
        self.open_action.triggered.connect(self._open_data_file)
        file_menu.addAction(self.open_action)
        
        # Save action
        self.save_action = QAction("&Save Data...", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setStatusTip("Save current data")
        self.save_action.triggered.connect(self._save_data_file)
        self.save_action.setEnabled(False)
        file_menu.addAction(self.save_action)
        
        file_menu.addSeparator()
        
        # Session actions
        self.new_session_action = QAction("&New Session", self)
        self.new_session_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_session_action.triggered.connect(self._new_session)
        file_menu.addAction(self.new_session_action)
        
        self.open_session_action = QAction("Open &Session...", self)
        self.open_session_action.triggered.connect(self._open_session)
        file_menu.addAction(self.open_session_action)
        
        self.save_session_action = QAction("Save Session &As...", self)
        self.save_session_action.triggered.connect(self._save_session)
        file_menu.addAction(self.save_session_action)
        
        file_menu.addSeparator()
        
        # Exit action
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.setStatusTip("Exit QuickLab")
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Module visibility actions (will be populated by dock manager)
        self.modules_menu = view_menu.addMenu("&Modules")
        
        view_menu.addSeparator()
        
        # Reset layout action
        self.reset_layout_action = QAction("&Reset Layout", self)
        self.reset_layout_action.triggered.connect(self._reset_layout)
        view_menu.addAction(self.reset_layout_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Preprocessing submenu
        preprocessing_menu = tools_menu.addMenu("&Preprocessing")
        
        # Analysis submenu
        analysis_menu = tools_menu.addMenu("&Analysis")
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # About action
        self.about_action = QAction("&About QuickLab", self)
        self.about_action.triggered.connect(self._show_about)
        help_menu.addAction(self.about_action)
        
        # Documentation action
        self.docs_action = QAction("&Documentation", self)
        self.docs_action.triggered.connect(self._show_docs)
        help_menu.addAction(self.docs_action)
    
    def _setup_toolbars(self) -> None:
        """Set up application toolbars."""
        # Main toolbar
        self.main_toolbar = self.addToolBar("Main")
        self.main_toolbar.setObjectName("MainToolBar")
        
        # Add file actions to toolbar
        self.main_toolbar.addAction(self.open_action)
        self.main_toolbar.addAction(self.save_action)
        self.main_toolbar.addSeparator()
        
        # Analysis toolbar
        self.analysis_toolbar = self.addToolBar("Analysis")
        self.analysis_toolbar.setObjectName("AnalysisToolBar")
        
        # Module-specific toolbars will be added by the dock manager
    
    def _setup_status_bar(self) -> None:
        """Set up the status bar."""
        self.status_bar = self.statusBar()
        
        # Status widget for detailed information
        self.status_widget = StatusWidget()
        self.status_bar.addPermanentWidget(self.status_widget)
        
        # Default message
        self.status_bar.showMessage("Ready")
    
    def _setup_dockable_modules(self) -> None:
        """Set up dockable analysis modules."""
        # This will be implemented by the dock manager
        # For now, we'll create placeholder docks
        
        # Raw data viewer dock
        raw_dock = QDockWidget("Raw Data Viewer", self)
        raw_dock.setObjectName("RawDataViewer")
        raw_widget = QWidget()  # Placeholder
        raw_dock.setWidget(raw_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, raw_dock)
        
        # Epochs viewer dock
        epochs_dock = QDockWidget("Epochs Viewer", self)
        epochs_dock.setObjectName("EpochsViewer")
        epochs_widget = QWidget()  # Placeholder
        epochs_dock.setWidget(epochs_widget)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, epochs_dock)
        
        # ICA viewer dock
        ica_dock = QDockWidget("ICA Components", self)
        ica_dock.setObjectName("ICAViewer")
        ica_widget = QWidget()  # Placeholder
        ica_dock.setWidget(ica_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, ica_dock)
        
        # Preprocessing dock
        preprocessing_dock = QDockWidget("Preprocessing", self)
        preprocessing_dock.setObjectName("Preprocessing")
        preprocessing_widget = QWidget()  # Placeholder
        preprocessing_dock.setWidget(preprocessing_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, preprocessing_dock)
        
        # Store docks for later reference
        self.docks = {
            'raw_viewer': raw_dock,
            'epochs_viewer': epochs_dock,
            'ica_viewer': ica_dock,
            'preprocessing': preprocessing_dock,
        }
        
        # Add dock visibility actions to menu
        for name, dock in self.docks.items():
            action = dock.toggleViewAction()
            self.modules_menu.addAction(action)
    
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        # Data manager signals
        self.data_manager.data_loaded.connect(self._on_data_loaded)
        self.data_manager.data_changed.connect(self._on_data_changed)
        self.data_manager.data_removed.connect(self._on_data_removed)
        self.data_manager.active_data_changed.connect(self._on_active_data_changed)
        
        # Event system subscription
        self.subscribe_to_event(EventType.ANALYSIS_STARTED, self._on_analysis_started)
        self.subscribe_to_event(EventType.ANALYSIS_COMPLETED, self._on_analysis_completed)
        self.subscribe_to_event(EventType.ANALYSIS_FAILED, self._on_analysis_failed)
    
    def _restore_settings(self) -> None:
        """Restore window settings from previous session."""
        # Restore geometry
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # Restore window state (docks, toolbars)
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
        
        # Restore splitter state
        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.main_splitter.restoreState(splitter_state)
    
    def _save_settings(self) -> None:
        """Save window settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("splitterState", self.main_splitter.saveState())
    
    def _open_data_file(self) -> None:
        """Open a data file dialog and load the selected file."""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Open Data File")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        # Set file filters for supported formats
        filters = [
            "All Supported (*.fif *.edf *.bdf *.gdf *.set *.cnt *.vhdr)",
            "FIF files (*.fif)",
            "EDF files (*.edf)",
            "BDF files (*.bdf)",
            "GDF files (*.gdf)",
            "EEGLAB files (*.set)",
            "CNT files (*.cnt)",
            "BrainVision files (*.vhdr)",
            "All files (*.*)"
        ]
        file_dialog.setNameFilters(filters)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            try:
                data_id = self.data_manager.load_data(file_path)
                self.status_bar.showMessage(f"Loaded data: {data_id}", 3000)
                logger.info(f"Loaded data file: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Loading Data", 
                                   f"Failed to load data file:\n{e}")
                logger.error(f"Failed to load data file {file_path}: {e}")
    
    def _save_data_file(self) -> None:
        """Save the current active data."""
        active_id, active_data = self.data_manager.get_active_data()
        if active_data is None:
            QMessageBox.information(self, "No Data", "No data to save.")
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Save Data File")
        file_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        file_dialog.setDefaultSuffix("fif")
        
        filters = ["FIF files (*.fif)", "All files (*.*)"]
        file_dialog.setNameFilters(filters)
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            try:
                self.data_manager.save_data(active_id, file_path, overwrite=True)
                self.status_bar.showMessage(f"Saved data: {active_id}", 3000)
                logger.info(f"Saved data to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error Saving Data",
                                   f"Failed to save data:\n{e}")
                logger.error(f"Failed to save data: {e}")
    
    def _new_session(self) -> None:
        """Create a new session."""
        # TODO: Implement session management
        self.status_bar.showMessage("New session created", 2000)
    
    def _open_session(self) -> None:
        """Open a session file."""
        # TODO: Implement session loading
        self.status_bar.showMessage("Session loading not yet implemented", 2000)
    
    def _save_session(self) -> None:
        """Save the current session."""
        # TODO: Implement session saving
        self.status_bar.showMessage("Session saving not yet implemented", 2000)
    
    def _reset_layout(self) -> None:
        """Reset the window layout to default."""
        # Reset dock positions
        for dock in self.docks.values():
            dock.setVisible(True)
        
        # Reset to default layout
        self.main_splitter.setSizes([200, 800])
        self.status_bar.showMessage("Layout reset", 2000)
    
    def _show_about(self) -> None:
        """Show the About dialog."""
        QMessageBox.about(self, "About QuickLab",
                         "<h3>QuickLab 0.1.0</h3>"
                         "<p>An advanced EEG/MEG analysis IDE for MNE-Python</p>"
                         "<p>Built with PyQt6 and MNE-Python</p>"
                         "<p>© 2024 QuickLab Development Team</p>")
    
    def _show_docs(self) -> None:
        """Open the documentation."""
        import webbrowser
        webbrowser.open("https://quicklab.readthedocs.io")
    
    # Event handling methods
    def _on_data_loaded(self, data_id: str, data_obj: Any) -> None:
        """Handle data loaded event."""
        self.save_action.setEnabled(True)
        self.status_widget.update_data_info(data_id, data_obj)
        logger.debug(f"UI updated for loaded data: {data_id}")
    
    def _on_data_changed(self, data_id: str, data_obj: Any) -> None:
        """Handle data changed event."""
        self.status_widget.update_data_info(data_id, data_obj)
        logger.debug(f"UI updated for changed data: {data_id}")
    
    def _on_data_removed(self, data_id: str) -> None:
        """Handle data removed event."""
        if not self.data_manager.get_data_list():
            self.save_action.setEnabled(False)
        logger.debug(f"UI updated for removed data: {data_id}")
    
    def _on_active_data_changed(self, data_id: str) -> None:
        """Handle active data changed event."""
        active_id, active_data = self.data_manager.get_active_data()
        if active_data:
            self.status_widget.update_data_info(active_id, active_data)
        logger.debug(f"UI updated for active data change: {data_id}")
    
    def _on_analysis_started(self, event) -> None:
        """Handle analysis started event."""
        self.status_bar.showMessage(f"Analysis started: {event.data.get('analysis_type', 'Unknown')}")
    
    def _on_analysis_completed(self, event) -> None:
        """Handle analysis completed event."""
        self.status_bar.showMessage(f"Analysis completed: {event.data.get('analysis_type', 'Unknown')}", 3000)
    
    def _on_analysis_failed(self, event) -> None:
        """Handle analysis failed event."""
        error_msg = event.data.get('error', 'Unknown error')
        self.status_bar.showMessage(f"Analysis failed: {error_msg}", 5000)
        QMessageBox.warning(self, "Analysis Failed", f"Analysis failed:\n{error_msg}")
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Save settings
        self._save_settings()
        
        # Clean up subscriptions
        self.cleanup_subscriptions()
        
        # Emit closing signal
        self.closing.emit()
        
        # Accept the close event
        event.accept()
        logger.info("MainWindow closed")