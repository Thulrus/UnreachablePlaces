#!/usr/bin/env python3
"""
Download terrain data using GDAL and publicly available sources.

This script uses GDAL's virtual file systems to download data
without requiring API keys.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_gdal():
    """Check if GDAL is installed."""
    try:
        result = subprocess.run(['gdalinfo', '--version'],
                                capture_output=True,
                                text=True,
                                check=True)
        print(f"✓ GDAL found: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ GDAL not found")
        print("\nGDAL is required for this script.")
        print("Install with:")
        print("  Ubuntu/Debian: sudo apt install gdal-bin python3-gdal")
        print("  Mac: brew install gdal")
        print("  Or use conda: conda install -c conda-forge gdal")
        return False


def download_dem_aws_terrain():
    """
    Download DEM using AWS Terrain Tiles.
    
    AWS Terrain Tiles provides free global elevation data.
    """
    print("\n" + "=" * 60)
    print("Downloading DEM from AWS Terrain Tiles")
    print("=" * 60)

    # AWS Terrain Tiles URL format
    # These are Mapzen/Tilezen terrain tiles hosted on AWS S3
    base_url = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff"

    # For Utah, we need to determine which tiles to download
    # Utah roughly covers: -114 to -109 longitude, 37 to 42 latitude

    print("\nAWS Terrain Tiles covers: zoom levels 0-14")
    print("For state-level data, we need multiple tiles.")
    print("\nAlternative: Use GDAL to download directly from USGS:")

    # Actually, let's use GDAL's /vsicurl/ to access USGS directly
    output_path = Path("data/raw/utah_dem.tif")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Utah bounding box
    bbox = "-114.05 37.0 -109.05 42.0"

    print(f"\nDownloading DEM for Utah...")
    print(f"  Bounds: {bbox}")
    print(f"  Using: USGS 3DEP via GDAL")
    print(f"  Output: {output_path}")

    # Try to use USGS 3DEP WCS service
    wcs_url = ("https://elevation.nationalmap.gov/arcgis/services/"
               "3DEPElevation/ImageServer/WCSServer?"
               "SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
               "&COVERAGEID=DEP3Elevation"
               "&SUBSET=Long(-114.05,-109.05)"
               "&SUBSET=Lat(37.0,42.0)"
               "&FORMAT=image/tiff")

    print("\nAttempting download via USGS WCS service...")

    cmd = [
        'gdal_translate', '-of', 'GTiff', '-co', 'COMPRESS=LZW', '-co',
        'TILED=YES', f'/vsicurl/{wcs_url}',
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"\n✓ Successfully downloaded DEM!")
        return True
    except subprocess.CalledProcessError:
        print("\n✗ WCS download failed")
        print("\nTrying alternative method...")
        return False


def download_landcover_direct():
    """
    Try to download NLCD directly from MRLC.
    """
    print("\n" + "=" * 60)
    print("Downloading Land Cover from MRLC")
    print("=" * 60)

    # MRLC sometimes has direct download links
    # The issue is they change the URLs frequently

    urls_to_try = [
        "https://www.mrlc.gov/downloads/sciweb1/shared/mrlc/metadata/NLCD_2021_Land_Cover_L48.zip",
        "http://www.mrlc.gov/nlcd2021.php",
    ]

    print("\nSearching for working download URL...")
    print("Note: MRLC frequently changes download URLs.")
    print("\nRecommendation: Manual download from MRLC website:")
    print("1. Visit: https://www.mrlc.gov/data")
    print("2. Click on NLCD 2021")
    print("3. Download CONUS Land Cover")
    print("4. Save to: data/raw/utah_landcover.tif (or full CONUS file)")

    return False


def guide_manual_download():
    """Provide comprehensive manual download guide."""
    print("\n" + "=" * 60)
    print("MANUAL DOWNLOAD GUIDE")
    print("=" * 60)

    print("\n📥 DEM (Digital Elevation Model)")
    print("-" * 60)
    print("\nOption 1: OpenTopography (Recommended - Easiest)")
    print("  1. Visit: https://portal.opentopography.org/")
    print("  2. Click 'Data' > 'Select Data'")
    print("  3. Search for 'SRTM GL1' (30m) or 'ALOS' (30m)")
    print("  4. Draw box around Utah: (-114, 37) to (-109, 42)")
    print("  5. Select 'GeoTiff' format")
    print("  6. Submit job (requires free account)")
    print("  7. Download when ready (email notification)")
    print("  8. Save as: data/raw/utah_dem.tif")

    print("\nOption 2: USGS National Map")
    print("  1. Visit: https://apps.nationalmap.gov/downloader/")
    print("  2. Enter location: 'Utah'")
    print("  3. Select 'Elevation Products (3DEP)'")
    print("  4. Choose: 1/3 arc-second or 1 arc-second")
    print("  5. Download all tiles")
    print("  6. Merge with GDAL:")
    print("     gdalbuildvrt utah.vrt tiles/*.tif")
    print("     gdal_translate utah.vrt data/raw/utah_dem.tif")

    print("\nOption 3: USGS EarthExplorer")
    print("  1. Visit: https://earthexplorer.usgs.gov/")
    print("  2. Search for Utah")
    print("  3. Data Sets > Digital Elevation > SRTM")
    print("  4. Download tiles and merge")

    print("\n\n📥 Land Cover")
    print("-" * 60)
    print("\nOption 1: MRLC Website (Recommended)")
    print("  1. Visit: https://www.mrlc.gov/data")
    print("  2. Find 'NLCD 2021 Land Cover'")
    print("  3. Click download for CONUS")
    print("  4. Extract the .tif file")
    print("  5. Optional - clip to Utah:")
    print("     gdalwarp -cutline data/raw/utah_boundary.geojson \\")
    print("              -crop_to_cutline -co COMPRESS=LZW \\")
    print("              nlcd_2021_land_cover_l48.tif \\")
    print("              data/raw/utah_landcover.tif")
    print("  6. Or place full CONUS file at: data/raw/utah_landcover.tif")

    print("\n\n✓ After downloading both files:")
    print("  1. Verify files exist:")
    print("     ls -lh data/raw/utah_dem.tif")
    print("     ls -lh data/raw/utah_landcover.tif")
    print("  2. Enable cost-distance in config.yaml:")
    print("     cost_distance.enabled: true")
    print("  3. Generate cost surface:")
    print("     ./venv/bin/python -m src.cli cost-surface")
    print("  4. Run full pipeline:")
    print("     ./venv/bin/python -m src.cli run-all --skip-fetch")


def main():
    print("=" * 60)
    print("TERRAIN DATA DOWNLOADER")
    print("=" * 60)

    print(
        "\nThis script helps download terrain data for cost-distance analysis."
    )

    if not check_gdal():
        print(
            "\n⚠️  GDAL not available - showing manual download guide instead."
        )
        guide_manual_download()
        return 1

    print("\nWhat would you like to download?")
    print("  1. DEM only (elevation data)")
    print("  2. Land Cover only")
    print("  3. Both DEM and Land Cover")
    print("  4. Show manual download guide")
    print("  5. Exit")

    try:
        choice = input("\nEnter choice (1-5): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting.")
        return 0

    success = False

    if choice == '1':
        success = download_dem_aws_terrain()
        if not success:
            print("\n⚠️  Automatic download failed.")
            print("Please use manual download method (see guide below)")
    elif choice == '2':
        success = download_landcover_direct()
        if not success:
            print("\n⚠️  Automatic download not available.")
            print("Please use manual download method (see guide below)")
    elif choice == '3':
        dem_ok = download_dem_aws_terrain()
        lc_ok = download_landcover_direct()
        success = dem_ok and lc_ok
    elif choice == '4':
        guide_manual_download()
        return 0
    else:
        print("Exiting.")
        return 0

    if not success:
        guide_manual_download()

    return 0


if __name__ == '__main__':
    sys.exit(main())
