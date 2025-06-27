"""Pytest configuration and fixtures for QuickLab tests."""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# Add the package root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_mne_data():
    """Create mock MNE data objects for testing."""
    mock_raw = Mock()
    mock_raw.info = {
        'nchan': 64,
        'sfreq': 1000.0,
        'ch_names': [f'Ch{i:02d}' for i in range(64)]
    }
    mock_raw.n_times = 10000
    mock_raw.save = Mock()
    
    return mock_raw


@pytest.fixture
def mock_qt_app():
    """Create a mock QApplication for GUI tests."""
    with patch('PyQt6.QtWidgets.QApplication') as mock_app:
        mock_app.instance.return_value = None
        yield mock_app


@pytest.fixture
def sample_data_file(tmp_path):
    """Create a sample data file for testing."""
    data_file = tmp_path / "sample_data.fif"
    data_file.write_text("mock data content")
    return data_file


@pytest.fixture
def temp_session_dir(tmp_path):
    """Create a temporary directory for session files."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    return session_dir