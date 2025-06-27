"""Comprehensive error handling utilities for PyMNE Studio."""

import sys
import traceback
import logging
from typing import Optional, Callable, Any, Dict
from functools import wraps
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox, QWidget, QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from .logger import get_logger

logger = get_logger(__name__)


class ErrorHandler(QObject):
    """Central error handler for PyMNE Studio.
    
    Provides comprehensive error handling, logging, and user notification
    while keeping the application running.
    
    Signals
    -------
    error_occurred : str, str, str
        Emitted when an error occurs (error_type, message, details).
    """
    
    error_occurred = pyqtSignal(str, str, str)
    
    def __init__(self):
        """Initialize the ErrorHandler."""
        super().__init__()
        self.error_count = 0
        self.error_log_file: Optional[Path] = None
        self._setup_error_logging()
        
        # Install global exception handler
        sys.excepthook = self.handle_exception
        
        logger.info("ErrorHandler initialized with global exception handling")
    
    def _setup_error_logging(self) -> None:
        """Set up error-specific logging."""
        try:
            log_dir = Path.home() / ".pymne-studio" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            self.error_log_file = log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
            
            # Create error-specific logger
            error_logger = logging.getLogger('pymne_studio.errors')
            error_logger.setLevel(logging.ERROR)
            
            if not error_logger.handlers:
                handler = logging.FileHandler(self.error_log_file)
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s\n%(exc_info)s\n'
                )
                handler.setFormatter(formatter)
                error_logger.addHandler(handler)
                
        except Exception as e:
            logger.warning(f"Could not set up error logging: {e}")
    
    def handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Handle uncaught exceptions.
        
        Parameters
        ----------
        exc_type : type
            Exception type.
        exc_value : Exception
            Exception instance.
        exc_traceback : traceback
            Exception traceback.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to work normally
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        self.error_count += 1
        
        # Format error information
        error_msg = str(exc_value)
        error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        error_type = exc_type.__name__
        
        # Log the error
        logger.error(f"Uncaught exception: {error_type}: {error_msg}")
        logger.debug(f"Traceback:\n{error_details}")
        
        # Log to error file
        if self.error_log_file:
            try:
                with open(self.error_log_file, 'a') as f:
                    f.write(f"\n{'='*50}\n")
                    f.write(f"Error #{self.error_count} - {datetime.now()}\n")
                    f.write(f"Type: {error_type}\n")
                    f.write(f"Message: {error_msg}\n")
                    f.write(f"Details:\n{error_details}\n")
            except Exception:
                pass  # Don't let error logging break the app
        
        # Emit signal for UI handling
        self.error_occurred.emit(error_type, error_msg, error_details)
        
        # Show user-friendly error dialog
        self.show_error_dialog(error_type, error_msg, error_details)
    
    def show_error_dialog(self, error_type: str, message: str, details: str) -> None:
        """Show user-friendly error dialog.
        
        Parameters
        ----------
        error_type : str
            Type of error.
        message : str
            Error message.
        details : str
            Detailed error information.
        """
        try:
            app = QApplication.instance()
            if app is None:
                return
            
            # Create error dialog
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("PyMNE Studio - Error Occurred")
            
            # Main message
            user_message = f"An error occurred but PyMNE Studio will continue running.\n\n"
            user_message += f"Error: {message}\n\n"
            user_message += f"If this error persists, please report it on GitHub."
            
            msg_box.setText(user_message)
            msg_box.setDetailedText(details)
            
            # Add buttons
            msg_box.setStandardButtons(
                QMessageBox.StandardButton.Ok | 
                QMessageBox.StandardButton.Ignore
            )
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Show dialog
            msg_box.exec()
            
        except Exception as e:
            # Fallback - just log if dialog fails
            logger.error(f"Failed to show error dialog: {e}")
    
    def handle_module_error(self, module_name: str, error: Exception, 
                          context: str = "") -> None:
        """Handle errors from specific modules.
        
        Parameters
        ----------
        module_name : str
            Name of the module where error occurred.
        error : Exception
            The exception that occurred.
        context : str, optional
            Additional context about the error.
        """
        self.error_count += 1
        
        error_msg = f"Error in {module_name}: {str(error)}"
        if context:
            error_msg += f" (Context: {context})"
        
        logger.error(error_msg)
        logger.debug(f"Exception details: {traceback.format_exc()}")
        
        # Emit signal
        self.error_occurred.emit(
            f"{module_name}Error", 
            str(error), 
            traceback.format_exc()
        )
        
        # Show warning (less intrusive than critical error)
        self.show_warning_dialog(module_name, str(error))
    
    def show_warning_dialog(self, module_name: str, message: str) -> None:
        """Show warning dialog for module errors.
        
        Parameters
        ----------
        module_name : str
            Name of the module.
        message : str
            Warning message.
        """
        try:
            app = QApplication.instance()
            if app is None:
                return
            
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(f"PyMNE Studio - {module_name} Warning")
            msg_box.setText(f"An issue occurred in {module_name}:\n\n{message}\n\nThe operation was cancelled but PyMNE Studio continues running.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            
        except Exception:
            pass  # Don't let warning dialog break the app
    
    def safe_execute(self, func: Callable, *args, module_name: str = "Unknown", 
                    context: str = "", **kwargs) -> Any:
        """Safely execute a function with error handling.
        
        Parameters
        ----------
        func : callable
            Function to execute safely.
        *args
            Arguments to pass to function.
        module_name : str
            Name of the module for error reporting.
        context : str
            Context description for error reporting.
        **kwargs
            Keyword arguments to pass to function.
            
        Returns
        -------
        Any
            Function result, or None if error occurred.
        """
        return safe_execute(func, *args, error_handler=self, 
                          module_name=module_name, context=context, **kwargs)


def safe_execute(func: Callable, *args, error_handler: Optional[ErrorHandler] = None, 
                module_name: str = "Unknown", context: str = "", **kwargs) -> Any:
    """Safely execute a function with error handling.
    
    Parameters
    ----------
    func : callable
        Function to execute safely.
    *args
        Arguments to pass to function.
    error_handler : ErrorHandler, optional
        Error handler instance.
    module_name : str
        Name of the module for error reporting.
    context : str
        Context description for error reporting.
    **kwargs
        Keyword arguments to pass to function.
        
    Returns
    -------
    Any
        Function result, or None if error occurred.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_handler:
            error_handler.handle_module_error(module_name, e, context)
        else:
            logger.error(f"Error in {module_name} ({context}): {e}")
        return None


# Add safe_execute method to ErrorHandler class
class ErrorHandlerExtension:
    """Extension methods for ErrorHandler class."""
    
    def safe_execute(self, func: Callable, *args, module_name: str = "Unknown", 
                    context: str = "", **kwargs) -> Any:
        """Instance method version of safe_execute."""
        return safe_execute(func, *args, error_handler=self, 
                          module_name=module_name, context=context, **kwargs)


def error_boundary(module_name: str = "", show_dialog: bool = True):
    """Decorator to create an error boundary around functions.
    
    Parameters
    ----------
    module_name : str
        Name of the module for error reporting.
    show_dialog : bool
        Whether to show error dialog to user.
        
    Returns
    -------
    callable
        Decorated function with error handling.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_name = module_name or func.__module__ or "Unknown"
                error_msg = f"Error in {error_name}.{func.__name__}: {str(e)}"
                
                logger.error(error_msg)
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if show_dialog:
                    try:
                        app = QApplication.instance()
                        if app:
                            msg_box = QMessageBox()
                            msg_box.setIcon(QMessageBox.Icon.Warning)
                            msg_box.setWindowTitle("PyMNE Studio - Operation Failed")
                            msg_box.setText(f"Operation failed but PyMNE Studio continues running.\n\nError: {str(e)}")
                            msg_box.exec()
                    except Exception:
                        pass  # Don't let dialog errors break anything
                
                return None
        
        return wrapper
    return decorator


def critical_error_boundary(func: Callable) -> Callable:
    """Decorator for critical functions that should never fail silently.
    
    Parameters
    ----------
    func : callable
        Function to wrap with critical error handling.
        
    Returns
    -------
    callable
        Decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"Critical error in {func.__name__}: {str(e)}"
            logger.critical(error_msg)
            logger.critical(f"Traceback: {traceback.format_exc()}")
            
            # Always show critical errors
            try:
                app = QApplication.instance()
                if app:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Critical)
                    msg_box.setWindowTitle("PyMNE Studio - Critical Error")
                    msg_box.setText(f"A critical error occurred:\n\n{str(e)}\n\nPlease restart PyMNE Studio.")
                    msg_box.exec()
            except Exception:
                print(f"CRITICAL ERROR: {error_msg}")  # Fallback to console
            
            raise  # Re-raise critical errors
    
    return wrapper


class ErrorRecovery:
    """Utilities for recovering from errors and maintaining application state."""
    
    @staticmethod
    def reset_widget_state(widget: QWidget) -> None:
        """Reset a widget to a safe state after an error.
        
        Parameters
        ----------
        widget : QWidget
            Widget to reset.
        """
        try:
            widget.setEnabled(True)
            widget.setVisible(True)
            # Clear any error styling
            widget.setStyleSheet("")
            logger.debug(f"Reset widget state: {widget.__class__.__name__}")
        except Exception as e:
            logger.warning(f"Failed to reset widget state: {e}")
    
    @staticmethod
    def safe_widget_operation(widget: QWidget, operation: Callable, 
                            *args, **kwargs) -> Any:
        """Safely perform an operation on a widget.
        
        Parameters
        ----------
        widget : QWidget
            Widget to operate on.
        operation : callable
            Operation to perform.
        *args, **kwargs
            Arguments for the operation.
            
        Returns
        -------
        Any
            Operation result, or None if failed.
        """
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Widget operation failed on {widget.__class__.__name__}: {e}")
            ErrorRecovery.reset_widget_state(widget)
            return None


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance.
    
    Returns
    -------
    ErrorHandler
        Global error handler instance.
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def initialize_error_handling() -> ErrorHandler:
    """Initialize global error handling for PyMNE Studio.
    
    Returns
    -------
    ErrorHandler
        Initialized error handler.
    """
    handler = get_error_handler()
    logger.info("Global error handling initialized")
    return handler