# Virtual Environment Usage Notes

## Important: Python Command Usage

This project uses a Python virtual environment (`venv/`) with all dependencies installed. 

### When Using VS Code Tasks

✅ **No need to activate manually** - The tasks are configured to use `./venv/bin/python` directly.

Just press `Ctrl+Shift+B` or use the Task menu to run any task.

### When Using the Command Line

You have **two options**:

#### Option 1: Activate venv first (Recommended for interactive work)

```bash
# Activate (bash/zsh)
source venv/bin/activate

# Activate (fish)
source venv/bin/activate.fish

# Then use 'python' command
python -m src.cli info
python -m src.cli run-all
```

Benefits:
- Shorter commands (`python` instead of `./venv/bin/python`)
- Works for multiple commands
- Clear indication in prompt that venv is active

#### Option 2: Use venv python directly

```bash
# Use full path to venv python
./venv/bin/python -m src.cli info
./venv/bin/python -m src.cli run-all
```

Benefits:
- No activation needed
- Works without modifying shell
- Good for scripts and automation

### Why Not `python3`?

❌ **Don't use `python3`** - This runs the system Python, which doesn't have the project dependencies.

```bash
# This will fail with ModuleNotFoundError
python3 -m src.cli run-all  # ❌ Wrong

# Use one of these instead
python -m src.cli run-all           # ✅ (after activating venv)
./venv/bin/python -m src.cli run-all  # ✅ (always works)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'geopandas'"

This means you're using the system Python instead of the venv Python.

**Solution:**
1. Make sure venv is created: `ls venv/bin/python` should exist
2. If not, run `./setup.sh` to create it
3. Use `./venv/bin/python` or activate venv first

### "No such file or directory: ./venv/bin/python"

The virtual environment doesn't exist.

**Solution:**
Run the setup script: `./setup.sh`

### VS Code tasks still failing

1. Check that `venv/` directory exists in workspace root
2. Restart VS Code
3. Check the task output - it should show `./venv/bin/python` being used

## Summary

| Context | Command to Use |
|---------|---------------|
| VS Code Tasks | Just run the task (auto uses venv) |
| Terminal (activated venv) | `python -m src.cli ...` |
| Terminal (no activation) | `./venv/bin/python -m src.cli ...` |
| Scripts/Automation | `./venv/bin/python -m src.cli ...` |

**Never use** `python3` when running this project's code!
