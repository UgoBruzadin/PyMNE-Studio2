"""Event system for inter-module communication in QuickLab.

This module provides a centralized event system that allows different components
of QuickLab to communicate without tight coupling.
"""

import logging
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

from ..utils.logger import get_logger

logger = get_logger(__name__)


class EventType(Enum):
    """Enumeration of event types in QuickLab."""
    
    # Data events
    DATA_LOADED = "data_loaded"
    DATA_CHANGED = "data_changed"
    DATA_REMOVED = "data_removed"
    ACTIVE_DATA_CHANGED = "active_data_changed"
    
    # Analysis events
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    ANALYSIS_PROGRESS = "analysis_progress"
    
    # UI events
    MODULE_ACTIVATED = "module_activated"
    MODULE_DEACTIVATED = "module_deactivated"
    SELECTION_CHANGED = "selection_changed"
    VIEW_CHANGED = "view_changed"
    
    # Processing events
    PREPROCESSING_APPLIED = "preprocessing_applied"
    FILTER_APPLIED = "filter_applied"
    ARTIFACT_REJECTED = "artifact_rejected"
    ICA_COMPUTED = "ica_computed"
    
    # Session events
    SESSION_LOADED = "session_loaded"
    SESSION_SAVED = "session_saved"
    PROJECT_OPENED = "project_opened"
    PROJECT_CLOSED = "project_closed"


@dataclass
class Event:
    """Represents an event in the QuickLab event system.
    
    Parameters
    ----------
    event_type : EventType
        The type of event.
    source : str
        Identifier for the event source.
    data : dict, optional
        Additional event data.
    timestamp : float, optional
        Event timestamp (will be auto-generated if None).
    """
    
    event_type: EventType
    source: str
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            import time
            self.timestamp = time.time()
        
        if self.data is None:
            self.data = {}


class EventSystem(QObject):
    """Centralized event system for QuickLab.
    
    The EventSystem provides a publish-subscribe mechanism for communication
    between different modules in QuickLab. Components can subscribe to specific
    event types and will be notified when those events occur.
    
    Signals
    -------
    event_emitted : Event
        Emitted when any event is published through the system.
    """
    
    # Qt signal for event notifications
    event_emitted = pyqtSignal(object)
    
    def __init__(self) -> None:
        """Initialize the EventSystem."""
        super().__init__()
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history: int = 1000
        
        logger.info("EventSystem initialized")
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to subscribe to.
        callback : callable
            Function to call when the event occurs. Should accept an Event object.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to {event_type.value}: {callback.__name__}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to unsubscribe from.
        callback : callable
            The callback function to remove.
        """
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from {event_type.value}: {callback.__name__}")
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.
        
        Parameters
        ----------
        event : Event
            The event to publish.
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify Qt signal subscribers
        self.event_emitted.emit(event)
        
        # Notify direct subscribers
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback {callback.__name__}: {e}")
        
        logger.debug(f"Published event: {event.event_type.value} from {event.source}")
    
    def publish_simple(self, event_type: EventType, source: str, **kwargs) -> None:
        """Publish a simple event with keyword arguments as data.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to publish.
        source : str
            Identifier for the event source.
        **kwargs
            Additional data to include in the event.
        """
        event = Event(event_type=event_type, source=source, data=kwargs)
        self.publish(event)
    
    def get_event_history(self, event_type: Optional[EventType] = None,
                         source: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Event]:
        """Get event history with optional filtering.
        
        Parameters
        ----------
        event_type : EventType, optional
            Filter by event type.
        source : str, optional
            Filter by event source.
        limit : int, optional
            Maximum number of events to return.
            
        Returns
        -------
        list
            List of Event objects matching the criteria.
        """
        events = self._event_history
        
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        
        if source is not None:
            events = [e for e in events if e.source == source]
        
        if limit is not None:
            events = events[-limit:]
        
        return events
    
    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        logger.info("Event history cleared")
    
    def get_subscribers(self, event_type: EventType) -> List[Callable]:
        """Get list of subscribers for an event type.
        
        Parameters
        ----------
        event_type : EventType
            The event type to query.
            
        Returns
        -------
        list
            List of callback functions subscribed to the event type.
        """
        return self._subscribers.get(event_type, []).copy()
    
    def get_subscription_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type.
        
        Parameters
        ----------
        event_type : EventType
            The event type to query.
            
        Returns
        -------
        int
            Number of subscribers.
        """
        return len(self._subscribers.get(event_type, []))
    
    def unsubscribe_all(self, callback: Callable[[Event], None]) -> None:
        """Unsubscribe a callback from all event types.
        
        Parameters
        ----------
        callback : callable
            The callback function to remove from all subscriptions.
        """
        removed_count = 0
        for event_type in list(self._subscribers.keys()):
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                removed_count += 1
        
        logger.debug(f"Unsubscribed {callback.__name__} from {removed_count} event types")


class EventMixin:
    """Mixin class to add event capabilities to other classes.
    
    This mixin provides convenient methods for publishing and subscribing
    to events. Classes that inherit from this mixin should also set the
    `event_system` attribute to an EventSystem instance.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the EventMixin."""
        super().__init__(*args, **kwargs)
        self.event_system: Optional[EventSystem] = None
        self._subscriptions: List[tuple] = []  # Track our subscriptions
    
    def set_event_system(self, event_system: EventSystem) -> None:
        """Set the event system for this object.
        
        Parameters
        ----------
        event_system : EventSystem
            The event system to use.
        """
        self.event_system = event_system
    
    def emit_event(self, event_type: EventType, **kwargs) -> None:
        """Emit an event through the event system.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to emit.
        **kwargs
            Additional data to include in the event.
        """
        if self.event_system is not None:
            source_name = getattr(self, '__class__', type(self)).__name__
            self.event_system.publish_simple(event_type, source_name, **kwargs)
    
    def subscribe_to_event(self, event_type: EventType, 
                          callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to subscribe to.
        callback : callable
            Function to call when the event occurs.
        """
        if self.event_system is not None:
            self.event_system.subscribe(event_type, callback)
            self._subscriptions.append((event_type, callback))
    
    def unsubscribe_from_event(self, event_type: EventType,
                              callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type.
        
        Parameters
        ----------
        event_type : EventType
            The type of event to unsubscribe from.
        callback : callable
            The callback function to remove.
        """
        if self.event_system is not None:
            self.event_system.unsubscribe(event_type, callback)
            if (event_type, callback) in self._subscriptions:
                self._subscriptions.remove((event_type, callback))
    
    def cleanup_subscriptions(self) -> None:
        """Unsubscribe from all events when object is destroyed."""
        if self.event_system is not None:
            for event_type, callback in self._subscriptions:
                self.event_system.unsubscribe(event_type, callback)
            self._subscriptions.clear()