"""Command line interface for QuickLab."""

import sys
import argparse
from pathlib import Path

from .main import main as main_gui
from .utils.logger import get_logger

logger = get_logger(__name__)


def main() -> int:
    """Main CLI entry point for QuickLab.
    
    Returns
    -------
    int
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="QuickLab: Advanced EEG/MEG Analysis IDE for MNE-Python",
        prog="quicklab"
    )
    
    parser.add_argument(
        "data_file",
        nargs="?",
        help="Data file to load on startup"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="QuickLab 0.1.0"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run without GUI (batch mode - not yet implemented)"
    )
    
    args = parser.parse_args()
    
    if args.no_gui:
        print("Batch mode not yet implemented")
        return 1
    
    # Run GUI application
    return main_gui()


if __name__ == "__main__":
    sys.exit(main())