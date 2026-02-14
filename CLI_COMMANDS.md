# CLI Command Name Reference

## Important: Command Names Use Hyphens

The CLI uses the [Click framework](https://click.palletsprojects.com/), which automatically converts underscores in Python function names to hyphens in command-line commands.

### Function Name → Command Name Mapping

| Python Function | CLI Command | Usage |
|----------------|-------------|-------|
| `fetch_data()` | `fetch-data` | `python -m src.cli fetch-data` |
| `preprocess()` | `preprocess` | `python -m src.cli preprocess` |
| `compute_distance()` | `compute-distance` | `python -m src.cli compute-distance` |
| `find_unreachable()` | `find-unreachable` | `python -m src.cli find-unreachable` |
| `visualize()` | `visualize` | `python -m src.cli visualize` |
| `run_all()` | `run-all` | `python -m src.cli run-all` |
| `info()` | `info` | `python -m src.cli info` |

### Why Hyphens?

This is a Click convention that follows CLI best practices:
- **Hyphens** are standard in command-line tools (`git commit-tree`, `npm run-script`)
- **Underscores** are Pythonic for function names
- Click bridges the gap automatically

### Getting Help

To see all available commands with correct names:

```bash
python -m src.cli --help
```

To see help for a specific command:

```bash
python -m src.cli run-all --help
python -m src.cli fetch-data --help
```

### Quick Reference

**Complete pipeline:**
```bash
./venv/bin/python -m src.cli run-all
```

**Individual steps:**
```bash
./venv/bin/python -m src.cli fetch-data
./venv/bin/python -m src.cli preprocess
./venv/bin/python -m src.cli compute-distance
./venv/bin/python -m src.cli find-unreachable
./venv/bin/python -m src.cli visualize
```

**With options:**
```bash
./venv/bin/python -m src.cli run-all --skip-fetch
./venv/bin/python -m src.cli --config custom.yaml run-all
```

### VS Code Integration

All VS Code tasks and debug configurations now use the correct hyphenated command names. Simply:
- Press `Ctrl+Shift+B` to run the default task
- Or use Task menu to select any pipeline step

No need to remember the command names when using VS Code!
