# Quick Start Guide

## Installation (5 minutes)

```bash
# 1. Navigate to project
cd /home/keyser/Documents/Projects/UnreachablePlaces

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Run the Pipeline (15-25 minutes)

```bash
# Option 1: Run everything at once
./venv/bin/python -m src.cli run_all

# Option 2: Run step by step
./venv/bin/python -m src.cli fetch_data          # Downloads data (10-20 min first time)
./venv/bin/python -m src.cli preprocess          # Processes data (2-3 min)
./venv/bin/python -m src.cli compute_distance    # Computes distances (30 sec)
./venv/bin/python -m src.cli find_unreachable    # Finds most remote point (5 sec)
./venv/bin/python -m src.cli visualize           # Creates maps (1 min)
```

## View Results

```bash
# View results JSON
cat outputs/results.json

# Open static map
xdg-open outputs/maps/utah_unreachability_map.png

# Open interactive map in browser
xdg-open outputs/maps/utah_unreachability_interactive.html
```

## Common Commands

```bash
# Show project info
./venv/bin/python -m src.cli info

# Run with custom config
./venv/bin/python -m src.cli --config my_config.yaml run_all

# Skip data download if already fetched
./venv/bin/python -m src.cli run_all --skip-fetch

# Get help
./venv/bin/python -m src.cli --help
./venv/bin/python -m src.cli run_all --help
```

## Analyze Another State

```bash
# 1. Edit config.yaml
# Change:
#   state:
#     name: "Colorado"
#     fips_code: "08"

# 2. Run pipeline
./venv/bin/python -m src.cli run_all
```

## Project Structure

```
src/
├── fetch.py       - Downloads boundary and roads
├── preprocess.py  - Clips and rasterizes data
├── distance.py    - Computes distance fields
├── analyze.py     - Finds unreachable points
├── visualize.py   - Creates maps
└── cli.py         - Command-line interface

data/
├── raw/           - Downloaded data
└── processed/     - Processed rasters

outputs/
├── maps/          - Generated visualizations
└── results.json   - Analysis results
```

## Troubleshooting

**OSMnx takes too long:**
- Roads download is one-time operation
- Use `--skip-fetch` flag on subsequent runs

**Out of memory:**
- Increase resolution in config.yaml (e.g., 500m instead of 250m)

**Import errors:**
- Make sure virtual environment is activated
- Reinstall: `pip install -r requirements.txt`

---

For full documentation, see [README.md](README.md)
