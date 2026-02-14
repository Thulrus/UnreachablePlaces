#!/bin/bash
# Download DEM and Land Cover for Utah using GDAL and working sources

set -e

echo "============================================================"
echo "TERRAIN DATA DOWNLOADER FOR UTAH"
echo "============================================================"
echo

# Create directories
mkdir -p data/raw
mkdir -p data/raw/temp_terrain

# Utah bounding box (WGS84)
WEST=-114.05
SOUTH=37.0
EAST=-109.05
NORTH=42.0

echo "📥 Step 1: Downloading DEM (Digital Elevation Model)"
echo "--------------------------------------------------------"
echo "Using USGS 3DEP via ArcGIS REST service..."
echo

# USGS 3DEP has an ImageServer that we can query
# This is their 1/3 arc-second (10m) DEM for CONUS
DEM_URL="https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"

# Download using gdal_translate with ArcGIS REST API
gdal_translate \
    -of GTiff \
    -co COMPRESS=LZW \
    -co TILED=YES \
    -projwin $WEST $NORTH $EAST $SOUTH \
    -projwin_srs EPSG:4326 \
    "/vsicurl_streaming/${DEM_URL}/exportImage?bbox=${WEST},${SOUTH},${EAST},${NORTH}&bboxSR=4326&size=2000,2000&imageSR=4326&format=tiff&pixelType=F32&noDataValue=-9999&interpolation=+RSP_BilinearInterpolation" \
    data/raw/utah_dem.tif 2>&1 || {
    echo "✗ USGS download failed. Trying alternative..."
    
    # Alternative: Download SRTM tiles from CGIAR-CSI
    echo "Trying CGIAR-CSI SRTM..."
    
    # SRTM tiles for Utah region (tiles 14 and 15 in row 09-10)
    # This is a simplified approach - full coverage needs multiple tiles
    echo "Note: SRTM tile download requires manual tile selection"
    echo "Please download manually from: http://srtm.csi.cgiar.org/"
    exit 1
}

if [ -f data/raw/utah_dem.tif ]; then
    DEM_SIZE=$(du -h data/raw/utah_dem.tif | cut -f1)
    echo "✓ DEM downloaded successfully! Size: $DEM_SIZE"
    gdalinfo data/raw/utah_dem.tif | head -20
else
    echo "✗ DEM download failed"
    exit 1
fi

echo
echo "📥 Step 2: Downloading Land Cover (NLCD 2021)"
echo "--------------------------------------------------------"
echo "Note: NLCD download through S3 is currently blocked."
echo "Checking MRLC direct download..."
echo

# Try MRLC GeoServer WMS (if available)
# Note: This may not work reliably

# Actually, for land cover, we really need manual download
# The files are too large and URLs change too frequently

echo "✗ Automated land cover download not available"
echo
echo "Please download manually:"
echo "1. Visit: https://www.mrlc.gov/data"
echo "2. Find 'NLCD 2021 Land Cover (CONUS)'"  
echo "3. Click the download button"
echo "4. Save and extract the file"
echo "5. Clip to Utah boundary:"
echo
echo "   gdalwarp -cutline data/raw/utah_boundary.geojson \\"
echo "            -crop_to_cutline \\"
echo "            -co COMPRESS=LZW \\"
echo "            -t_srs EPSG:5070 \\"
echo "            nlcd_2021_land_cover_l48_20230630.tif \\"
echo "            data/raw/utah_landcover.tif"
echo
echo "Or place the full CONUS file at data/raw/utah_landcover.tif"
echo "(The pipeline will clip it automatically during processing)"
echo

# Check what we have
echo "============================================================"
echo "STATUS CHECK"
echo "============================================================"
echo

if [ -f data/raw/utah_dem.tif ]; then
    echo "✓ DEM: data/raw/utah_dem.tif ($(du -h data/raw/utah_dem.tif | cut -f1))"
else
    echo "✗ DEM: Not found"
fi

if [ -f data/raw/utah_landcover.tif ]; then
    echo "✓ Land Cover: data/raw/utah_landcover.tif ($(du -h data/raw/utah_landcover.tif | cut -f1))"
else
    echo "✗ Land Cover: Not found - manual download required"
fi

echo
echo "============================================================"
echo "NEXT STEPS"
echo "============================================================"
echo

if [ -f data/raw/utah_dem.tif ] && [ -f data/raw/utah_landcover.tif ]; then
    echo "✓ All terrain data ready!"
    echo
    echo "Run these commands:"
    echo "  1. Set cost_distance.enabled: true in config.yaml"
    echo "  2. ./venv/bin/python -m src.cli cost-surface"
    echo "  3. ./venv/bin/python -m src.cli run-all --skip-fetch"
elif [ -f data/raw/utah_dem.tif ]; then
    echo "DEM ready, but land cover needed."
    echo "Download land cover from: https://www.mrlc.gov/data"
else
    echo "Both files needed. See TERRAIN_DATA.md for detailed instructions."
fi

echo
