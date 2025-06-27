"""Status widget for displaying application status information."""

from typing import Optional, Any
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer

from ...utils.logger import get_logger

logger = get_logger(__name__)


class StatusWidget(QWidget):
    """Status widget for the main window status bar.
    
    Displays information about the current data, memory usage, and
    operation status.
    
    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the StatusWidget."""
        super().__init__(parent)
        
        self._setup_ui()
        self._setup_timer()
        
        logger.debug("StatusWidget initialized")
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Data info label
        self.data_label = QLabel("No data")
        self.data_label.setMinimumWidth(150)
        layout.addWidget(self.data_label)
        
        # Separator
        separator1 = QLabel("|")
        separator1.setStyleSheet("color: gray;")
        layout.addWidget(separator1)
        
        # Memory usage label
        self.memory_label = QLabel("Memory: 0 MB")
        self.memory_label.setMinimumWidth(100)
        layout.addWidget(self.memory_label)
        
        # Separator
        separator2 = QLabel("|")
        separator2.setStyleSheet("color: gray;")
        layout.addWidget(separator2)
        
        # Progress/status label
        self.status_label = QLabel("Ready")
        self.status_label.setMinimumWidth(80)
        layout.addWidget(self.status_label)
    
    def _setup_timer(self) -> None:
        """Set up timer for periodic updates."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_memory_usage)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def update_data_info(self, data_id: str, data_obj: Any) -> None:
        """Update data information display.
        
        Parameters
        ----------
        data_id : str
            The data identifier.
        data_obj : Any
            The MNE data object.
        """
        try:
            if hasattr(data_obj, 'info'):
                n_channels = data_obj.info['nchan']
                sfreq = data_obj.info['sfreq']
                
                if hasattr(data_obj, 'n_times'):
                    duration = data_obj.n_times / sfreq
                    info_text = f"{data_id}: {n_channels}ch, {sfreq:.0f}Hz, {duration:.1f}s"
                else:
                    info_text = f"{data_id}: {n_channels}ch, {sfreq:.0f}Hz"
            else:
                info_text = f"{data_id}: {type(data_obj).__name__}"
            
            self.data_label.setText(info_text)
            
        except Exception as e:
            logger.warning(f"Error updating data info: {e}")
            self.data_label.setText(f"{data_id}: Error")
    
    def _update_memory_usage(self) -> None:
        """Update memory usage display."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_label.setText(f"Memory: {memory_mb:.0f} MB")
            
        except ImportError:
            # psutil not available
            self.memory_label.setText("Memory: N/A")
        except Exception as e:
            logger.debug(f"Error updating memory usage: {e}")
    
    def set_status(self, status: str, timeout: Optional[int] = None) -> None:
        """Set status message.
        
        Parameters
        ----------
        status : str
            Status message to display.
        timeout : int, optional
            Timeout in milliseconds to clear the message.
        """
        self.status_label.setText(status)
        
        if timeout:
            QTimer.singleShot(timeout, lambda: self.status_label.setText("Ready"))
    
    def clear_data_info(self) -> None:
        """Clear data information display."""
        self.data_label.setText("No data")
    
    def set_progress(self, progress: int, operation: str = "") -> None:
        """Set progress information.
        
        Parameters
        ----------
        progress : int
            Progress percentage (0-100).
        operation : str, optional
            Description of the operation.
        """
        if operation:
            self.status_label.setText(f"{operation}: {progress}%")
        else:
            self.status_label.setText(f"Progress: {progress}%")
    
    def clear_progress(self) -> None:
        """Clear progress display."""
        self.status_label.setText("Ready")