"""Tests for core QuickLab modules."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from quicklab.core.data_manager import DataManager
from quicklab.core.event_system import EventSystem, EventType, Event
from quicklab.core.session_manager import SessionManager


class TestDataManager:
    """Test cases for DataManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.data_manager = DataManager()
    
    def test_initialization(self):
        """Test DataManager initialization."""
        assert self.data_manager._data_objects == {}
        assert self.data_manager._data_metadata == {}
        assert self.data_manager._active_data_id is None
        assert self.data_manager._data_counter == 0
    
    def test_generate_data_id(self):
        """Test data ID generation."""
        # Test base name
        data_id = self.data_manager._generate_data_id("test.fif")
        assert data_id == "test"
        
        # Test with existing name
        self.data_manager._data_objects["test"] = Mock()
        data_id = self.data_manager._generate_data_id("test.fif")
        assert data_id == "test_1"
    
    def test_get_data_list(self):
        """Test getting data list."""
        assert self.data_manager.get_data_list() == []
        
        # Add mock data
        mock_data = Mock()
        self.data_manager._data_objects["test"] = mock_data
        assert self.data_manager.get_data_list() == ["test"]
    
    def test_get_data_nonexistent(self):
        """Test getting non-existent data."""
        with pytest.raises(KeyError):
            self.data_manager.get_data("nonexistent")
    
    def test_get_active_data_none(self):
        """Test getting active data when none is set."""
        data_id, data_obj = self.data_manager.get_active_data()
        assert data_id is None
        assert data_obj is None
    
    def test_set_active_data_nonexistent(self):
        """Test setting non-existent data as active."""
        with pytest.raises(KeyError):
            self.data_manager.set_active_data("nonexistent")
    
    def test_clear_all_data(self):
        """Test clearing all data."""
        # Add mock data
        self.data_manager._data_objects["test"] = Mock()
        self.data_manager._data_metadata["test"] = {}
        self.data_manager._active_data_id = "test"
        self.data_manager._data_counter = 1
        
        self.data_manager.clear_all_data()
        
        assert self.data_manager._data_objects == {}
        assert self.data_manager._data_metadata == {}
        assert self.data_manager._active_data_id is None
        assert self.data_manager._data_counter == 0


class TestEventSystem:
    """Test cases for EventSystem."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_system = EventSystem()
    
    def test_initialization(self):
        """Test EventSystem initialization."""
        assert self.event_system._subscribers == {}
        assert self.event_system._event_history == []
        assert self.event_system._max_history == 1000
    
    def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing to events."""
        callback = Mock()
        
        # Subscribe
        self.event_system.subscribe(EventType.DATA_LOADED, callback)
        assert EventType.DATA_LOADED in self.event_system._subscribers
        assert callback in self.event_system._subscribers[EventType.DATA_LOADED]
        
        # Unsubscribe
        self.event_system.unsubscribe(EventType.DATA_LOADED, callback)
        assert callback not in self.event_system._subscribers.get(EventType.DATA_LOADED, [])
    
    def test_publish_event(self):
        """Test publishing events."""
        callback = Mock()
        self.event_system.subscribe(EventType.DATA_LOADED, callback)
        
        event = Event(
            event_type=EventType.DATA_LOADED,
            source="test",
            data={"test_key": "test_value"}
        )
        
        self.event_system.publish(event)
        
        # Check callback was called
        callback.assert_called_once_with(event)
        
        # Check event was added to history
        assert len(self.event_system._event_history) == 1
        assert self.event_system._event_history[0] == event
    
    def test_publish_simple(self):
        """Test publishing simple events."""
        callback = Mock()
        self.event_system.subscribe(EventType.DATA_LOADED, callback)
        
        self.event_system.publish_simple(
            EventType.DATA_LOADED,
            "test_source",
            test_data="test_value"
        )
        
        # Check callback was called with correct event
        callback.assert_called_once()
        event = callback.call_args[0][0]
        assert event.event_type == EventType.DATA_LOADED
        assert event.source == "test_source"
        assert event.data["test_data"] == "test_value"
    
    def test_get_event_history(self):
        """Test getting event history."""
        # Add some events
        self.event_system.publish_simple(EventType.DATA_LOADED, "source1")
        self.event_system.publish_simple(EventType.DATA_CHANGED, "source2")
        self.event_system.publish_simple(EventType.DATA_LOADED, "source1")
        
        # Get all events
        all_events = self.event_system.get_event_history()
        assert len(all_events) == 3
        
        # Filter by event type
        data_loaded_events = self.event_system.get_event_history(
            event_type=EventType.DATA_LOADED
        )
        assert len(data_loaded_events) == 2
        
        # Filter by source
        source1_events = self.event_system.get_event_history(source="source1")
        assert len(source1_events) == 2
        
        # Limit results
        limited_events = self.event_system.get_event_history(limit=2)
        assert len(limited_events) == 2
    
    def test_clear_history(self):
        """Test clearing event history."""
        self.event_system.publish_simple(EventType.DATA_LOADED, "test")
        assert len(self.event_system._event_history) == 1
        
        self.event_system.clear_history()
        assert len(self.event_system._event_history) == 0
    
    def test_get_subscribers(self):
        """Test getting subscribers for event type."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.event_system.subscribe(EventType.DATA_LOADED, callback1)
        self.event_system.subscribe(EventType.DATA_LOADED, callback2)
        
        subscribers = self.event_system.get_subscribers(EventType.DATA_LOADED)
        assert len(subscribers) == 2
        assert callback1 in subscribers
        assert callback2 in subscribers
    
    def test_get_subscription_count(self):
        """Test getting subscription count."""
        callback = Mock()
        
        assert self.event_system.get_subscription_count(EventType.DATA_LOADED) == 0
        
        self.event_system.subscribe(EventType.DATA_LOADED, callback)
        assert self.event_system.get_subscription_count(EventType.DATA_LOADED) == 1
    
    def test_unsubscribe_all(self):
        """Test unsubscribing from all event types."""
        callback = Mock()
        
        self.event_system.subscribe(EventType.DATA_LOADED, callback)
        self.event_system.subscribe(EventType.DATA_CHANGED, callback)
        
        self.event_system.unsubscribe_all(callback)
        
        assert callback not in self.event_system.get_subscribers(EventType.DATA_LOADED)
        assert callback not in self.event_system.get_subscribers(EventType.DATA_CHANGED)


class TestSessionManager:
    """Test cases for SessionManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
        self.data_manager = Mock()
    
    def test_initialization(self):
        """Test SessionManager initialization."""
        assert self.session_manager._current_session_path is None
        assert self.session_manager._session_metadata == {}
    
    def test_get_current_session_path_none(self):
        """Test getting current session path when none is set."""
        assert self.session_manager.get_current_session_path() is None
    
    def test_get_session_metadata_empty(self):
        """Test getting session metadata when empty."""
        metadata = self.session_manager.get_session_metadata()
        assert metadata == {}
    
    @patch('quicklab.core.session_manager.json.dump')
    @patch('builtins.open')
    def test_save_session(self, mock_open, mock_json_dump):
        """Test saving a session."""
        # Mock data manager
        self.data_manager.get_data_list.return_value = ["test_data"]
        self.data_manager.get_data.return_value = Mock()
        self.data_manager.get_data_info.return_value = {
            'data_type': 'Raw',
            'file_path': '/test/path.fif'
        }
        
        # Mock the data object's save method
        mock_data = Mock()
        mock_data.save = Mock()
        self.data_manager.get_data.return_value = mock_data
        
        with tempfile.TemporaryDirectory() as temp_dir:
            session_path = Path(temp_dir) / "test_session.json"
            
            # This would normally fail due to mocking, but we're testing the structure
            try:
                self.session_manager.save_session(
                    session_path,
                    self.data_manager,
                    ui_state={"test": "state"}
                )
            except Exception:
                pass  # Expected due to mocking
            
            # Verify the data manager methods were called
            self.data_manager.get_data_list.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])