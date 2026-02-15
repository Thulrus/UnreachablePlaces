"""
Utility script to extract terrain data from national files for a specific state.

This handles automatic extraction of DEM and land cover from national files
when cost-distance analysis is enabled.
"""
import subprocess
import sys
from pathlib import Path

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

    # Paths
    raw_dir = config.get_path('raw_data')
    dem_path = raw_dir / f"{state_lower}_dem.tif"
    landcover_path = raw_dir / f"{state_lower}_landcover.tif"
    boundary_path = raw_dir / f"{state_lower}_boundary.geojson"

    if not boundary_path.exists():
        print(f"Warning: State boundary not found: {boundary_path}")
        print("Run 'fetch-data' first to download boundary")
        return None, None

    # Check if DEM is enabled and needed
    dem_enabled = config.get('cost_distance.terrain_data.dem.enabled', True)
    dem_final = None

    if dem_enabled:
        if not dem_path.exists():
            # Try local extraction first
            local_dem = config.get('cost_distance.terrain_data.dem.local_file')
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
                    print(f"  Warning: Local DEM file not found: {local_dem}")
                    print("  Continuing without DEM (flat terrain assumed)")
            else:
                print(
                    f"  Warning: DEM not found for {state_name} and no local source configured"
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
