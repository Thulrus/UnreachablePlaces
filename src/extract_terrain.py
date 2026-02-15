"""
Utility script to extract terrain data from national files for a specific state.

This handles automatic extraction of DEM and land cover from national files
when cost-distance analysis is enabled.
"""
import re
import subprocess
import sys
from pathlib import Path
from typing import List

from .config import get_config


def extract_from_national_file(national_file: Path, state_boundary_path: Path,
                               output_path: Path) -> bool:
    """
    Extract state-specific data from national raster file using gdalwarp.
    
    Args:
        national_file: Path to national raster (e.g., NLCD for whole USA)
        state_boundary_path: Path to state boundary GeoJSON
        output_path: Where to save extracted state raster
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Extracting {output_path.name} from national file...")
        print(f"  Source: {national_file.name}")

        cmd = [
            'gdalwarp', '-cutline',
            str(state_boundary_path), '-crop_to_cutline', '-co',
            'COMPRESS=LZW',
            str(national_file),
            str(output_path)
        ]

        result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=300)

        if result.returncode == 0:
            print(f"  ✓ Extracted to {output_path}")
            return True
        else:
            print(f"  ✗ gdal warp failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ Extraction timed out after 5 minutes")
        return False
    except FileNotFoundError:
        print(
            f"  ✗ gdalwarp not found. Install GDAL: sudo apt install gdal-bin")
        return False
    except Exception as e:
        print(f"  ✗ Extraction error: {e}")
        return False


def parse_gmted_tile_bounds(
        folder_name: str) -> tuple[float, float, float, float] | None:
    """
    Parse GMTED2010 folder name to extract geographic bounds.
    
    Example: GMTED2010N30W120_075 means:
    - N30: starts at 30°N
    - W120: starts at 120°W
    - Tiles are 30° longitude × 20° latitude
    
    Args:
        folder_name: e.g., "GMTED2010N30W120_075"
        
    Returns:
        Tuple of (min_lon, min_lat, max_lon, max_lat) or None if invalid
    """
    pattern = r'GMTED2010N(\d+)W(\d+)_\d+'
    match = re.match(pattern, folder_name)

    if not match:
        return None

    lat_start = int(match.group(1))
    lon_start = int(match.group(2))

    # GMTED tiles are 30° wide (longitude) × 20° tall (latitude)
    min_lon = -lon_start
    max_lon = min_lon + 30
    min_lat = lat_start
    max_lat = lat_start + 20

    return (min_lon, min_lat, max_lon, max_lat)


def find_gmted_tiles(gmted_dir: Path,
                     state_bounds: tuple[float, float, float, float],
                     variant: str = 'mea') -> List[Path]:
    """
    Find all GMTED tiles that intersect with given state bounds.
    
    Args:
        gmted_dir: Path to GMTED2010 directory
        state_bounds: Tuple of (min_lon, min_lat, max_lon, max_lat) in EPSG:4326
        variant: GMTED variant to use (mea, med, min, max, etc.)
        
    Returns:
        List of paths to GMTED .tif files that cover the state
    """
    if not gmted_dir.exists():
        return []

    state_min_lon, state_min_lat, state_max_lon, state_max_lat = state_bounds
    matching_tiles = []

    # Scan all GMTED tile folders
    for tile_dir in sorted(gmted_dir.iterdir()):
        if not tile_dir.is_dir() or not tile_dir.name.startswith('GMTED2010'):
            continue

        tile_bounds = parse_gmted_tile_bounds(tile_dir.name)
        if not tile_bounds:
            continue

        tile_min_lon, tile_min_lat, tile_max_lon, tile_max_lat = tile_bounds

        # Check for intersection
        if (tile_max_lon >= state_min_lon and tile_min_lon <= state_max_lon
                and tile_max_lat >= state_min_lat
                and tile_min_lat <= state_max_lat):

            # Find the specific variant file
            pattern = f"*_gmted_{variant}075.tif"
            matching_files = list(tile_dir.glob(pattern))

            if matching_files:
                matching_tiles.append(matching_files[0])

    return matching_tiles


def create_gmted_vrt(gmted_tiles: List[Path], output_vrt: Path) -> bool:
    """
    Create a virtual raster (VRT) that mosaics multiple GMTED tiles.
    
    Args:
        gmted_tiles: List of GMTED .tif files to mosaic
        output_vrt: Path where VRT should be saved
        
    Returns:
        True if successful, False otherwise
    """
    if not gmted_tiles:
        return False

    try:
        cmd = ['gdalbuildvrt', str(output_vrt)] + [str(t) for t in gmted_tiles]

        result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=60)

        if result.returncode == 0:
            return True
        else:
            print(f"  ✗ gdalbuildvrt failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ VRT creation timed out")
        return False
    except FileNotFoundError:
        print(
            f"  ✗ gdalbuildvrt not found. Install GDAL: sudo apt install gdal-bin"
        )
        return False
    except Exception as e:
        print(f"  ✗ VRT creation error: {e}")
        return False


def extract_dem_from_gmted(gmted_dir: Path,
                           state_boundary_path: Path,
                           output_path: Path,
                           variant: str = 'mea') -> bool:
    """
    Extract state DEM from GMTED2010 tiles.
    
    This will:
    1. Find which GMTED tiles cover the state
    2. Create a VRT to mosaic them (if multiple)
    3. Extract the state area using gdalwarp
    
    Args:
        gmted_dir: Path to GMTED2010 directory
        state_boundary_path: Path to state boundary GeoJSON
        output_path: Where to save extracted DEM
        variant: GMTED variant ('mea' for mean, 'med' for median, etc.)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"Extracting DEM from GMTED2010 ({variant} variant)...")

        # Get state bounds to find relevant tiles
        import geopandas as gpd
        boundary = gpd.read_file(state_boundary_path)
        bounds_4326 = boundary.to_crs('EPSG:4326').total_bounds

        # Find tiles
        tiles = find_gmted_tiles(gmted_dir, tuple(bounds_4326), variant)

        if not tiles:
            print(f"  ✗ No GMTED tiles found covering the state")
            return False

        print(
            f"  Found {len(tiles)} GMTED tile(s): {[t.parent.name for t in tiles]}"
        )

        # Create VRT if multiple tiles, or use single tile directly
        if len(tiles) == 1:
            source_raster = tiles[0]
        else:
            vrt_path = output_path.parent / f"{output_path.stem}_gmted.vrt"
            print(f"  Creating VRT mosaic...")
            if not create_gmted_vrt(tiles, vrt_path):
                return False
            source_raster = vrt_path

        # Extract state area
        print(f"  Extracting state area...")
        cmd = [
            'gdalwarp', '-cutline',
            str(state_boundary_path), '-crop_to_cutline', '-co',
            'COMPRESS=LZW',
            str(source_raster),
            str(output_path)
        ]

        result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=300)

        if result.returncode == 0:
            print(f"  ✓ Extracted DEM to {output_path}")

            # Clean up VRT if we created one
            if len(tiles) > 1:
                vrt_path.unlink(missing_ok=True)

            return True
        else:
            print(f"  ✗ gdalwarp failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ Extraction timed out")
        return False
    except Exception as e:
        print(f"  ✗ Extraction error: {e}")
        return False


def ensure_terrain_data(config,
                        state_name: str) -> tuple[Path | None, Path | None]:
    """
    Ensure DEM and land cover exist for the state.
    Tries local extraction first if terrain data is missing.
    
    Args:
        config: Configuration object
        state_name: Name of state (e.g., "Utah")
        
    Returns:
        Tuple of (dem_path, landcover_path). Either can be None if disabled/failed.
    """
    state_lower = state_name.lower()

    # Paths - use state-specific folder
    raw_dir = config.get_path('raw_data')
    state_folder = raw_dir / state_lower
    state_folder.mkdir(parents=True, exist_ok=True)
    
    dem_path = state_folder / "dem.tif"
    landcover_path = state_folder / "landcover.tif"
    boundary_path = state_folder / "boundary.geojson"

    if not boundary_path.exists():
        print(f"Warning: State boundary not found: {boundary_path}")
        print("Run 'fetch-data' first to download boundary")
        return None, None

    # Check if DEM is enabled and needed
    dem_enabled = config.get('cost_distance.terrain_data.dem.enabled', True)
    dem_final = None

    if dem_enabled:
        if not dem_path.exists():
            # Try GMTED2010 first if available
            gmted_dir_config = config.get(
                'cost_distance.terrain_data.dem.gmted_dir')
            if gmted_dir_config:
                gmted_dir = Path(gmted_dir_config)
                if gmted_dir.exists():
                    gmted_variant = config.get(
                        'cost_distance.terrain_data.dem.gmted_variant', 'mea')
                    print(
                        f"DEM not found for {state_name}, extracting from GMTED2010..."
                    )
                    if extract_dem_from_gmted(gmted_dir, boundary_path,
                                              dem_path, gmted_variant):
                        dem_final = dem_path
                    else:
                        print("  Warning: GMTED extraction failed")
                else:
                    print(f"  Warning: GMTED directory not found: {gmted_dir}")

            # Fall back to local_file if GMTED didn't work
            if not dem_final:
                local_dem = config.get(
                    'cost_distance.terrain_data.dem.local_file')
                if local_dem:
                    local_dem_path = Path(local_dem)
                    if local_dem_path.exists():
                        print(
                            f"DEM not found for {state_name}, extracting from {local_dem_path.name}..."
                        )
                        if extract_from_national_file(local_dem_path,
                                                      boundary_path, dem_path):
                            dem_final = dem_path
                        else:
                            print(
                                "  Warning: Extraction failed, continuing without DEM (flat terrain assumed)"
                            )
                    else:
                        print(
                            f"  Warning: Local DEM file not found: {local_dem}"
                        )
                        print(
                            "  Continuing without DEM (flat terrain assumed)")
                else:
                    print(
                        f"  Warning: DEM not found for {state_name} and no source configured"
                    )
                    print("  Continuing without DEM (flat terrain assumed)")
        else:
            dem_final = dem_path
    else:
        print("DEM disabled in config, assuming flat terrain")

    # Check if land cover is enabled and needed
    landcover_enabled = config.get(
        'cost_distance.terrain_data.landcover.enabled', True)
    landcover_final = None

    if landcover_enabled:
        if not landcover_path.exists():
            # Try local extraction first
            local_landcover = config.get(
                'cost_distance.terrain_data.landcover.local_file')
            if local_landcover:
                local_lc_path = Path(local_landcover)
                if local_lc_path.exists():
                    print(
                        f"Land cover not found for {state_name}, extracting from {local_lc_path.name}..."
                    )
                    if extract_from_national_file(local_lc_path, boundary_path,
                                                  landcover_path):
                        landcover_final = landcover_path
                    else:
                        print(
                            "  Warning: Extraction failed, continuing without land cover (uniform cost)"
                        )
                else:
                    print(
                        f"  Warning: Local land cover file not found: {local_landcover}"
                    )
                    print("  Continuing without land cover (uniform cost)")
            else:
                print(
                    f"  Warning: Land cover not found for {state_name} and no local source configured"
                )
                print("  Continuing without land cover (uniform cost)")
        else:
            landcover_final = landcover_path
    else:
        print("Land cover disabled in config, using uniform cost")

    return dem_final, landcover_final


def main():
    """CLI entry point for manual terrain extraction."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract terrain data for a state')
    parser.add_argument('--config',
                        default='config.yaml',
                        help='Path to config file')
    parser.add_argument(
        'state',
        nargs='?',
        help='State name (optional, uses config if not provided)')

    args = parser.parse_args()

    config = get_config(args.config)
    state_name = args.state or config.state_name

    print(f"Extracting terrain data for {state_name}...")
    dem_path, landcover_path = ensure_terrain_data(config, state_name)

    if dem_path:
        print(f"✓ DEM available: {dem_path}")
    else:
        print("✗ DEM not available (assuming flat terrain)")

    if landcover_path:
        print(f"✓ Land cover available: {landcover_path}")
    else:
        print("✗ Land cover not available (using uniform cost)")


if __name__ == "__main__":
    main()
