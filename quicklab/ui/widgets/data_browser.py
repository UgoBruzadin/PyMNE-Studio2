"""Data browser widget for QuickLab."""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QPushButton, QMenu, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QContextMenuEvent

from ...core.data_manager import DataManager
from ...core.event_system import EventSystem, EventType, EventMixin
from ...utils.logger import get_logger

logger = get_logger(__name__)


class DataBrowser(QWidget, EventMixin):
    """Data browser widget for managing loaded data objects.
    
    The DataBrowser provides a tree view of all loaded data objects with
    context menus for data operations and information display.
    
    Parameters
    ----------
    data_manager : DataManager
        The data management system.
    event_system : EventSystem
        The event communication system.
    parent : QWidget, optional
        Parent widget.
    
    Signals
    -------
    data_selected : str
        Emitted when a data object is selected (data_id).
    """
    
    # Signals
    data_selected = pyqtSignal(str)
    
    def __init__(self, 
                 data_manager: DataManager,
                 event_system: EventSystem,
                 parent: Optional[QWidget] = None):
        """Initialize the DataBrowser."""
        super().__init__(parent)
        EventMixin.__init__(self)
        
        self.data_manager = data_manager
        self.event_system = event_system
        self.set_event_system(event_system)
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("DataBrowser initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Data Objects")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_button = QPushButton("🔄")
        self.refresh_button.setToolTip("Refresh data list")
        self.refresh_button.setMaximumWidth(30)
        self.refresh_button.clicked.connect(self._refresh_data_list)
        header_layout.addWidget(self.refresh_button)
        
        layout.addLayout(header_layout)
        
        # Data tree
        self.data_tree = QTreeWidget()
        self.data_tree.setHeaderLabels(["Name", "Type", "Channels", "Time Points"])
        self.data_tree.setRootIsDecorated(False)
        self.data_tree.setAlternatingRowColors(True)
        self.data_tree.itemClicked.connect(self._on_item_clicked)
        self.data_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.data_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.data_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.data_tree)
        
        # Info panel
        self.info_label = QLabel("No data loaded")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border: 1px solid #ccc;")
        layout.addWidget(self.info_label)
    
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        # Data manager signals
        self.data_manager.data_loaded.connect(self._on_data_loaded)
        self.data_manager.data_changed.connect(self._on_data_changed)
        self.data_manager.data_removed.connect(self._on_data_removed)
        self.data_manager.active_data_changed.connect(self._on_active_data_changed)
    
    def _refresh_data_list(self) -> None:
        """Refresh the data list display."""
        self.data_tree.clear()
        
        data_list = self.data_manager.get_data_list()
        active_id, _ = self.data_manager.get_active_data()
        
        for data_id in data_list:
            try:
                data_obj = self.data_manager.get_data(data_id)
                data_info = self.data_manager.get_data_info(data_id)
                
                # Create tree item
                item = QTreeWidgetItem([
                    data_id,
                    data_info.get('data_type', 'Unknown'),
                    str(data_info.get('n_channels', 'N/A')),
                    str(data_info.get('n_times', 'N/A'))
                ])
                
                # Store data ID in item
                item.setData(0, Qt.ItemDataRole.UserRole, data_id)
                
                # Highlight active data
                if data_id == active_id:
                    font = item.font(0)
                    font.setBold(True)
                    for col in range(self.data_tree.columnCount()):
                        item.setFont(col, font)
                
                self.data_tree.addTopLevelItem(item)
                
            except Exception as e:
                logger.error(f"Error adding data item {data_id}: {e}")
        
        # Resize columns to content
        for col in range(self.data_tree.columnCount()):
            self.data_tree.resizeColumnToContents(col)
        
        # Update info panel
        if data_list:
            self.info_label.setText(f"Loaded {len(data_list)} data object(s)")
        else:
            self.info_label.setText("No data loaded")
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item click."""
        data_id = item.data(0, Qt.ItemDataRole.UserRole)
        if data_id:
            try:
                data_info = self.data_manager.get_data_info(data_id)
                
                # Update info display
                info_text = f"<b>{data_id}</b><br>"
                info_text += f"Type: {data_info.get('data_type', 'Unknown')}<br>"
                info_text += f"Channels: {data_info.get('n_channels', 'N/A')}<br>"
                info_text += f"Sampling Rate: {data_info.get('sampling_rate', 'N/A')} Hz<br>"
                info_text += f"Modified: {'Yes' if data_info.get('modified', False) else 'No'}"
                
                self.info_label.setText(info_text)
                
                # Emit selection signal
                self.data_selected.emit(data_id)
                
            except Exception as e:
                logger.error(f"Error handling item click: {e}")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item double click - set as active data."""
        data_id = item.data(0, Qt.ItemDataRole.UserRole)
        if data_id:
            try:
                self.data_manager.set_active_data(data_id)
                logger.debug(f"Set active data: {data_id}")
            except Exception as e:
                logger.error(f"Error setting active data: {e}")
    
    def _show_context_menu(self, position) -> None:
        """Show context menu for data operations."""
        item = self.data_tree.itemAt(position)
        if not item:
            return
        
        data_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not data_id:
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Set as active action
        set_active_action = QAction("Set as Active", self)
        set_active_action.triggered.connect(lambda: self._set_active_data(data_id))
        menu.addAction(set_active_action)
        
        menu.addSeparator()
        
        # View properties action
        properties_action = QAction("Properties...", self)
        properties_action.triggered.connect(lambda: self._show_properties(data_id))
        menu.addAction(properties_action)
        
        # Export action
        export_action = QAction("Export...", self)
        export_action.triggered.connect(lambda: self._export_data(data_id))
        menu.addAction(export_action)
        
        menu.addSeparator()
        
        # Remove action
        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(lambda: self._remove_data(data_id))
        menu.addAction(remove_action)
        
        # Show menu
        menu.exec(self.data_tree.mapToGlobal(position))
    
    def _set_active_data(self, data_id: str) -> None:
        """Set data as active."""
        try:
            self.data_manager.set_active_data(data_id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set active data: {e}")
    
    def _show_properties(self, data_id: str) -> None:
        """Show data properties dialog."""
        try:
            data_info = self.data_manager.get_data_info(data_id)
            data_obj = self.data_manager.get_data(data_id)
            
            # Create properties text
            props_text = f"Data ID: {data_id}\\n"
            props_text += f"Type: {data_info.get('data_type', 'Unknown')}\\n"
            props_text += f"File: {data_info.get('file_path', 'N/A')}\\n"
            props_text += f"Channels: {data_info.get('n_channels', 'N/A')}\\n"
            props_text += f"Sampling Rate: {data_info.get('sampling_rate', 'N/A')} Hz\\n"
            props_text += f"Time Points: {data_info.get('n_times', 'N/A')}\\n"
            props_text += f"Loaded: {data_info.get('loaded_at', 'N/A')}\\n"
            props_text += f"Modified: {'Yes' if data_info.get('modified', False) else 'No'}\\n"
            
            # Add history if available
            history = data_info.get('history', [])
            if history:
                props_text += "\\nHistory:\\n"
                for entry in history[-5:]:  # Show last 5 operations
                    props_text += f"  - {entry.get('operation', 'Unknown')} at {entry.get('timestamp', 'N/A')}\\n"
            
            QMessageBox.information(self, f"Properties - {data_id}", props_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to show properties: {e}")
    
    def _export_data(self, data_id: str) -> None:
        """Export data object."""
        # TODO: Implement data export dialog
        QMessageBox.information(self, "Export", "Data export not yet implemented")
    
    def _remove_data(self, data_id: str) -> None:
        """Remove data object."""
        reply = QMessageBox.question(
            self, "Remove Data",
            f"Are you sure you want to remove '{data_id}'?\\n\\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.data_manager.remove_data(data_id)
                logger.info(f"Removed data: {data_id}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to remove data: {e}")
    
    # Event handlers
    def _on_data_loaded(self, data_id: str, data_obj) -> None:
        """Handle data loaded event."""
        self._refresh_data_list()
    
    def _on_data_changed(self, data_id: str, data_obj) -> None:
        """Handle data changed event."""
        self._refresh_data_list()
    
    def _on_data_removed(self, data_id: str) -> None:
        """Handle data removed event."""
        self._refresh_data_list()
    
    def _on_active_data_changed(self, data_id: str) -> None:
        """Handle active data changed event."""
        self._refresh_data_list()