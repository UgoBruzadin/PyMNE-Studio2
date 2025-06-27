"""Dock manager for handling dockable widgets in QuickLab."""

from typing import Dict, Optional, Any, Type
from PyQt6.QtWidgets import QWidget, QDockWidget, QMainWindow
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from ...utils.logger import get_logger

logger = get_logger(__name__)


class DockManager(QObject):
    """Manages dockable widgets in the main window.
    
    The DockManager handles creation, positioning, and state management
    of dockable analysis modules in QuickLab.
    
    Parameters
    ----------
    main_window : QMainWindow
        The main application window.
    
    Signals
    -------
    dock_added : str, QDockWidget
        Emitted when a dock is added (dock_id, dock_widget).
    dock_removed : str
        Emitted when a dock is removed (dock_id).
    dock_visibility_changed : str, bool
        Emitted when dock visibility changes (dock_id, visible).
    """
    
    # Signals
    dock_added = pyqtSignal(str, QDockWidget)
    dock_removed = pyqtSignal(str)
    dock_visibility_changed = pyqtSignal(str, bool)
    
    def __init__(self, main_window: QMainWindow):
        """Initialize the DockManager."""
        super().__init__(main_window)
        
        self.main_window = main_window
        self.docks: Dict[str, QDockWidget] = {}
        self.dock_configs: Dict[str, Dict[str, Any]] = {}
        
        logger.debug("DockManager initialized")
    
    def add_dock(self, 
                 dock_id: str,
                 widget_class: Type[QWidget],
                 title: str,
                 area: Qt.DockWidgetArea = Qt.DockWidgetArea.TopDockWidgetArea,
                 widget_args: Optional[tuple] = None,
                 widget_kwargs: Optional[Dict[str, Any]] = None) -> QDockWidget:
        """Add a dockable widget.
        
        Parameters
        ----------
        dock_id : str
            Unique identifier for the dock.
        widget_class : Type[QWidget]
            Class of the widget to create.
        title : str
            Title for the dock widget.
        area : Qt.DockWidgetArea, optional
            Initial dock area. Default is TopDockWidgetArea.
        widget_args : tuple, optional
            Arguments to pass to widget constructor.
        widget_kwargs : dict, optional
            Keyword arguments to pass to widget constructor.
            
        Returns
        -------
        QDockWidget
            The created dock widget.
            
        Raises
        ------
        ValueError
            If dock_id already exists.
        """
        if dock_id in self.docks:
            raise ValueError(f"Dock with ID '{dock_id}' already exists")
        
        # Create widget instance
        if widget_args is None:
            widget_args = ()
        if widget_kwargs is None:
            widget_kwargs = {}
        
        try:
            widget = widget_class(*widget_args, **widget_kwargs)
        except Exception as e:
            logger.error(f"Failed to create widget for dock {dock_id}: {e}")
            raise
        
        # Create dock widget
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(dock_id)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        # Connect visibility signal
        dock.visibilityChanged.connect(
            lambda visible: self.dock_visibility_changed.emit(dock_id, visible)
        )
        
        # Add to main window
        self.main_window.addDockWidget(area, dock)
        
        # Store references
        self.docks[dock_id] = dock
        self.dock_configs[dock_id] = {
            'title': title,
            'widget_class': widget_class,
            'area': area,
            'widget_args': widget_args,
            'widget_kwargs': widget_kwargs
        }
        
        logger.debug(f"Added dock: {dock_id}")
        self.dock_added.emit(dock_id, dock)
        
        return dock
    
    def remove_dock(self, dock_id: str) -> None:
        """Remove a dockable widget.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock to remove.
            
        Raises
        ------
        KeyError
            If dock_id doesn't exist.
        """
        if dock_id not in self.docks:
            raise KeyError(f"Dock with ID '{dock_id}' not found")
        
        dock = self.docks[dock_id]
        
        # Remove from main window
        self.main_window.removeDockWidget(dock)
        
        # Clean up
        dock.deleteLater()
        del self.docks[dock_id]
        del self.dock_configs[dock_id]
        
        logger.debug(f"Removed dock: {dock_id}")
        self.dock_removed.emit(dock_id)
    
    def get_dock(self, dock_id: str) -> Optional[QDockWidget]:
        """Get a dock widget by ID.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock.
            
        Returns
        -------
        QDockWidget or None
            The dock widget, or None if not found.
        """
        return self.docks.get(dock_id)
    
    def get_dock_widget(self, dock_id: str) -> Optional[QWidget]:
        """Get the widget inside a dock.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock.
            
        Returns
        -------
        QWidget or None
            The widget inside the dock, or None if not found.
        """
        dock = self.docks.get(dock_id)
        return dock.widget() if dock else None
    
    def set_dock_visible(self, dock_id: str, visible: bool) -> None:
        """Set dock visibility.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock.
        visible : bool
            Whether the dock should be visible.
            
        Raises
        ------
        KeyError
            If dock_id doesn't exist.
        """
        if dock_id not in self.docks:
            raise KeyError(f"Dock with ID '{dock_id}' not found")
        
        self.docks[dock_id].setVisible(visible)
    
    def is_dock_visible(self, dock_id: str) -> bool:
        """Check if a dock is visible.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock.
            
        Returns
        -------
        bool
            True if dock is visible, False otherwise.
            
        Raises
        ------
        KeyError
            If dock_id doesn't exist.
        """
        if dock_id not in self.docks:
            raise KeyError(f"Dock with ID '{dock_id}' not found")
        
        return self.docks[dock_id].isVisible()
    
    def get_dock_list(self) -> list:
        """Get list of all dock IDs.
        
        Returns
        -------
        list
            List of dock identifiers.
        """
        return list(self.docks.keys())
    
    def tabify_docks(self, dock_ids: list) -> None:
        """Tabify multiple docks together.
        
        Parameters
        ----------
        dock_ids : list
            List of dock IDs to tabify together.
            
        Raises
        ------
        ValueError
            If any dock_id doesn't exist or list is too short.
        """
        if len(dock_ids) < 2:
            raise ValueError("Need at least 2 docks to tabify")
        
        # Check all docks exist
        for dock_id in dock_ids:
            if dock_id not in self.docks:
                raise KeyError(f"Dock with ID '{dock_id}' not found")
        
        # Tabify docks
        docks = [self.docks[dock_id] for dock_id in dock_ids]
        for i in range(1, len(docks)):
            self.main_window.tabifyDockWidget(docks[0], docks[i])
        
        # Raise the first dock
        docks[0].raise_()
        
        logger.debug(f"Tabified docks: {dock_ids}")
    
    def float_dock(self, dock_id: str, floating: bool = True) -> None:
        """Set dock floating state.
        
        Parameters
        ----------
        dock_id : str
            Identifier of the dock.
        floating : bool, optional
            Whether dock should be floating. Default is True.
            
        Raises
        ------
        KeyError
            If dock_id doesn't exist.
        """
        if dock_id not in self.docks:
            raise KeyError(f"Dock with ID '{dock_id}' not found")
        
        self.docks[dock_id].setFloating(floating)
    
    def reset_dock_layout(self) -> None:
        """Reset all docks to their default layout."""
        for dock_id, config in self.dock_configs.items():
            if dock_id in self.docks:
                dock = self.docks[dock_id]
                
                # Remove and re-add to reset position
                self.main_window.removeDockWidget(dock)
                self.main_window.addDockWidget(config['area'], dock)
                
                # Ensure visible
                dock.setVisible(True)
                dock.setFloating(False)
        
        logger.debug("Reset dock layout")
    
    def save_dock_state(self) -> Dict[str, Any]:
        """Save current dock state.
        
        Returns
        -------
        dict
            Dictionary containing dock state information.
        """
        state = {}
        
        for dock_id, dock in self.docks.items():
            state[dock_id] = {
                'visible': dock.isVisible(),
                'floating': dock.isFloating(),
                'geometry': dock.saveGeometry().data().hex() if dock.isFloating() else None
            }
        
        # Save main window dock state
        state['_window_state'] = self.main_window.saveState().data().hex()
        
        return state
    
    def restore_dock_state(self, state: Dict[str, Any]) -> None:
        """Restore dock state.
        
        Parameters
        ----------
        state : dict
            Dictionary containing dock state information.
        """
        try:
            # Restore main window state first
            if '_window_state' in state:
                window_state = bytes.fromhex(state['_window_state'])
                self.main_window.restoreState(window_state)
            
            # Restore individual dock states
            for dock_id, dock_state in state.items():
                if dock_id.startswith('_') or dock_id not in self.docks:
                    continue
                
                dock = self.docks[dock_id]
                
                # Set visibility
                if 'visible' in dock_state:
                    dock.setVisible(dock_state['visible'])
                
                # Set floating state and geometry
                if 'floating' in dock_state:
                    dock.setFloating(dock_state['floating'])
                    
                    if dock_state['floating'] and 'geometry' in dock_state and dock_state['geometry']:
                        geometry = bytes.fromhex(dock_state['geometry'])
                        dock.restoreGeometry(geometry)
            
            logger.debug("Restored dock state")
            
        except Exception as e:
            logger.warning(f"Failed to restore dock state: {e}")
            self.reset_dock_layout()