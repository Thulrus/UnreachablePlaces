# Contributing to Unreachable Mapper

Thank you for your interest in contributing to the Unreachable Mapper project!

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest black flake8  # Dev dependencies
   ```

## Code Style

- Follow PEP 8 guidelines
- Use `black` for code formatting:
  ```bash
  black src/
  ```
- Run `flake8` for linting:
  ```bash
  flake8 src/ --max-line-length=100
  ```

## Project Structure

- `src/fetch.py` - Data acquisition
- `src/preprocess.py` - Data preprocessing and rasterization
- `src/distance.py` - Distance field computation
- `src/analyze.py` - Finding unreachable points
- `src/visualize.py` - Creating visualizations
- `src/cli.py` - Command-line interface
- `src/config.py` - Configuration management

## Adding New Features

### Adding a New State

1. Edit `config.yaml` or create a new config file
2. Update state name and FIPS code
3. Run the pipeline with the new config

### Adding New Distance Metrics

1. Extend `src/distance.py`
2. Add new computation methods to `DistanceCalculator` class
3. Update configuration to support new metric selection

### Adding New Visualizations

1. Extend `src/visualize.py`
2. Add new methods to `Visualizer` class
3. Update CLI to expose new visualization options

## Testing

Create tests in a `tests/` directory:

```bash
mkdir tests
# Add test_*.py files
pytest tests/
```

## Submitting Changes

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request with:
   - Clear description of changes
   - Any configuration updates needed
   - Example usage

## Future Enhancements

See README.md for planned Phase 2 features:
- Cost-distance metrics
- DEM integration
- Land cover analysis
- Multi-state batch processing

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Usage questions
- Technical discussions

---

Happy contributing! 🚀
