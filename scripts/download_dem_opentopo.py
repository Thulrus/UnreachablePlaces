#!/usr/bin/env python3
"""
Download DEM from OpenTopography using their API.

OpenTopography provides free access to global elevation data.
You need a free API key from: https://opentopography.org/
"""

import sys
import requests
from pathlib import Path


def download_dem_opentopo(state_bbox, output_path, api_key=None):
    """
    Download DEM from OpenTopography.
    
    Args:
        state_bbox: (west, south, east, north) in WGS84
        output_path: Path to save DEM
        api_key: OpenTopography API key (get free at opentopography.org)
    """
    if not api_key:
        print("=" * 60)
        print("OpenTopography API Key Required")
        print("=" * 60)
        print("\n1. Visit: https://portal.opentopography.org/")
        print("2. Sign in (or create free account)")
        print("3. Go to: MyOpenTopo > Request API Key")
        print("4. Copy your API key")
        print("5. Run this script with: --api-key YOUR_KEY")
        print("\nOr set environment variable: OPENTOPO_API_KEY")
        return False
    
    west, south, east, north = state_bbox
    
    # Use SRTM GL1 (30m global coverage)
    url = "https://portal.opentopography.org/API/globaldem"
    
    params = {
        'demtype': 'SRTMGL1',  # 30m SRTM
        'south': south,
        'north': north,
        'west': west,
        'east': east,
        'outputFormat': 'GTiff',
        'API_Key': api_key
    }
    
    print(f"\nDownloading DEM from OpenTopography...")
    print(f"  Bounds: ({west}, {south}) to ({east}, {north})")
    print(f"  Dataset: SRTM GL1 (30m)")
    print(f"  Output: {output_path}")
    print("\nThis may take several minutes...")
    
    try:
        response = requests.get(url, params=params, stream=True, timeout=600)
        response.raise_for_status()
        
        # Check if we got a valid response
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            print("\n✗ Error: Received HTML instead of GeoTIFF")
            print("Check your API key or try again later.")
            return False
        
        total_size = int(response.headers.get('content-length', 0))
        print(f"  File size: {total_size / (1024*1024):.1f} MB")
        
        # Download
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r  Progress: {percent:.1f}%", end='', flush=True)
        
        print(f"\n\n✓ DEM downloaded successfully!")
        print(f"  Saved to: {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Download failed: {e}")
        return False


def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Download DEM from OpenTopography")
    parser.add_argument('--api-key', help='OpenTopography API key', 
                       default=os.environ.get('OPENTOPO_API_KEY'))
    parser.add_argument('--state', default='Utah', help='State name')
    parser.add_argument('--output', help='Output path',
                       default='data/raw/utah_dem.tif')
    args = parser.parse_args()
    
    # Utah bounding box (WGS84)
    utah_bbox = (-114.05, 37.0, -109.05, 42.0)
    
    success = download_dem_opentopo(utah_bbox, args.output, args.api_key)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
