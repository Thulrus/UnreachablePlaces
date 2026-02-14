# Cost-Distance Analysis Results

## Comparison: Euclidean vs Cost-Distance

### Summary Statistics

| Metric | Euclidean | Cost-Distance | Ratio |
|--------|-----------|---------------|-------|
| **Max Distance** | 32.70 km | 429.94 km | **13.1×** |
| **Mean Distance** | 2.98 km | 39.53 km | **13.3×** |
| **Median Distance** | 1.68 km | 26.04 km | **15.5×** |

### Top 5 Most Unreachable Locations

#### Cost-Distance (Terrain-Aware)
1. **429.94 km** - (37.004°N, 110.870°W) - **SE Utah** (Canyonlands region)
2. **337.07 km** - (40.395°N, 113.491°W) - Great Salt Lake Desert
3. **299.22 km** - (37.091°N, 111.132°W) - SE Utah (Canyon country)
4. **280.12 km** - (39.567°N, 110.060°W) - Central-East Utah
5. **276.07 km** - (38.089°N, 110.180°W) - Central-East Utah

#### Euclidean (Straight-Line)
1. **32.70 km** - (40.430°N, 113.500°W) - Great Salt Lake Desert
2. **30.87 km** - (37.005°N, 110.756°W) - SE Utah
3. **28.32 km** - (37.004°N, 111.039°W) - SE Utah
4. **24.91 km** - (40.961°N, 113.681°W) - NW Utah
5. **23.40 km** - (40.523°N, 113.774°W) - West Utah

## Key Findings

### Why Cost-Distance is 13× Higher

Cost-distance represents **"effective travel difficulty"** not straight-line distance:

1. **Slope costs** (1× flat → 10× at 45°+)
   - Steep terrain in canyon country adds 2-10× difficulty
   - Mountain ranges create major barriers

2. **Land cover costs** (1× open → 10× water)
   - Water bodies: 10× penalty (Great Salt Lake)
   - Dense forest: 2-2.5× penalty
   - Grassland/desert: 1.2-1.5× penalty

3. **Cumulative effect**: A 50 km straight-line distance through:
   - Flat desert: ~60 km cost-distance (1.2× multiplier)
   - Steep canyons: ~300-500 km cost-distance (6-10× multiplier)

### Geographic Interpretation

**SE Utah dominates** in cost-distance because:
- **Canyonlands/Moab area**: Extreme terrain with deep canyons, mesas, vertical cliffs
- **Sparse road network**: Very few roads through rugged terrain
- **Compounding difficulties**: Must traverse multiple barriers to reach these areas

**Great Salt Lake Desert** (Euclidean #1) drops to **#2** in cost-distance:
- Flat terrain (low slope cost)
- But water bodies still create major barriers
- Easier to traverse once you reach it

## Data Sources

- **DEM**: SRTM 30m elevation (332 MB)
- **Land Cover**: NLCD 2021 (25 MB)
- **Resolution**: 250m analysis grid (2485×1986 pixels)
- **Computation**: scikit-image MCP (Marching Cubes Priority) algorithm
- **Processing Time**: ~2-5 minutes (vs <5 seconds for Euclidean)

## Generated Files

```
data/processed/
  utah_distance.tif          # Euclidean (7.6 MB)
  utah_distance_cost.tif     # Cost-distance (16 MB)
  utah_slope.tif            # Slope from DEM (893 MB)
  utah_cost_surface.tif     # Combined costs (12 MB)

outputs/
  results.json                      # Analysis results (cost-distance)
  maps/utah_unreachability_map.png           # Heatmap
  maps/utah_top5_labeled_map.png            # Top 5 with labels
  maps/utah_unreachability_interactive.html  # Interactive map
```

## Usage

```bash
# Run full cost-distance analysis
./venv/bin/python -m src.cli run-all --skip-fetch

# Or step-by-step:
cost-surface           # Generate terrain costs
compute-distance       # Calculate cost-distance field
find-unreachable       # Find top 5 locations
visualize              # Create maps
```

## Configuration

Set `cost_distance.enabled: true` in `config.yaml`:

```yaml
cost_distance:
  enabled: true           # false = Euclidean mode
  resolution_m: 250       # Must match raster.resolution
  
  slope:
    flat_cost: 1.0       # 0° slope
    steep_cost: 10.0     # ≥45° slope
    steep_threshold: 45  # degrees
    
  landcover:
    water: 10.0
    developed: 1.1
    barren: 1.2
    forest: 2.0-2.5
    shrubland: 1.3
    grassland: 1.2
    crops: 1.1
    wetlands: 3.0
```

---

**Analysis Date**: February 14, 2026  
**System**: Utah Unreachability Mapping Tool v2.0
