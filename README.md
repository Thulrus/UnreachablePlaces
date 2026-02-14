# Unreachable Mapper

A Python-based geospatial analysis tool that computes and visualizes the most unreachable locations based on Euclidean distance from roads and settlements.

**Current Phase:** Utah implementation (Phase 1)  
**Metric:** Euclidean distance to nearest road

## 🎯 Project Goal

Find and visualize the most remote, hard-to-reach locations by computing distance fields from roads and infrastructure. The tool produces both static and interactive maps showing:

1. Input data layers (roads, state boundary)
2. Distance field visualization (heatmap)
3. Most unreachable point(s) marked on maps

## 📋 Features

- **Automated data fetching** from OpenStreetMap and US Census
- **Distance field computation** using Euclidean distance transforms
- **Modular pipeline** with individual CLI commands
- **Static and interactive visualizations**
- **Extensible architecture** for additional states and metrics
- **Configurable resolution** and parameters

## 🚀 Quick Start

### Installation

```bash
# Clone the repository (or navigate to project directory)
cd UnreachablePlaces

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or use Poetry
poetry install
```

### Run Complete Pipeline

```bash
# Run everything at once
python -m src.cli run-all

# Or run individual steps
python -m src.cli fetch-data
python -m src.cli preprocess
python -m src.cli compute-distance
python -m src.cli find-unreachable
python -m src.cli visualize
```

### View Results

After running the pipeline:

- **Results JSON:** `outputs/results.json`
- **Static map:** `outputs/maps/utah_unreachability_map.png`
- **Interactive map:** `outputs/maps/utah_unreachability_interactive.html`

## 📂 Project Structure

```
unreachable_mapper/
├── data/
│   ├── raw/              # Downloaded raw data
│   └── processed/        # Processed/rasterized data
├── src/
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration management
│   ├── fetch.py          # Data acquisition module
│   ├── preprocess.py     # Data preprocessing
│   ├── distance.py       # Distance field computation
│   ├── analyze.py        # Unreachability analysis
│   ├── visualize.py      # Map visualization
│   └── cli.py            # Command-line interface
├── notebooks/            # Jupyter notebooks (optional)
├── outputs/
│   └── maps/             # Generated visualizations
├── config.yaml           # Configuration file
├── pyproject.toml        # Poetry configuration
├── requirements.txt      # Pip dependencies
└── README.md             # This file
```

## 🛠️ Technical Stack

**Language:** Python 3.11+

**Core Libraries:**
- **Geospatial:** geopandas, rasterio, shapely, pyproj, osmnx
- **Numerical:** numpy, scipy
- **Visualization:** matplotlib, folium, contextily
- **CLI:** click
- **Config:** pyyaml

## 📊 How It Works

### 1. Data Acquisition
- Fetches Utah state boundary from US Census TIGER shapefiles
- Downloads road network from OpenStreetMap via OSMnx
- Optional: Fetches settlement data

### 2. Preprocessing
- Reprojects all data to EPSG:5070 (NAD83 Conus Albers - distance-preserving)
- Clips roads to state boundary
- Rasterizes roads to 250m resolution grid (configurable)

### 3. Distance Field Computation
- Applies Euclidean distance transform using `scipy.ndimage.distance_transform_edt`
- Converts pixel distances to meters
- Masks to state boundary

### 4. Analysis
- Finds pixel with maximum distance from roads
- Converts to geographic coordinates (lat/lon)
- Identifies top 10 most unreachable locations
- Computes statistics (mean, median distance)

### 5. Visualization
- **Static:** Matplotlib map with distance heatmap and marked points
- **Interactive:** Folium map with toggleable layers and popups

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
state:
  name: "Utah"
  fips_code: "49"

projection:
  crs: "EPSG:5070"  # Distance-preserving projection

raster:
  resolution: 250  # Meters per pixel

visualization:
  colormap: "YlOrRd"
  dpi: 300
```

### Key Parameters

- **Resolution:** Trade-off between accuracy and computation time
  - 250m: Good balance (default)
  - 100m: High detail, slower
  - 500m: Fast, lower resolution

- **CRS:** Must be distance-preserving for accurate Euclidean distances
  - EPSG:5070 recommended for CONUS states

## 📝 CLI Commands

> **Note:** Command names use hyphens (e.g., `run-all`, `fetch-data`) due to Click framework conventions. See [CLI_COMMANDS.md](CLI_COMMANDS.md) for details.

```bash
# Show project info
python -m src.cli info

# Run complete pipeline
python -m src.cli run-all

# Individual steps
python -m src.cli fetch-data          # Download data
python -m src.cli preprocess          # Process and rasterize
python -m src.cli compute-distance    # Calculate distance field
python -m src.cli find-unreachable    # Find most remote point
python -m src.cli visualize           # Create maps

# Use custom config
python -m src.cli --config custom_config.yaml run-all

# Skip data fetch if already downloaded
python -m src.cli run-all --skip-fetch
```

## 🔧 Adding Another State

To analyze a different state:

1. **Create new config file** (e.g., `config_california.yaml`):
   ```yaml
   state:
     name: "California"
     fips_code: "06"
   
   # ... rest of config ...
   ```

2. **Run with custom config:**
   ```bash
   python -m src.cli --config config_california.yaml run-all
   ```

3. **Or edit** `config.yaml` directly to change the default state.

## 📈 Results Interpretation

### Distance Metric (Phase 1)

**Current metric:** Straight-line (Euclidean) distance to nearest road

**What it measures:**
- Physical remoteness from road infrastructure
- "As the crow flies" distance
- Does NOT account for:
  - Terrain difficulty (mountains, canyons)
  - Legal access restrictions
  - Actual travel time or path

**Typical Utah results:**
- Most unreachable point: ~20-40 km from nearest road
- Located in remote desert or mountain regions
- Mean distance: ~2-5 km statewide

## 🔮 Future Enhancements

### Cost-Distance Analysis (Implemented - Manual Data Required)

The project now includes **optional cost-distance analysis** that accounts for terrain difficulty:
- **Slope-based costs** - Steeper terrain = harder to traverse
- **Land cover costs** - Water, forests, developed areas have different traversal difficulty
- **Realistic accessibility** - More accurate than straight-line distance

**Status:** Infrastructure complete, but automatic terrain data download is currently unreliable.

**To enable:**
1. Download terrain data manually (see `TERRAIN_DATA.md`)
2. Or run helper script: `./download_terrain_data.py`
3. Set `cost_distance.enabled: true` in `config.yaml`
4. Run: `python -m src.cli cost-surface` then `python -m src.cli run-all`

**Note:** Euclidean distance (default) works fine without terrain data.

### Phase 2 Features (Planned)
- **Travel-time modeling** based on terrain
- **Settlement integration** in distance calculations
- **Batch processing** for all US states
- **GPU acceleration** for large rasters
- **Route finding** to unreachable points

### Architecture Design Choices

The codebase is designed for extensibility:
- **Modular pipeline** - Each step is independent
- **Configuration-driven** - Easy to swap states or parameters
- **CRS-aware** - Handles projections explicitly
- **Scalable** - Vectorized operations, ready for parallelization

## 🐛 Troubleshooting

### Common Issues

**1. OSMnx timeout downloading roads:**
```bash
# Roads download can take 10-30 minutes for large states
# Be patient or use --skip-fetch on subsequent runs
```

**2. Memory errors on large states:**
```yaml
# In config.yaml, increase resolution to reduce raster size
raster:
  resolution: 500  # Use 500m instead of 250m
```

**3. Projection warnings:**
```
# Ignore CRS warnings - the tool handles reprojection automatically
```

## 📚 Data Sources

- **State Boundaries:** US Census Bureau TIGER/Line Shapefiles (2022)
- **Roads:** OpenStreetMap via OSMnx
- **Optional Settlements:** OpenStreetMap place nodes

## 📄 License

This project is provided as-is for educational and research purposes.

## 🤝 Contributing

To extend this project:

1. **Add new distance metrics:** Modify `src/distance.py`
2. **Add new data sources:** Extend `src/fetch.py`
3. **Improve visualizations:** Enhance `src/visualize.py`
4. **Add tests:** Create `tests/` directory

## 📧 Contact

For questions or issues, please open an issue on the project repository.

---

## 🎓 Technical Details

### Distance Transform Algorithm

Uses `scipy.ndimage.distance_transform_edt`:
- **EDT:** Euclidean Distance Transform
- **Algorithm:** Efficient scan-based method
- **Complexity:** O(n) for n pixels
- **Accuracy:** Sub-pixel precision

### Coordinate Systems

1. **Input (WGS84):** EPSG:4326 (lat/lon)
2. **Analysis (Albers):** EPSG:5070 (equal-area, distance-preserving)
3. **Output:** Both projections for usability

### Performance Notes

**Typical runtime for Utah (250m resolution):**
- Data fetch: 10-20 minutes (one-time)
- Preprocessing: 2-3 minutes
- Distance computation: 30 seconds
- Analysis: 5 seconds
- Visualization: 1 minute

**Total:** ~15-25 minutes first run, ~5 minutes subsequent runs

### Memory Usage

- **250m resolution:** ~2-4 GB RAM
- **100m resolution:** ~10-20 GB RAM
- Scales quadratically with resolution

---

**Version:** 0.1.0  
**Last Updated:** February 2026  
**Status:** Phase 1 Complete (Utah implementation)
