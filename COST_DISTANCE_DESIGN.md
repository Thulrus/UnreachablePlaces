# Cost-Distance Analysis Design

## Overview
Transition from simple Euclidean distance to weighted cost-distance analysis that accounts for terrain difficulty and land cover.

## Current vs Enhanced Approach

### Current (Phase 1): Euclidean Distance
- **Method**: Simple straight-line distance from any pixel to nearest road
- **Calculation**: `scipy.ndimage.distance_transform_edt()`
- **Assumption**: All terrain is equally traversable
- **Output**: Distance in meters

### Enhanced (Phase 2): Cost-Distance Analysis
- **Method**: Accumulated cost of travel through different terrain types
- **Calculation**: Cost-weighted path using `skimage.graph.route_through_array()` or similar
- **Factors**: Slope, land cover type, elevation
- **Output**: Cost units (can be interpreted as "difficulty-adjusted distance")

## Data Sources

### 1. Digital Elevation Model (DEM) ✅ High Priority
**Source**: USGS 3DEP (3D Elevation Program)
- **Resolution**: 1 arc-second (~30m) or 1/3 arc-second (~10m)
- **Format**: GeoTIFF
- **Access**: Via `elevation` Python package or direct USGS download
- **Coverage**: Complete US coverage
- **URL**: https://apps.nationalmap.gov/downloader/

**Derived Products**:
- **Slope**: Rate of elevation change (degrees or percent)
- **Aspect**: Direction of slope (less critical for unreachability)

### 2. Land Cover ✅ High Priority
**Source**: NLCD (National Land Cover Database) 2021
- **Resolution**: 30m
- **Format**: GeoTIFF
- **Access**: Via MRLC API or direct download
- **Coverage**: Complete US coverage
- **URL**: https://www.mrlc.gov/data

**Land Cover Classes** (simplified):
- Open Water (11) - **Very High Cost** (impassable without boat)
- Developed (21-24) - **Low Cost** (roads already counted)
- Barren (31) - **Medium Cost** (rocky terrain)
- Forest (41-43) - **Medium-High Cost** (dense vegetation)
- Shrubland (51-52) - **Medium Cost**
- Grassland (71) - **Low-Medium Cost**
- Wetlands (90, 95) - **High Cost** (difficult terrain)
- Agriculture (81-82) - **Medium Cost**

### 3. Other Potential Data (Future)
- **Wilderness Areas**: USFS/BLM data (legal restrictions)
- **Private Land**: USGS Protected Areas Database
- **Snow Cover**: MODIS data (seasonal)
- **Population**: Census blocks (remoteness perception)

## Cost Function Design

### Formula
```
Total_Cost = Base_Distance × Slope_Factor × LandCover_Factor
```

### Slope Factor
```python
def slope_cost_factor(slope_degrees):
    """
    Convert slope to cost multiplier.
    
    Flat terrain: 1.0x
    10° slope: 1.2x
    20° slope: 1.5x
    30° slope: 2.0x
    40° slope: 3.0x
    >45° slope: 5.0x (extremely difficult)
    """
    if slope <= 5:
        return 1.0
    elif slope <= 10:
        return 1.0 + (slope - 5) * 0.04  # 1.0 to 1.2
    elif slope <= 20:
        return 1.2 + (slope - 10) * 0.03  # 1.2 to 1.5
    elif slope <= 30:
        return 1.5 + (slope - 20) * 0.05  # 1.5 to 2.0
    elif slope <= 40:
        return 2.0 + (slope - 30) * 0.1   # 2.0 to 3.0
    elif slope <= 45:
        return 3.0 + (slope - 40) * 0.4   # 3.0 to 5.0
    else:
        return 5.0 + (slope - 45) * 0.2   # 5.0+ (very steep)
```

### Land Cover Cost Table
```python
LANDCOVER_COSTS = {
    11: 10.0,   # Open Water - extremely high
    21: 1.0,    # Developed, Open Space
    22: 1.0,    # Developed, Low Intensity
    23: 1.0,    # Developed, Medium Intensity
    24: 1.0,    # Developed, High Intensity
    31: 1.5,    # Barren Land
    41: 2.0,    # Deciduous Forest
    42: 2.5,    # Evergreen Forest
    43: 2.2,    # Mixed Forest
    51: 1.4,    # Dwarf Scrub
    52: 1.4,    # Shrub/Scrub
    71: 1.2,    # Grassland/Herbaceous
    81: 1.3,    # Pasture/Hay
    82: 1.3,    # Cultivated Crops
    90: 3.0,    # Woody Wetlands
    95: 4.0,    # Emergent Herbaceous Wetlands
}
```

## Implementation Plan

### Phase 2A: Infrastructure (Week 1)
- [ ] Add DEM download capability to `fetch.py`
- [ ] Add NLCD download capability to `fetch.py`
- [ ] Create `src/cost_surface.py` module for cost calculations
- [ ] Add configuration options for cost factors

### Phase 2B: Cost Surface Generation (Week 1-2)
- [ ] Implement slope calculation from DEM
- [ ] Rasterize land cover to match analysis resolution
- [ ] Create composite cost surface raster
- [ ] Validate cost surface with test data

### Phase 2C: Cost-Distance Calculation (Week 2-3)
- [ ] Replace Euclidean distance with cost-distance algorithm
- [ ] Implement either:
  - Option A: `skimage.graph.route_through_array()` for exact paths
  - Option B: Modified distance transform with cost weighting
  - Option C: `scipy.ndimage` custom distance transform
- [ ] Benchmark performance (cost-distance is slower than Euclidean)
- [ ] Add progress indicators for long calculations

### Phase 2D: Visualization Updates (Week 3)
- [ ] Update maps to show "cost-weighted distance" vs "Euclidean distance"
- [ ] Add cost surface visualization layer
- [ ] Create comparison maps (before/after)
- [ ] Update documentation and examples

## Technical Challenges

### 1. Performance
**Problem**: Cost-distance calculations are computationally expensive
**Solutions**:
- Use coarser resolution (500m instead of 250m)
- Implement parallel processing
- Cache intermediate results
- Use GPU acceleration (optional)

### 2. Data Size
**Problem**: DEM and land cover files are large
**Solutions**:
- Stream data instead of loading entirely into memory
- Use cloud-optimized GeoTIFFs (COGs)
- Implement lazy loading with dask/rasterio windows

### 3. Resolution Mismatch
**Problem**: DEM (30m), NLCD (30m), roads (vector), analysis (250m)
**Solutions**:
- Resample all to common resolution
- Use bilinear interpolation for DEM
- Use mode/majority for land cover
- Aggregate appropriately

### 4. Cost Calibration
**Problem**: How to weight slope vs land cover vs distance?
**Solutions**:
- Use empirical hiking speed data (Tobler's hiking function)
- Make costs configurable via config.yaml
- Provide sensitivity analysis tools
- Compare with real-world accessibility data

## Validation

### Comparison Points
1. **Known Remote Locations**: Compare results with documented remote areas
2. **Hiking Trail Data**: Compare cost-distance with actual trail distances
3. **Expert Knowledge**: Validate with local geography experts
4. **Field Validation**: Ground-truth selected locations (long-term)

### Expected Outcomes
- Open water areas should have extremely high costs
- Mountainous regions should show increased difficulty
- Flat desert should show moderate costs
- Results should account for terrain barriers (canyons, rivers)

## Configuration Schema

```yaml
# Cost-distance calculation settings
cost_distance:
  enabled: true                    # Use cost-distance instead of Euclidean
  resolution_m: 250                # Analysis resolution
  
  # Data sources
  dem:
    source: "USGS_3DEP"           # DEM source
    resolution: 30                 # Native DEM resolution (m)
  
  landcover:
    source: "NLCD_2021"           # Land cover source
    resolution: 30                 # Native NLCD resolution (m)
  
  # Cost factors
  factors:
    slope_weight: 1.0              # Multiplier for slope costs
    landcover_weight: 1.0          # Multiplier for land cover costs
    base_distance_weight: 1.0      # Multiplier for base distance
    
  # Advanced options
  max_slope_cost: 10.0             # Cap on slope cost factor
  water_passable: false            # Can cross water bodies
  
  # Performance
  chunk_size: 1000                 # Process in chunks for memory efficiency
  use_parallel: true               # Use multiprocessing
  num_workers: 4                   # Number of parallel workers
```

## Migration Path

### For Users
1. **Backward Compatible**: Keep Euclidean distance as default option
2. **Enable Cost-Distance**: Add `cost_distance.enabled: true` to config
3. **Download Data**: First run will download DEM and NLCD (~500MB-2GB)
4. **Compare Results**: Both methods available for comparison

### For Developers
1. **New Module**: `src/cost_surface.py` handles all cost calculations
2. **Modified Distance Calculation**: `src/distance.py` gains cost-distance mode
3. **Enhanced Fetch**: `src/fetch.py` adds DEM and NLCD downloaders
4. **Extended Preprocessing**: `src/preprocess.py` handles cost surface creation

## Deliverables

### Code
- [ ] `src/cost_surface.py` - Cost surface generation
- [ ] Updated `src/fetch.py` - DEM and NLCD download
- [ ] Updated `src/distance.py` - Cost-distance calculation
- [ ] Updated `src/preprocess.py` - Cost surface preprocessing
- [ ] Updated `config.yaml` - Cost-distance settings

### Documentation
- [ ] COST_DISTANCE_GUIDE.md - User guide for cost-distance analysis
- [ ] Updated README.md - Mention cost-distance capabilities
- [ ] Updated CLI_COMMANDS.md - Document new options
- [ ] Example notebooks - Before/after comparisons

### Testing
- [ ] Unit tests for cost functions
- [ ] Integration tests for full pipeline
- [ ] Performance benchmarks
- [ ] Validation against known locations

## Timeline
- **Week 1**: Data fetching and cost surface infrastructure
- **Week 2**: Cost-distance algorithm implementation
- **Week 3**: Visualization and documentation
- **Week 4**: Testing, validation, and optimization

## Next Steps
1. Implement DEM download in `fetch.py`
2. Implement NLCD download in `fetch.py`
3. Create `cost_surface.py` module
4. Add slope calculation
5. Add composite cost surface generation
