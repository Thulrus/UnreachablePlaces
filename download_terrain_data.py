#!/usr/bin/env python3
"""
Helper script to download terrain data using alternative sources.

This script provides simplified download options when automatic download fails.
"""

import subprocess
import sys
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")


def check_gdal():
    """Check if GDAL tools are available."""
    try:
        subprocess.run(['gdalinfo', '--version'],
                       capture_output=True,
                       check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def download_dem_alternative():
    """Provide instructions for DEM download using OpenTopography."""
    print_header("DEM Download - Alternative Source: OpenTopography")

    print("OpenTopography provides easier access to elevation data.")
    print("\nOption 1: Web Interface (Easiest)")
    print("  1. Visit: https://opentopography.org/")
    print("  2. Click 'Data' > 'Browse/Select Data'")
    print("  3. Select 'SRTM GL1 (30m)' or 'ALOS World 3D (30m)'")
    print("  4. Draw a box around your area or upload boundary")
    print("  5. Select output: 'GeoTiff'")
    print("  6. Download and save as: data/raw/utah_dem.tif")

    print("\nOption 2: Copernicus DEM (Alternative)")
    print("  1. Visit: https://portal.opentopography.org/dataCatalog")
    print("  2. Search for 'Copernicus DEM GLO-30'")
    print("  3. Select your region and download")

    print("\nOption 3: USGS Manual Download")
    print("  1. Visit: https://apps.nationalmap.gov/downloader/")
    print("  2. Search for your state")
    print("  3. Select 'Elevation Products (3DEP)'")
    print("  4. Choose 1/3 or 1 arc-second DEM")
    print("  5. Download all tiles for your area")

    if check_gdal():
        print("\n✓ GDAL is installed - you can merge tiles with:")
        print("  gdalbuildvrt utah_dem.vrt downloaded_tiles/*.tif")
        print(
            "  gdal_translate -co COMPRESS=LZW utah_dem.vrt data/raw/utah_dem.tif"
        )
    else:
        print("\n⚠ GDAL not found. To merge tiles, install with:")
        print("  Ubuntu/Debian: sudo apt install gdal-bin")
        print("  Mac: brew install gdal")

    return "data/raw/utah_dem.tif"


def download_landcover_alternative():
    """Provide instructions for land cover download."""
    print_header("Land Cover Download - MRLC")

    print("The NLCD S3 URLs are currently restricted.")
    print("\nOption 1: Direct Download from MRLC (Recommended)")
    print("  1. Visit: https://www.mrlc.gov/data")
    print("  2. Find 'NLCD 2021' section")
    print("  3. Click 'Download' for CONUS Land Cover")
    print("  4. Large file warning - click 'Continue'")
    print("  5. Save and extract the .tif file")

    print("\nOption 2: Google Earth Engine (Advanced)")
    print("  1. Use Earth Engine if you have an account")
    print("  2. Export NLCD 2021 for your region")

    print("\nOption 3: State-specific data")
    print("  1. Some states provide their own land cover data")
    print("  2. Check your state's GIS data portal")

    if check_gdal():
        print("\n✓ GDAL is installed - you can clip to state with:")
        print("  gdalwarp -cutline data/raw/utah_boundary.geojson \\")
        print("           -crop_to_cutline -co COMPRESS=LZW \\")
        print("           nlcd_2021_land_cover_l48.tif \\")
        print("           data/raw/utah_landcover.tif")

    return "data/raw/utah_landcover.tif"


def check_files_exist():
    """Check if terrain data files already exist."""
    dem_path = Path("data/raw/utah_dem.tif")
    lc_path = Path("data/raw/utah_landcover.tif")

    print_header("Checking for existing terrain data...")

    if dem_path.exists():
        size_mb = dem_path.stat().st_size / (1024 * 1024)
        print(f"✓ DEM found: {dem_path} ({size_mb:.1f} MB)")
    else:
        print(f"✗ DEM not found: {dem_path}")

    if lc_path.exists():
        size_mb = lc_path.stat().st_size / (1024 * 1024)
        print(f"✓ Land cover found: {lc_path} ({size_mb:.1f} MB)")
    else:
        print(f"✗ Land cover not found: {lc_path}")

    return dem_path.exists() and lc_path.exists()


def main():
    """Main function."""
    print_header("Terrain Data Download Helper")

    print(
        "This script helps download terrain data for cost-distance analysis.")
    print(
        "Automatic download is currently unreliable, so manual download is recommended."
    )

    # Check current status
    if check_files_exist():
        print("\n✓ All terrain data files present!")
        print("\nYou can now run:")
        print("  1. Edit config.yaml: set cost_distance.enabled: true")
        print("  2. ./venv/bin/python -m src.cli cost-surface")
        print("  3. ./venv/bin/python -m src.cli run-all")
        return 0

    print("\nWhat would you like to download?")
    print("  1. DEM (Digital Elevation Model)")
    print("  2. Land Cover (NLCD)")
    print("  3. Both")
    print("  4. Check status and exit")
    print("  5. Exit")

    try:
        choice = input("\nEnter choice (1-5): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting.")
        return 0

    if choice == '1':
        dem_path = download_dem_alternative()
        print(f"\n📥 After downloading, place DEM file at: {dem_path}")
    elif choice == '2':
        lc_path = download_landcover_alternative()
        print(f"\n📥 After downloading, place land cover file at: {lc_path}")
    elif choice == '3':
        dem_path = download_dem_alternative()
        lc_path = download_landcover_alternative()
        print(f"\n📥 After downloading, place files at:")
        print(f"  DEM: {dem_path}")
        print(f"  Land cover: {lc_path}")
    elif choice == '4':
        check_files_exist()
    else:
        print("Exiting.")

    print("\n" + "=" * 60)
    print("See TERRAIN_DATA.md for detailed instructions")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
