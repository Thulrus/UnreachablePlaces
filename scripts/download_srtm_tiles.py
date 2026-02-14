#!/usr/bin/env python3
"""
Download SRTM elevation tiles for Utah.

Uses OpenDEM GeoTIFF cloud service which provides direct access
to SRTM and other elevation datasets.
"""

import sys
import subprocess
from pathlib import Path
import math


def download_srtm_tile(lat, lon, output_dir):
    """
    Download a single SRTM tile using GDAL.
    
    SRTM tiles are 1° x 1° and named by their SW corner.
    """
    # Construct SRTM tile name
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    lat_str = f"{abs(int(lat)):02d}"
    lon_str = f"{abs(int(lon)):03d}"
    
    tile_name = f"{lat_dir}{lat_str}{lon_dir}{lon_str}"
    
    # Try OpenTopography's public SRTM archives
    # Note: These may require authentication
    urls_to_try = [
        f"https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/SRTM_GL1/SRTM_GL1_srtm/  {tile_name}.hgt",
        f"/vsis3/raster/SRTM_GL1/SRTM_GL1_srtm/{tile_name}.hgt",
        f"https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/{tile_name}.zip",
    ]
    
    output_path = output_dir / f"{tile_name}.tif"
    
    print(f"  Trying to download tile {tile_name}...")
    
    # For now, return the tile name - we'll need to download manually or use a different service
    return None


def main():
    print("=" * 60)
    print("SRTM TILE DOWNLOADER FOR UTAH")
    print("=" * 60)
    
    # Utah coverage: approximately -114 to -109 longitude, 37 to 42 latitude
    # SRTM tiles are 1° x 1°, so we need:
    # Longitude: -114 to -109 = tiles W114, W113, W112, W111, W110, W109
    # Latitude: 37 to 42 = tiles N37, N38, N39, N40, N41
    
    min_lon, max_lon = -114, -109
    min_lat, max_lat = 37, 42
    
    tiles_needed = []
    for lat in range(min_lat, max_lat + 1):
        for lon in range(min_lon, max_lon + 1):
            tiles_needed.append((lat, lon))
    
    print(f"\nUtah requires {len(tiles_needed)} SRTM tiles")
    print(f"Coverage: {min_lon}°W to {max_lon}°W, {min_lat}°N to {max_lat}°N")
    
    print("\n" + "=" * 60)
    print("AUTOMATED DOWNLOAD NOT AVAILABLE")
    print("=" * 60)
    
    print("\nUnfortunately, there's no reliable free API for SRTM tiles")
    print("without authentication.")
    
    print("\n📋 RECOMMENDED APPROACH:")
    print("-" * 60)
    
    print("\nOption 1: Use OpenTopography (Easiest)")
    print("  Benefits: Simple web interface, no command line needed")
    print("  Steps:")
    print("    1. Go to: https://portal.opentopography.org/")
    print("    2. Create free account (takes 2 minutes)")
    print("    3. Click 'Select Data' > 'Global & Regional DEMs'")
    print("    4. Select 'SRTM GL1 (30m)'")
    print("    5. On map: Draw a box around Utah")
    print("       Southwest corner: -114.05°, 37.0°")
    print("       Northeast corner: -109.05°, 42.0°")
    print("    6. Select output format: 'GeoTiff'")
    print("    7. Click 'Submit'")
    print("    8. Wait for email (usually 5-15 minutes)")
    print("    9. Download the ZIP file")
    print("   10. Extract and rename to: data/raw/utah_dem.tif")
    
    print("\nOption 2: Use QGIS SRTM Downloader (Good for visualization)")
    print("  Benefits: GUI-based, can preview terrain")
    print("  Steps:")
    print("    1. Install QGIS: https://qgis.org/")
    print("    2. Open QGIS")
    print("    3. Menu: Raster > Analysis > SRTM Downloader")
    print("    4. Draw box over Utah")
    print("    5. Download tiles")
    print("    6. Merge tiles: Raster > Miscellaneous > Merge")
    print("    7. Save as: data/raw/utah_dem.tif")
    
    print("\nOption 3: Download individual SRTM tiles manually")
    print("  Source: EarthExplorer (requires free USGS account)")
    print("  Steps:")
    print("    1. Go to: https://earthexplorer.usgs.gov/")
    print("    2. Create free account")
    print("    3. Search coordinates: Utah")
    print("    4. Data Sets > Digital Elevation > SRTM > SRTM 1Arc-Second Global")
    print("    5. Results > Download tiles for:")
    
    # List all tiles needed
    for lat in range(min_lat, max_lat + 1):
        for lon in range(min_lon, max_lon + 1):
            lat_dir = 'N' if lat >= 0 else 'S'
            lon_dir = 'E' if lon >= 0 else 'W'
            tile_name = f"{lat_dir}{abs(lat):02d}{lon_dir}{abs(lon):03d}"
            print(f"       - {tile_name}")
    
    print("\n    6. Merge tiles using GDAL:")
    print("       cd data/raw")
    print("       gdalbuildvrt utah_dem.vrt *.hgt")
    print("       gdal_translate -co COMPRESS=LZW utah_dem.vrt utah_dem.tif")
    
    print("\n" + "=" * 60)
    print("\n💡 TIP: Option 1 (OpenTopography) is fastest for one-time download!")
    print("   Takes about 15 minutes total including account creation.")
    print("\n" + "=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
