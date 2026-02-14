# How to Switch to a New State

## Quick Start (3 Steps)

**1. Edit `config.yaml`** - Change 2 lines:

```yaml
state:
  name: "YourState"     # e.g., "Arizona", "Nevada", "Montana"
  fips_code: "XX"       # 2-digit FIPS code (see table below)
```

**2. Make sure Euclidean mode is enabled** (for fast testing):

```yaml
cost_distance:
  enabled: false     # false = Euclidean (fast), true = cost-distance (slow, requires terrain data)
```

**3. Run the pipeline:**

```bash
./venv/bin/python -m src.cli run-all
```

That's it! The tool will automatically:
- Download the new state boundary
- Fetch roads from OpenStreetMap
- Process and analyze
- Generate maps

## State FIPS Codes Reference

### Western States
| State | FIPS | Notes |
|-------|------|-------|
| **Alaska** | 02 | Very large, may be slow |
| **Arizona** | 04 | Tested ✓ |
| **California** | 06 | Very large, expect 10-20 min |
| **Colorado** | 08 | Mountain states work well |
| **Hawaii** | 15 | Islands - interesting results! |
| **Idaho** | 16 | Good test state |
| **Montana** | 30 | Large but sparse roads |
| **Nevada** | 32 | Huge desert areas |
| **New Mexico** | 35 | Similar to Arizona |
| **Oregon** | 41 | Moderate size |
| **Utah** | 49 | Default, fully tested ✓ |
| **Washington** | 53 | Moderate size |
| **Wyoming** | 56 | Very low road density |

### Midwest States
| State | FIPS | Notes |
|-------|------|-------|
| **Illinois** | 17 | Dense roads, less interesting |
| **Indiana** | 18 | Dense roads |
| **Iowa** | 19 | Dense roads, flat |
| **Kansas** | 20 | Flat, sparse in west |
| **Michigan** | 26 | Water boundaries affect results |
| **Minnesota** | 27 | Lots of lakes |
| **Missouri** | 29 | Moderately dense |
| **Nebraska** | 31 | Sparse in sandhills |
| **North Dakota** | 38 | Very sparse |
| **Ohio** | 39 | Dense roads |
| **South Dakota** | 46 | Badlands area interesting |
| **Wisconsin** | 55 | Lakes affect results |

### Southern States
| State | FIPS | Notes |
|-------|------|-------|
| **Alabama** | 01 | Moderate density |
| **Arkansas** | 05 | Ozarks region interesting |
| **Florida** | 12 | Everglades! |
| **Georgia** | 13 | Okefenokee swamp |
| **Kentucky** | 21 | Daniel Boone Forest |
| **Louisiana** | 22 | Bayou regions |
| **Mississippi** | 28 | Delta region |
| **North Carolina** | 37 | Mountains to coast |
| **Oklahoma** | 40 | Panhandle sparse |
| **South Carolina** | 45 | Coastal areas |
| **Tennessee** | 47 | Smoky Mountains |
| **Texas** | 48 | Huge - Big Bend area amazing |
| **Virginia** | 51 | Appalachian regions |
| **West Virginia** | 54 | Very mountainous |

### Northeastern States
| State | FIPS | Notes |
|-------|------|-------|
| **Connecticut** | 09 | Small, dense roads |
| **Delaware** | 10 | Very small state |
| **Maine** | 23 | Northern forests interesting |
| **Maryland** | 24 | Small, dense |
| **Massachusetts** | 25 | Dense roads |
| **New Hampshire** | 33 | White Mountains |
| **New Jersey** | 34 | Very dense roads |
| **New York** | 36 | Adirondacks interesting |
| **Pennsylvania** | 42 | State forests |
| **Rhode Island** | 44 | Smallest state |
| **Vermont** | 50 | Rural, forest |

## Expected Runtime (Euclidean Mode)

| Phase | Small State | Medium State | Large State |
|-------|-------------|--------------|-------------|
| **fetch-data** | 1-2 min | 3-5 min | 10-20 min |
| **preprocess** | 30 sec | 1-2 min | 3-5 min |
| **compute-distance** | 2-5 sec | 5-10 sec | 10-30 sec |
| **find-unreachable** | 1-2 sec | 2-5 sec | 5-10 sec |
| **visualize** | 10-15 sec | 15-30 sec | 30-60 sec |
| **Total** | ~2-3 min | ~5-8 min | ~15-30 min |

*Note: First run is slower due to OSM downloads. Subsequent runs use cached data.*

## Interesting States to Try

### For Extreme Remoteness
1. **Alaska** - Vast wilderness, very few roads
2. **Nevada** - Huge uninhabited desert areas
3. **Wyoming** - Very low population density
4. **Montana** - Large wilderness areas
5. **New Mexico** - Desert and mountains

### For Interesting Geography
1. **Florida** - Everglades create natural barriers
2. **Michigan** - Great Lakes boundaries
3. **Maine** - Northern forests and coastline
4. **West Virginia** - Extreme topography
5. **Hawaii** - Island geography

### For Comparison
1. **Rhode Island** - Smallest state, very accessible
2. **New Jersey** - Densest road network
3. **Texas** - Contrast between urban and Big Bend
4. **California** - Urban vs Sierra Nevada vs Death Valley

## Tips for Testing

### Start Small
Test with a moderate-sized state first (e.g., Utah, Arizona, Colorado, Oregon):
- Faster download times
- Quick results
- Easy to iterate

### Large States
For very large states (California, Texas, Alaska):
- Expect longer OSM downloads (10-30 minutes)
- Consider increasing OSM timeout in code if needed
- May want to increase raster resolution for detail

### Dense vs Sparse Roads
- **Dense road networks** (East Coast): Lower unreachability distances, less dramatic results
- **Sparse road networks** (Western states): Higher unreachability, more interesting findings

## Troubleshooting

### OSM Download Timeout
If `fetch-data` times out:
```bash
# Run again - OSM caches partial downloads
./venv/bin/python -m src.cli fetch-data
```

### Memory Issues (Large States)
If you run out of memory, reduce raster resolution in `config.yaml`:
```yaml
raster:
  resolution: 500  # Default 250. Higher = less memory, lower detail
```

### Wrong State Still Showing
Make sure you:
1. Saved `config.yaml` after editing
2. Changed both `name` and `fips_code`
3. The state name matches the FIPS code (see table above)

## File Naming Convention

All output files use the **lowercase state name**:
```
data/raw/
  arizona_boundary.geojson
  arizona_roads.geojson

data/processed/
  arizona_boundary_projected.geojson
  arizona_roads_clipped.geojson
  arizona_road_mask.tif
  arizona_distance.tif

outputs/
  results.json
  maps/arizona_unreachability_map.png
  maps/arizona_top5_labeled_map.png
  maps/arizona_unreachability_interactive.html
```

The old state's files remain in place but are not used. You can delete them if you want to free up space.

## Example: Switching to Nevada

```yaml
# config.yaml
state:
  name: "Nevada"
  fips_code: "32"

cost_distance:
  enabled: false  # Start with fast Euclidean mode
```

```bash
# Run pipeline
./venv/bin/python -m src.cli run-all

# Or step by step:
./venv/bin/python -m src.cli fetch-data
./venv/bin/python -m src.cli preprocess
./venv/bin/python -m src.cli compute-distance
./venv/bin/python -m src.cli find-unreachable
./venv/bin/python -m src.cli visualize
```

Expected result: Very high unreachability in central Nevada (Nevada Test Site, military ranges, desert basins).

## Cost-Distance Mode (Advanced)

To use terrain-aware cost-distance for a new state:

1. **Download terrain data** (see `QUICKSTART_COST_DISTANCE.md`)
2. **Enable in config:**
   ```yaml
   cost_distance:
     enabled: true
   ```
3. **Generate cost surface:**
   ```bash
   ./venv/bin/python -m src.cli cost-surface
   ```
4. **Run analysis:**
   ```bash
   ./venv/bin/python -m src.cli compute-distance
   ./venv/bin/python -m src.cli find-unreachable
   ./venv/bin/python -m src.cli visualize
   ```

*Note: Cost-distance adds 2-5 minutes to analysis and requires manual terrain data download.*

---

**Last Updated**: February 14, 2026  
**Tested States**: Utah ✓, Arizona ✓
