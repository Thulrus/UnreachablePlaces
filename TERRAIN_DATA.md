# Terrain Data Guide for Cost-Distance Analysis

This guide explains how to obtain and prepare terrain data (DEM and land cover) for cost-distance analysis when automatic download fails.

## Overview

Cost-distance analysis requires two datasets:
- **DEM (Digital Elevation Model)**: For slope calculations
- **Land Cover**: For terrain type traversal costs

## Automatic Download

The pipeline attempts automatic download when `cost_distance.enabled: true`:

```bash
./venv/bin/python -m src.cli fetch-data
```

**Known Issues:**
- DEM download may fill `/tmp` directory (uses ~3-5GB temporarily)
- Land cover S3 URLs may be blocked or changed
- Both require significant bandwidth (~2-4GB total)

## Manual Download Instructions

If automatic download fails, follow these steps:

### 1. Digital Elevation Model (DEM)

**Source**: USGS 3DEP (3D Elevation Program)

**Steps:**
1. Visit [The National Map Downloader](https://apps.nationalmap.gov/downloader/)
2. Click "Elevation Products (3DEP)"
3. Options:
   - **Preferred**: 1/3 arc-second (~10m resolution)
   - **Alternative**: 1 arc-second (~30m resolution)
4. Draw a box around Utah (or your state)
5. Add all tiles to cart and download
6. Merge tiles and save to: `data/raw/utah_dem.tif`

**Using GDAL to merge tiles:**
```bash
# If you downloaded multiple tiles
gdalbuildvrt utah_dem.vrt tile_*.tif
gdal_translate -co COMPRESS=LZW utah_dem.vrt data/raw/utah_dem.tif
```

**Alternative sources:**
- [OpenTopography](https://opentopography.org/) - SRTM or ALOS
- [USGS EarthExplorer](https://earthexplorer.usgs.gov/) - Multiple datasets

### 2. Land Cover Data

**Source**: NLCD 2021 (National Land Cover Database)

**Steps:**
1. Visit [MRLC Data Download](https://www.mrlc.gov/data)
2. Select "NLCD 2021 Land Cover (CONUS)"
3. Download the full CONUS GeoTIFF (~1.5GB compressed)
4. Extract the archive
5. **Option A**: Use full CONUS file
   ```bash
   # Clip to state boundary
   gdalwarp -cutline data/raw/utah_boundary.geojson \
            -crop_to_cutline \
            -co COMPRESS=LZW \
            nlcd_2021_land_cover_l48_20230630.tif \
            data/raw/utah_landcover.tif
   ```

6. **Option B**: Or place full CONUS file directly:
   ```bash
   cp nlcd_2021_land_cover_l48_20230630.tif data/raw/utah_landcover.tif
   ```
   (The pipeline will clip it automatically)

**Alternative land cover sources:**
- [ESA WorldCover](https://worldcover2021.esa.int/) - 10m global
- [USGS GAP](https://www.usgs.gov/programs/gap-analysis-project) - Vegetation

## File Sizes and Requirements

| Dataset | Resolution | Size (Compressed) | Size (Extracted) |
|---------|-----------|-------------------|------------------|
| DEM (Utah, 1/3 arc-sec) | ~10m | ~500MB | ~1.5GB |
| Land Cover (CONUS) | 30m | ~1.5GB | ~4.5GB |
| Land Cover (Utah only) | 30m | ~50MB | ~150MB |

**Disk Space Requirements:**
- Automatic download: 5-10GB temporary + 2GB final
- Manual download: 2GB final (if pre-clipped)

## Verifying Downloaded Data

After manual download, verify files exist:

```bash
ls -lh data/raw/utah_dem.tif
ls -lh data/raw/utah_landcover.tif
```

Check file info:
```bash
gdalinfo data/raw/utah_dem.tif
gdalinfo data/raw/utah_landcover.tif
```

## Running Cost-Distance Analysis

Once data is in place:

```bash
# Generate cost surface
./venv/bin/python -m src.cli cost-surface

# Or run full pipeline (with cost-distance)
./venv/bin/python -m src.cli run-all
```

## Troubleshooting

### "No space left on device" during DEM download
- **Cause**: `/tmp` directory on small partition
- **Solution**: 
  1. Clear `/tmp`: `sudo rm -rf /tmp/tmp*`
  2. Or download manually and place in `data/raw/`

### "403 Forbidden" for land cover
- **Cause**: S3 URL changed or blocked
- **Solution**: Download manually from MRLC website

### Cost surface generation fails
- **Check**: Both files exist and are readable
- **Check**: Files are in correct CRS (will be reprojected automatically)
- **Check**: Files cover the state boundary

### Pipeline falls back to Euclidean distance
- **Check**: `cost_distance.enabled: true` in config.yaml
- **Check**: Cost surface file exists: `data/processed/utah_cost_surface.tif`
- **Run**: `./venv/bin/python -m src.cli cost-surface` first

## Cost-Distance vs Euclidean

**Euclidean Distance** (default):
- Straight-line distance only
- Fast computation (~5 seconds)
- Good for road accessibility

**Cost-Distance** (optional):
- Accounts for terrain difficulty
- Slower computation (~2-5 minutes)
- More realistic for hiking/traversal
- Results may differ significantly near:
  - Water bodies (10x cost)
  - Mountains (2-10x cost based on slope)
  - Forests (2-2.5x cost)

## Example: Expected Results Difference

**Euclidean mode** (current):
- #1: 32.70 km - Great Salt Lake Desert (flat, dry lakebed)

**Cost-distance mode** (predicted):
- #1: May shift to mountainous areas where straight-line distance is shorter but slope makes it harder to reach
- Water crossings become extremely costly
- Steep canyons appear more unreachable than flat deserts

## References

- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
- [NLCD](https://www.mrlc.gov/)
- [The National Map](https://www.usgs.gov/programs/national-geospatial-program/national-map)
- [GDAL Documentation](https://gdal.org/)
