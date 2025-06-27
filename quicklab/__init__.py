"""PyMNE Studio: An advanced EEG/MEG analysis IDE for MNE-Python.

PyMNE Studio provides an intuitive, modular environment for neurophysiological
data analysis that combines the interactive capabilities of EEGLAB with
the robust data structures and analysis methods of MNE-Python.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.1.0-dev"

# Core imports
from .core.data_manager import DataManager
from .core.session_manager import SessionManager
from .core.event_system import EventSystem

# Main application
from .main import PyMNEStudioIDE

# Utility imports
from .utils import logger

__all__ = [
    "__version__",
    "DataManager", 
    "SessionManager",
    "EventSystem",
    "PyMNEStudioIDE",
    "logger",
]