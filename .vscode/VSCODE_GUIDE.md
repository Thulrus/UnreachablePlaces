# VS Code Tasks and Configuration

This document explains the VS Code tasks and debug configurations available for the Unreachable Mapper project.

## Quick Access

- **Run a task:** Press `Ctrl+Shift+B` (or `Cmd+Shift+B` on Mac) for the default build task, or `Ctrl+Shift+P` → "Tasks: Run Task"
- **Debug:** Press `F5` or go to Run and Debug panel (Ctrl+Shift+D)

## Available Tasks

### Setup & Info

**Setup: Install Dependencies**
- Runs the `setup.sh` script to create virtual environment and install all dependencies
- **When to use:** First time setup or when dependencies change

**Project: Show Info**
- Displays project configuration, paths, and available commands
- **When to use:** Check current configuration or get a quick overview

**Help: Show CLI Help**
- Shows all available CLI commands with descriptions
- **When to use:** Need to see what CLI options are available

---

### Pipeline Execution

**Pipeline: Run All (Complete)** ⭐ *Default Build Task*
- Executes the complete pipeline from data fetch to visualization
- **Duration:** 15-25 minutes (first run)
- **When to use:** Fresh start or first time running the project
- **Keyboard shortcut:** `Ctrl+Shift+B` (or `Cmd+Shift+B`)

**Pipeline: Run All (Skip Fetch)**
- Runs the complete pipeline but skips data downloading
- **Duration:** ~5 minutes
- **When to use:** Data already downloaded, want to re-run analysis

---

### Individual Pipeline Steps

**Step 1: Fetch Data**
- Downloads state boundary and road network from OpenStreetMap/Census
- **Duration:** 10-20 minutes (one-time operation)
- **Output:** `data/raw/utah_boundary.geojson`, `data/raw/utah_roads.geojson`

**Step 2: Preprocess Data**
- Reprojects, clips, and rasterizes vector data
- **Duration:** 2-3 minutes
- **Output:** Processed GeoJSON files and raster masks in `data/processed/`

**Step 3: Compute Distance Field**
- Calculates Euclidean distance transform from roads
- **Duration:** ~30 seconds
- **Output:** `data/processed/utah_distance.tif`

**Step 4: Find Unreachable Point**
- Analyzes distance field to find most remote location(s)
- **Duration:** ~5 seconds
- **Output:** `outputs/results.json`

**Step 5: Create Visualizations**
- Generates static (PNG) and interactive (HTML) maps
- **Duration:** ~1 minute
- **Output:** Maps in `outputs/maps/` directory

---

### Viewing Results

**View: Open Results JSON**
- Displays `outputs/results.json` in terminal
- **When to use:** Quick check of analysis results (coordinates, distances)

**View: Open Static Map**
- Opens the PNG map in your default image viewer
- **When to use:** View high-resolution static visualization

**View: Open Interactive Map**
- Opens the HTML map in your default web browser
- **When to use:** Explore results interactively with zoom/pan

---

### Cleanup Tasks

**Clean: Remove Cached Data**
- Deletes all downloaded and processed data
- **Warning:** You'll need to re-download data (10-20 minutes)
- **When to use:** Free up disk space or start completely fresh

**Clean: Remove Output Maps**
- Deletes only the generated visualizations and results
- **When to use:** Re-generate visualizations without re-processing data

---

### Development Tasks

**Dev: Run Module Tests**
- Executes pytest test suite
- **When to use:** After making code changes (when tests are created)

**Dev: Format Code (Black)**
- Formats all Python code according to Black style guide
- **When to use:** Before committing code changes

**Dev: Lint Code (Flake8)**
- Checks code style and potential issues
- **When to use:** Before committing or to check code quality

---

## Debug Configurations

Access via Run and Debug panel (`Ctrl+Shift+D`) or press `F5`.

### Available Configurations

1. **Python: Show Info** - Debug the info command
2. **Python: Run Pipeline (Complete)** - Debug full pipeline with breakpoints
3. **Python: Run Pipeline (Skip Fetch)** - Debug pipeline skipping data fetch
4. **Python: Fetch Data** - Debug data fetching module
5. **Python: Preprocess** - Debug preprocessing module
6. **Python: Compute Distance** - Debug distance computation
7. **Python: Find Unreachable** - Debug analysis module
8. **Python: Visualize** - Debug visualization module
9. **Python: Debug Current File** - Debug the currently open Python file
10. **Python: Custom Config** - Run pipeline with custom config file (prompts for path)

### Using Debugger

1. Set breakpoints in code by clicking left of line numbers
2. Select a debug configuration from dropdown
3. Press `F5` to start debugging
4. Use debug controls:
   - `F5`: Continue
   - `F10`: Step Over
   - `F11`: Step Into
   - `Shift+F11`: Step Out
   - `Ctrl+Shift+F5`: Restart
   - `Shift+F5`: Stop

---

## VS Code Settings

The project includes optimized settings for Python development:

### Python Environment
- Auto-activates virtual environment in terminal
- Uses `venv/bin/python` as interpreter

### Code Formatting
- **Black** formatter enabled
- Auto-format on save
- 100 character line length
- Auto-organize imports

### Linting
- **Flake8** enabled for style checking
- Configured to match Black's line length

### File Exclusions
- Hides `__pycache__`, `*.pyc`, `venv` from explorer
- Excludes data/outputs from file watcher (performance)

---

## Tips & Workflows

### First Time Setup
1. Run: **Setup: Install Dependencies**
2. Run: **Project: Show Info** (verify configuration)
3. Run: **Pipeline: Run All (Complete)**
4. Run: **View: Open Interactive Map**

### Iterative Development
1. Run: **Pipeline: Run All (Skip Fetch)** (use cached data)
2. Make code changes
3. Run specific step tasks to test changes
4. Use debug configurations to troubleshoot

### Analyzing Different States
1. Edit `config.yaml` - change state name and FIPS code
2. Run: **Clean: Remove Cached Data**
3. Run: **Pipeline: Run All (Complete)**

### Quick Results Check
1. Run: **View: Open Results JSON** (see coordinates/distances)
2. Run: **View: Open Interactive Map** (visual exploration)

### Before Committing Code
1. Run: **Dev: Format Code (Black)**
2. Run: **Dev: Lint Code (Flake8)**
3. Run: **Dev: Run Module Tests** (when tests exist)

---

## Keyboard Shortcuts Summary

| Action | Shortcut | Description |
|--------|----------|-------------|
| Run Build Task | `Ctrl+Shift+B` | Run complete pipeline |
| Run Any Task | `Ctrl+Shift+P` → "Tasks: Run Task" | Choose from all tasks |
| Start Debugging | `F5` | Run with debugger |
| Debug Panel | `Ctrl+Shift+D` | Open Run and Debug view |
| Toggle Terminal | `Ctrl+\`` | Show/hide integrated terminal |

---

## Customization

### Adding a New Task

Edit `.vscode/tasks.json`:

```json
{
  "label": "My Custom Task",
  "type": "shell",
  "command": "python3 -m src.cli my_command",
  "group": "none",
  "detail": "Description of what this task does"
}
```

### Adding a Debug Configuration

Edit `.vscode/launch.json`:

```json
{
  "name": "My Debug Config",
  "type": "python",
  "request": "launch",
  "module": "src.cli",
  "args": ["my_command"],
  "console": "integratedTerminal"
}
```

---

## Troubleshooting

**Tasks fail with "command not found"**
- Make sure virtual environment is activated
- Run **Setup: Install Dependencies** first

**Python interpreter not found**
- Check `.vscode/settings.json` python.defaultInterpreterPath
- Verify `venv/` directory exists

**Tasks panel not showing**
- Press `Ctrl+Shift+P` and type "Tasks: Run Task"
- Check that `.vscode/tasks.json` exists

**Debug breakpoints not working**
- Ensure file is saved
- Try restarting debug session (`Ctrl+Shift+F5`)
- Check "justMyCode" setting in launch.json

---

For more information about the project itself, see:
- [README.md](../README.md) - Full project documentation
- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [PROJECT_STATUS.md](../PROJECT_STATUS.md) - Current status
