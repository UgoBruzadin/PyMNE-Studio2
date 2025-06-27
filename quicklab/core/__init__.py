"""Core QuickLab modules for data management and system architecture."""

from .data_manager import DataManager
from .session_manager import SessionManager
from .event_system import EventSystem
from .pipeline_manager import PipelineManager

__all__ = [
    "DataManager",
    "SessionManager", 
    "EventSystem",
    "PipelineManager",
]