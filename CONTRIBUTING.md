# Contributing to QuickLab

We welcome contributions to QuickLab! This document provides guidelines for contributing to the project.

## Getting Started

### Development Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/quicklab.git
   cd quicklab
   ```

3. **Create a development environment**:
   ```bash
   # Using conda (recommended)
   conda create -n quicklab-dev python=3.9
   conda activate quicklab-dev
   
   # Or using venv
   python -m venv quicklab-dev
   source quicklab-dev/bin/activate  # On Windows: quicklab-dev\Scripts\activate
   ```

4. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

5. **Set up pre-commit hooks**:
   ```bash
   pre-commit install
   ```

## Development Workflow

### Creating a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### Code Style

We use several tools to maintain code quality:

#### Black (Code Formatting)
```bash
black quicklab/
```

#### isort (Import Sorting)
```bash
isort quicklab/
```

#### flake8 (Linting)
```bash
flake8 quicklab/
```

#### mypy (Type Checking)
```bash
mypy quicklab/
```

#### Run All Quality Checks
```bash
# This runs all checks at once
pre-commit run --all-files
```

### Testing

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=quicklab

# Run specific test file
pytest tests/test_core.py

# Run tests with GUI (requires display)
pytest tests/test_ui.py --no-xvfb
```

#### Writing Tests
- Place tests in the `tests/` directory
- Use descriptive test names: `test_function_name_expected_behavior`
- Test both success and failure cases
- Use fixtures for common setup
- Mock external dependencies

Example test:
```python
import pytest
from quicklab.core.data_manager import DataManager

def test_data_manager_load_raw_data():
    """Test that DataManager can load raw MNE data."""
    manager = DataManager()
    # Test implementation here
    assert manager.loaded_data is not None
```

### Documentation

#### Docstring Format
We use NumPy-style docstrings:

```python
def process_data(data, method='average'):
    """Process EEG data using specified method.
    
    Parameters
    ----------
    data : mne.io.Raw
        The raw EEG data to process.
    method : str, optional
        Processing method to use. Default is 'average'.
        
    Returns
    -------
    processed_data : mne.io.Raw
        The processed EEG data.
        
    Raises
    ------
    ValueError
        If method is not recognized.
        
    Examples
    --------
    >>> from quicklab.core import process_data
    >>> processed = process_data(raw_data, method='filter')
    """
    pass
```

#### Building Documentation
```bash
cd docs/
make html
# Open docs/_build/html/index.html in your browser
```

## Contribution Guidelines

### Code Requirements

1. **Type Hints**: All new code should include type hints
2. **Documentation**: All public functions/classes need docstrings
3. **Tests**: New features require corresponding tests
4. **Compatibility**: Code should work with Python 3.8+

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add ICA component rejection interface
fix: resolve memory leak in epoch browser
docs: update API documentation for preprocessing module
test: add unit tests for artifact detection
refactor: simplify data loading pipeline
```

Prefixes:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/modifications
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `perf:` - Performance improvements

### Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new functionality
3. **Ensure all tests pass**:
   ```bash
   pytest
   ```
4. **Run code quality checks**:
   ```bash
   pre-commit run --all-files
   ```
5. **Update CHANGELOG.md** if applicable
6. **Submit pull request** with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots for UI changes

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Issue Reporting

### Bug Reports
Include:
- Python version and OS
- QuickLab version
- MNE-Python version
- Minimal code example
- Full error traceback
- Expected vs. actual behavior

### Feature Requests
Include:
- Clear description of feature
- Use case and motivation
- Proposed implementation (if any)
- Willingness to implement

## Development Guidelines

### Architecture Principles

1. **Modularity**: Keep components loosely coupled
2. **MNE Integration**: Maintain compatibility with MNE workflows
3. **Performance**: Optimize for large datasets
4. **Usability**: Design for neuroscientists, not just programmers
5. **Extensibility**: Support plugins and custom analysis

### UI Development

1. **Use PyQt6** for all GUI components
2. **Follow Qt design patterns**
3. **Implement proper signal/slot connections**
4. **Support keyboard shortcuts**
5. **Provide tooltips and help text**
6. **Test on multiple platforms**

### Analysis Module Development

1. **Inherit from base classes** where appropriate
2. **Implement progress indicators** for long operations
3. **Support cancellation** of long-running tasks
4. **Cache results** when possible
5. **Provide parameter validation**
6. **Include visualization components**

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Development Chat**: [Link to be added]

### Code of Conduct

Please be:
- **Respectful** to all community members
- **Constructive** in feedback and criticism
- **Inclusive** and welcoming to newcomers
- **Patient** with questions and learning

## Recognition

Contributors will be acknowledged in:
- README.md
- Release notes
- Documentation
- About dialog in the application

## Getting Help

If you need help with development:

1. Check existing documentation
2. Search GitHub issues
3. Ask in GitHub Discussions
4. Contact maintainers directly

Thank you for contributing to QuickLab!