# PyMNE Studio

An advanced EEG/MEG analysis IDE inspired by EEGLAB, built for MNE-Python workflows.

## Overview

PyMNE Studio is a comprehensive graphical user interface for neurophysiological data analysis that combines the interactive capabilities of EEGLAB with the robust data structures and analysis methods of MNE-Python. It provides an intuitive, modular environment for EEG/MEG preprocessing, visualization, and analysis.

## Key Features

### 🔍 Advanced Data Visualization
- **eegplot_adv**: Enhanced continuous data plotting with multi-scale viewing
- **Interactive Epoch Browser**: Trial-by-trial data inspection with advanced selection tools
- **ICA Component Visualization**: Comprehensive ICA analysis with automated artifact detection
- **Real-time Scalp Topographies**: Dynamic topographic mapping with 3D head models

### ⚡ Intelligent Preprocessing
- **Interactive Pipeline Builder**: Drag-and-drop preprocessing workflow creation
- **Real-time Filter Preview**: Apply filters with immediate visual feedback
- **Advanced Referencing**: Multiple referencing schemes with preview capabilities
- **Automated Bad Channel Detection**: ML-powered artifact identification

### 🎯 Sophisticated Artifact Rejection
- **Manual Rejection Tools**: Advanced selection methods (lasso, magic wand, statistical)
- **Autoreject Integration**: Automated epoch rejection with cross-validation
- **ICA-based Cleaning**: Intelligent component classification and removal
- **Trial-by-Trial Analysis**: Comprehensive epoch-level quality control

### 📊 Comprehensive Analysis Suite
- **Frequency Analysis**: Power spectral density, connectivity, FOOOF integration
- **Time-Frequency Analysis**: Wavelet decomposition, cross-frequency coupling
- **ERP Analysis**: Advanced butterfly plots, peak detection, statistical analysis
- **Source Analysis**: Surface-based source reconstruction and ROI analysis

### 🔧 Extensible Architecture
- **Plugin System**: Custom analysis modules and extensions
- **Batch Processing**: Automated analysis pipelines for multiple datasets
- **BIDS Compatibility**: Full Brain Imaging Data Structure integration
- **Multi-format Export**: Support for various data formats and analysis results

## Installation

### Requirements
- Python 3.8+
- MNE-Python 1.4+
- PyQt6
- NumPy, SciPy, scikit-learn
- matplotlib, plotly

### Quick Install
```bash
# Clone the repository
git clone https://github.com/UgoBruzadin/PyMNE-Studio.git
cd PyMNE-Studio

# Install dependencies
pip install -r requirements.txt

# Install PyMNE Studio
pip install -e .

# Launch PyMNE Studio
pymne-studio
```

### Development Install
```bash
# Clone with development dependencies
git clone https://github.com/UgoBruzadin/PyMNE-Studio.git
cd PyMNE-Studio

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Build documentation
cd docs && make html
```

## Quick Start

### Loading Data
```python
import pymne_studio
from pymne_studio import PyMNEStudioIDE

# Launch the IDE
app = PyMNEStudioIDE()

# Load your MNE data
raw = mne.io.read_raw_fif('your_data.fif')
app.load_data(raw)

# Start interactive analysis
app.show()
```

### Basic Workflow
1. **Load Data**: Import EEG/MEG files in various formats
2. **Inspect**: Use eegplot_adv for initial data exploration  
3. **Preprocess**: Apply filters, referencing, and bad channel interpolation
4. **Clean**: Remove artifacts using manual and automated methods
5. **Epoch**: Extract trials around events of interest
6. **Analyze**: Perform frequency, time-frequency, or ERP analysis
7. **Export**: Save results in multiple formats

## Architecture

### Core Modules
- `core/`: Data management, session handling, event system
- `visualization/`: Advanced plotting widgets and interactive canvases
- `preprocessing/`: Filtering, referencing, interpolation interfaces
- `rejection/`: Artifact detection and removal tools
- `analysis/`: Frequency, time-frequency, and ERP analysis suites
- `ui/`: Main window, dockable widgets, themes
- `plugins/`: Extensible analysis modules

### Design Principles
- **Modular Architecture**: Independent, dockable analysis modules
- **MNE Integration**: Seamless compatibility with MNE-Python workflows
- **Performance Optimized**: Efficient handling of large neurophysiological datasets
- **User-Centric**: Intuitive interface designed for neuroscientists
- **Extensible**: Plugin system for custom analysis methods

## Documentation

- [User Guide](docs/user_guide/): Complete usage documentation
- [API Reference](docs/api/): Detailed API documentation  
- [Developer Guide](docs/developer/): Contributing and extending QuickLab
- [Tutorials](docs/tutorials/): Step-by-step analysis walkthroughs
- [Examples](examples/): Sample datasets and analysis scripts

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Reporting Issues
Please use the [GitHub Issues](https://github.com/UgoBruzadin/PyMNE-Studio/issues) page to report bugs or request features.

## License

PyMNE Studio is released under the BSD 3-Clause License. See [LICENSE](LICENSE) for details.

## Citation

If you use PyMNE Studio in your research, please cite:

```bibtex
@software{pymne_studio2024,
  title={PyMNE Studio: An Advanced EEG/MEG Analysis IDE for MNE-Python},
  author={Ugo Bruzadin},
  year={2024},
  url={https://github.com/UgoBruzadin/PyMNE-Studio}
}
```

## Acknowledgments

- **MNE-Python Team**: For the excellent neurophysiological analysis framework
- **EEGLAB Team**: For inspiration and design principles
- **Neuroscience Community**: For feedback and feature requests

## Support

- **Documentation**: [pymne-studio.readthedocs.io](https://pymne-studio.readthedocs.io)
- **Forum**: [GitHub Discussions](https://github.com/UgoBruzadin/PyMNE-Studio/discussions)
- **Email**: ugobruzadin@gmail.com

---

**PyMNE Studio**: Making neurophysiological data analysis more intuitive, powerful, and accessible.