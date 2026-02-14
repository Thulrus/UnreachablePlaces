# Quick Start Guide: Enable Cost-Distance Analysis

This guide gets you from Euclidean distance to cost-distance in ~20 minutes.

## Summary

Cost-distance analysis requires 2 terrain datasets:
1. **DEM** (Digital Elevation Model) - for slope calculation
2. **Land Cover** - for terrain type costs

**Bad news:** Automatic download APIs are all broken/restricted  
**Good news:** Manual download is straightforward (~15 min)

## Step-by-Step: Fastest Path

### Step 1: Download DEM (~10 minutes)

**Use OpenTopography** (easiest option):

1. Go to: https://portal.opentopography.org/
2. Click **"Sign In"** → **"Register"** (free, takes 2 min)
3. After login, click **"Select Data"**
4. In the left panel: **Global & Regional DEMs** → **SRTM GL1 (30m)**
5. On the map:
   - Click the **rectangle tool**
   - Draw a box around Utah:
     - **Southwest**: Latitude 37.0, Longitude -114.05
     - **Northeast**: Latitude 42.0, Longitude -109.05
6. Click **"Continue"**
7. Job Options:
   - **Output Format**: GeoTiff
   - Leave other options as default
8. Click **"Submit"**
9. Wait for email (~5-10 minutes)
10. Download the file (will be ~200-300MB ZIP)
11. Extract and move to project:
    ```bash
    cd ~/Downloads
    unzip rasters_*.zip
    mv output.tif ~/Documents/Projects/UnreachablePlaces/data/raw/utah_dem.tif
    ```

**Alternative if OpenTopography down:** Use QGIS SRTM Downloader plugin

### Step 2: Download Land Cover (~10 minutes)

**Direct download from MRLC:**

1. Go to: https://www.mrlc.gov/data
2. Scroll to **"NLCD 2021"**
3. Click **"NLCD 2021 Land Cover (CONUS)"** download button
4. Click through any warnings (it's a large file ~1.5GB)
5. Download will start automatically
6. Wait for download (~5-10 min depending on connection)
7. Extract the ZIP:
    ```bash
    cd ~/Downloads
    unzip nlcd_2021_land_cover_l48_20230630.zip
    ```

8. **Option A - Clip to Utah** (saves disk space):
    ```bash
    cd ~/Documents/Projects/UnreachablePlaces
    
    gdalwarp -cutline data/raw/utah_boundary.geojson \
             -crop_to_cutline \
             -co COMPRESS=LZW \
             -t_srs EPSG:5070 \
             ~/Downloads/nlcd_2021_land_cover_l48_20230630.tif \
             data/raw/utah_landcover.tif
    ```
    
    **Option B - Use full CONUS file** (simpler, needs 4GB space):
    ```bash
    cp ~/Downloads/nlcd_2021_land_cover_l48_20230630.tif \
       ~/Documents/Projects/UnreachablePlaces/data/raw/utah_landcover.tif
    ```

### Step 3: Verify Files

```bash
cd ~/Documents/Projects/UnreachablePlaces

# Check DEM
ls -lh data/raw/utah_dem.tif
gdalinfo data/raw/utah_dem.tif | head -10

# Check Land Cover  
ls -lh data/raw/utah_landcover.tif
gdalinfo data/raw/utah_landcover.tif | head -10
```

You should see both files with reasonable sizes (DEM ~200-500MB, Land Cover ~50-4000MB depending on clipping).

### Step 4: Enable Cost-Distance

Edit `config.yaml`:
```yaml
cost_distance:
  enabled: true  # Change from false to true
```

### Step 5: Generate Cost Surface

```bash
./venv/bin/python -m src.cli cost-surface
```

Expected output:
- Calculates slope from DEM
- Resamples land cover to match resolution
- Generates composite cost surface
- Saves to `data/processed/utah_cost_surface.tif`

### Step 6: Run Full Pipeline

```bash
./venv/bin/python -m src.cli run-all --skip-fetch
```

**What's different:**
- Step [3/5] will say "Mode: COST-DISTANCE (terrain-aware)"
- Computation takes 2-5 minutes (vs 5 seconds for Euclidean)
- Results will differ: mountainous areas and water crossings become more "unreachable"

## Troubleshooting

### "DEM not found" during cost-surface generation
- Make sure file is at exact path: `data/raw/utah_dem.tif`
- Check with: `ls -lh data/raw/utah_dem.tif`

### "Land cover not found"
- File must be named: `data/raw/utah_landcover.tif`
- Check with: `ls -lh data/raw/utah_landcover.tif`

### Download links don't work
- MRLC site changes URLs frequently
- Look for "NLCD 2021" and "Land Cover" keywords on https://www.mrlc.gov/data
- The download is always a large ZIP file (~1.5GB)

### Cost-distance computation is very slow
- Normal: Cost-distance uses MCP algorithm which is ~50-100x slower than Euclidean
- Utah takes ~2-5 minutes on modern hardware
- First run after reboot may be slower (disk caching)

### "scikit-image not found" error
```bash
./venv/bin/pip install scikit-image
```

## Expected Results

### Euclidean Distance (current):
- #1: 32.70 km - Great Salt Lake Desert (40.43°N, -113.50°W)
- Dry lakebed, flat terrain

### Cost-Distance (predicted):
- Top spots will likely shift toward:
  - Mountainous regions (despite shorter straight-line distance, high slope cost)
  - Areas beyond water bodies (10x traversal cost)
  - Dense forests in steep terrain
  
- Great Salt Lake Desert may drop in rank because:
  - It's flat (low slope cost)
  - Open terrain (low land cover cost)
  - High distance but low *effort* to reach

## Time Investment

| Task | Time | One-time? |
|------|------|-----------|
| Create OpenTopography account | 2 min | Yes |
| Request DEM job | 1 min | Yes |
| Wait for DEM processing | 5-10 min | Yes |
| Download DEM | 2 min | Yes |
| Download NLCD | 5-10 min | Yes |
| Clip land cover (optional) | 2 min | Yes |
| Generate cost surface | 1 min | No* |
| Run cost-distance analysis | 3 min | No* |
| **Total first time** | **~20-30 min** | |
| **Subsequent runs** | **~4 min** | |

\* These steps run every time you analyze a region

## Worth It?

**Yes, if:**
- You care about realistic accessibility (trails, hiking difficulty)
- You want to account for water barriers
- You're interested in terrain analysis
- You have 20-30 minutes for one-time setup

**No, if:**
- You only care about road distance (Euclidean works fine)
- You need quick results (<1 minute)
- You don't want to download 2GB of data

## Need Help?

See detailed instructions in `TERRAIN_DATA.md` or helper scripts in `scripts/` directory.
