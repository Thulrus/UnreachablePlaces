"""
Data acquisition module for fetching geospatial data.

This module handles:
- Downloading state boundary from US Census TIGER
- Fetching road network from OpenStreetMap
- Optionally fetching settlement data
- Downloading DEM (Digital Elevation Model) from USGS 3DEP
- Downloading land cover from NLCD
"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

import geopandas as gpd
import osmnx as ox
import rasterio
import requests
from rasterio.mask import mask
from rasterio.merge import merge
from tqdm import tqdm

from .config import get_config


class DataFetcher:
    """Handles fetching geospatial data from various sources."""

    def __init__(self, config=None):
        """
        Initialize DataFetcher.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()
        self.config.ensure_directories()

    def fetch_state_boundary(self,
                             state_name: Optional[str] = None
                             ) -> gpd.GeoDataFrame:
        """
        Fetch state boundary polygon from US Census TIGER.
        
        Args:
            state_name: Name of the state. If None, uses config value.
            
        Returns:
            GeoDataFrame with state boundary
        """
        state_name = state_name or self.config.state_name
        print(f"Fetching boundary for {state_name}...")

        # Use Census Bureau TIGER API
        # Download state boundaries from Census Bureau
        url = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_state_20m.zip"

        output_path = self.config.get_path(
            'raw_data') / f"{state_name.lower()}_boundary.geojson"

        # Check if already exists
        if output_path.exists():
            print(f"Boundary already exists at {output_path}")
            gdf = gpd.read_file(output_path)
            return gdf

        try:
            # Download and filter
            print(f"Downloading from {url}...")
            gdf = gpd.read_file(url)

            # Filter to specific state
            state_gdf = gdf[gdf['NAME'].str.upper() ==
                            state_name.upper()].copy()

            if len(state_gdf) == 0:
                raise ValueError(f"State '{state_name}' not found in dataset")

            # Save to file
            state_gdf.to_file(output_path, driver='GeoJSON')
            print(f"Saved boundary to {output_path}")

            return state_gdf

        except Exception as e:
            print(f"Error fetching state boundary: {e}")
            raise

    def fetch_roads(
            self,
            boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """
        Fetch road network from OpenStreetMap.
        
        Args:
            boundary: GeoDataFrame with boundary polygon. If None, fetches it first.
            
        Returns:
            GeoDataFrame with road network
        """
        if boundary is None:
            boundary = self.fetch_state_boundary()

        state_name = self.config.state_name
        output_path = self.config.get_path(
            'raw_data') / f"{state_name.lower()}_roads.geojson"

        # Check if already exists
        if output_path.exists():
            print(f"Roads already exist at {output_path}")
            return gpd.read_file(output_path)

        print(f"Fetching roads for {state_name} from OpenStreetMap...")
        print("This may take several minutes...")

        try:
            # Get the geometry in WGS84 for OSMnx
            boundary_wgs84 = boundary.to_crs('EPSG:4326')
            polygon = boundary_wgs84.geometry.iloc[0]

            # Configure OSMnx
            ox.settings.use_cache = True
            ox.settings.log_console = True

            # Fetch road network
            # Using custom filter for road types
            road_types = self.config.road_types
            if road_types:
                # Build custom filter
                road_filter = '["highway"~"' + '|'.join(road_types) + '"]'
                G = ox.graph_from_polygon(polygon,
                                          network_type='drive',
                                          custom_filter=road_filter)
            else:
                # Use default drive network
                G = ox.graph_from_polygon(polygon, network_type='drive')

            # Convert to GeoDataFrame
            edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

            print(f"Downloaded {len(edges)} road segments")

            # Save to file
            edges.to_file(output_path, driver='GeoJSON')
            print(f"Saved roads to {output_path}")

            return edges

        except Exception as e:
            print(f"Error fetching roads: {e}")
            raise

    def fetch_settlements(
            self,
            boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """
        Fetch settlement points from OpenStreetMap.
        
        Args:
            boundary: GeoDataFrame with boundary polygon. If None, fetches it first.
            
        Returns:
            GeoDataFrame with settlement points
        """
        if boundary is None:
            boundary = self.fetch_state_boundary()

        state_name = self.config.state_name
        output_path = self.config.get_path(
            'raw_data') / f"{state_name.lower()}_settlements.geojson"

        # Check if already exists
        if output_path.exists():
            print(f"Settlements already exist at {output_path}")
            return gpd.read_file(output_path)

        print(f"Fetching settlements for {state_name} from OpenStreetMap...")

        try:
            # Get the geometry in WGS84 for OSMnx
            boundary_wgs84 = boundary.to_crs('EPSG:4326')
            polygon = boundary_wgs84.geometry.iloc[0]

            # Fetch places (settlements)
            tags = {'place': ['city', 'town', 'village', 'hamlet']}
            settlements = ox.features_from_polygon(polygon, tags=tags)

            # Keep only point geometries
            settlements = settlements[settlements.geometry.type ==
                                      'Point'].copy()

            print(f"Downloaded {len(settlements)} settlements")

            # Save to file
            settlements.to_file(output_path, driver='GeoJSON')
            print(f"Saved settlements to {output_path}")

            return settlements

        except Exception as e:
            print(f"Error fetching settlements: {e}")
            print("Continuing without settlements...")
            return gpd.GeoDataFrame()

    def fetch_dem(self, boundary: Optional[gpd.GeoDataFrame] = None) -> str:
        """
        Fetch Digital Elevation Model from USGS 3DEP.
        
        Uses the National Map API to download 1/3 arc-second (~10m) elevation data.
        
        Args:
            boundary: GeoDataFrame with boundary polygon. If None, fetches it first.
            
        Returns:
            Path to merged DEM file
        """
        if boundary is None:
            boundary = self.fetch_state_boundary()

        state_name = self.config.state_name
        output_path = self.config.get_path(
            'raw_data') / f"{state_name.lower()}_dem.tif"

        # Check if already exists
        if output_path.exists():
            print(f"DEM already exists at {output_path}")
            return str(output_path)

        print(f"Fetching DEM for {state_name} from USGS 3DEP...")
        print(
            "This may take several minutes and require significant bandwidth..."
        )

        try:
            # Get boundary in WGS84
            boundary_wgs84 = boundary.to_crs('EPSG:4326')
            bounds = boundary_wgs84.total_bounds  # minx, miny, maxx, maxy

            # Use The National Map API
            # https://apps.nationalmap.gov/tnmaccess/#/
            base_url = "https://tnmaccess.nationalmap.gov/api/v1/products"

            params = {
                'datasets': 'National Elevation Dataset (NED) 1/3 arc-second',
                'bbox': f"{bounds[0]},{bounds[1]},{bounds[2]},{bounds[3]}",
                'prodFormats': 'GeoTIFF',
                'max': 100  # Maximum number of tiles
            }

            print(f"Querying National Map API for DEM tiles...")
            response = requests.get(base_url, params=params)
            response.raise_for_status()

            results = response.json()
            items = results.get('items', [])

            if not items:
                print("No DEM tiles found. Trying alternative dataset...")
                # Try 1 arc-second data as fallback
                params[
                    'datasets'] = 'National Elevation Dataset (NED) 1 arc-second'
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                results = response.json()
                items = results.get('items', [])

                if not items:
                    raise ValueError("No DEM data available for this region")

            print(f"Found {len(items)} DEM tiles to download")

            # Use project's data directory for temp files (not system /tmp which may be small)
            temp_dir = self.config.get_path('raw_data') / 'temp_dem'
            temp_dir.mkdir(exist_ok=True)

            # Process in batches to avoid filling disk
            batch_size = 20  # Process 20 tiles at a time
            all_tiles = []

            try:
                for batch_start in range(0, len(items), batch_size):
                    batch_end = min(batch_start + batch_size, len(items))
                    batch_items = items[batch_start:batch_end]

                    print(
                        f"\nProcessing batch {batch_start//batch_size + 1} (tiles {batch_start+1}-{batch_end})..."
                    )
                    tile_paths = []

                    # Download batch
                    for i, item in enumerate(batch_items):
                        download_url = item.get('downloadURL')
                        if not download_url:
                            continue

                        tile_num = batch_start + i + 1
                        print(f"  Downloading tile {tile_num}/{len(items)}...")

                        # Download file
                        tile_response = requests.get(download_url, stream=True)
                        tile_response.raise_for_status()

                        # Save to temp file
                        tile_path = temp_dir / f"tile_{tile_num}.tif"

                        with open(tile_path, 'wb') as f:
                            for chunk in tile_response.iter_content(
                                    chunk_size=8192):
                                f.write(chunk)

                        tile_paths.append(tile_path)

                    all_tiles.extend(tile_paths)
                    print(
                        f"  Batch {batch_start//batch_size + 1} downloaded ({len(tile_paths)} tiles)"
                    )

                # Merge all tiles
                print(f"\nMerging {len(all_tiles)} tiles...")
                src_files = [rasterio.open(str(p)) for p in all_tiles]

                mosaic, out_trans = merge(src_files)

                # Close source files
                for src in src_files:
                    src.close()

                # Get profile from first tile
                with rasterio.open(all_tiles[0]) as src:
                    out_meta = src.profile.copy()

                # Update profile for merged raster
                out_meta.update({
                    "driver": "GTiff",
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": out_trans,
                    "compress": "lzw"
                })

                # Clip to boundary and save
                print("Clipping DEM to state boundary...")
                boundary_proj = boundary.to_crs(out_meta['crs'])

                with rasterio.MemoryFile() as memfile:
                    with memfile.open(**out_meta) as mem_dataset:
                        mem_dataset.write(mosaic)

                    with memfile.open() as mem_dataset:
                        clipped, clip_trans = mask(mem_dataset,
                                                   boundary_proj.geometry,
                                                   crop=True,
                                                   all_touched=True)

                        clip_meta = mem_dataset.profile.copy()
                        clip_meta.update({
                            "height": clipped.shape[1],
                            "width": clipped.shape[2],
                            "transform": clip_trans
                        })

                # Save clipped raster
                with rasterio.open(output_path, 'w', **clip_meta) as dst:
                    dst.write(clipped)

                print(f"Saved DEM to {output_path}")

            finally:
                # Clean up temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    print("Cleaned up temporary files")

            return str(output_path)

        except Exception as e:
            print(f"Error fetching DEM: {e}")
            print("\nDEM download failed. Manual download instructions:")
            print("1. Visit: https://apps.nationalmap.gov/downloader/")
            print("2. Select 'Elevation Products (3DEP)'")
            print(f"3. Draw a box around {state_name} or use state boundary")
            print("4. Download 1/3 arc-second DEM (or 1 arc-second)")
            print(f"5. Save as: {output_path}")
            print("\nThen run the pipeline again.")
            raise

    def fetch_landcover(self,
                        boundary: Optional[gpd.GeoDataFrame] = None) -> str:
        """
        Fetch land cover data from NLCD (National Land Cover Database).
        
        Downloads NLCD 2021 30m resolution land cover.
        
        Args:
            boundary: GeoDataFrame with boundary polygon. If None, fetches it first.
            
        Returns:
            Path to clipped land cover file
        """
        if boundary is None:
            boundary = self.fetch_state_boundary()

        state_name = self.config.state_name
        output_path = self.config.get_path(
            'raw_data') / f"{state_name.lower()}_landcover.tif"

        # Check if already exists
        if output_path.exists():
            print(f"Land cover already exists at {output_path}")
            return str(output_path)

        print(f"Fetching land cover for {state_name} from NLCD...")
        print("This will download ~1-2GB of data and may take some time...")

        try:
            # NLCD 2021 CONUS land cover
            # Note: Direct download URLs may change. Check https://www.mrlc.gov/data

            # Try multiple possible URLs
            possible_urls = [
                "https://s3-us-west-2.amazonaws.com/mrlc/nlcd_2021_land_cover_l48_20230630.zip",
                "https://s3.us-west-2.amazonaws.com/mrlc/nlcd_2021_land_cover_l48_20230630.zip",
                "https://mrlc.s3.us-west-2.amazonaws.com/nlcd_2021_land_cover_l48_20230630.zip",
            ]

            url = None
            for test_url in possible_urls:
                try:
                    print(f"Trying URL: {test_url}")
                    test_response = requests.head(test_url, timeout=10)
                    if test_response.status_code == 200:
                        url = test_url
                        print("  ✓ URL accessible")
                        break
                    else:
                        print(f"  ✗ Got status {test_response.status_code}")
                except Exception as e:
                    print(f"  ✗ Failed: {e}")

            if not url:
                print("\nAutomatic download not available.")
                print("Please download NLCD 2021 data manually:")
                print("1. Visit: https://www.mrlc.gov/data")
                print("2. Click 'NLCD 2021 Land Cover (CONUS)'")
                print("3. Download the GeoTIFF (CONUS)")
                print("4. Extract and clip to state boundary using:")
                print(
                    f"   gdalwarp -cutline <boundary_file> -crop_to_cutline \\"
                )
                print(
                    f"            nlcd_2021_land_cover_l48.tif {output_path}")
                print(f"\nOr place the full CONUS file at: {output_path}")
                raise ValueError("No working download URL found for NLCD data")

            # Use project's data directory for temp files
            temp_dir = self.config.get_path('raw_data') / 'temp_landcover'
            temp_dir.mkdir(exist_ok=True)
            zip_path = temp_dir / "nlcd_2021.zip"

            try:
                print("Downloading NLCD 2021 data...")
                print("(This is a large file and may take 10-30 minutes)")

                response = requests.get(url, stream=True)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                with open(zip_path, 'wb') as f:
                    with tqdm(total=total_size, unit='B',
                              unit_scale=True) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            pbar.update(len(chunk))

                print("Extracting archive...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # Find the .tif file in extracted files
                tif_files = list(Path(temp_dir).glob("**/*.tif"))

                if not tif_files:
                    raise FileNotFoundError(
                        "No .tif file found in NLCD archive")

                nlcd_path = tif_files[0]
                print(f"Found land cover file: {nlcd_path.name}")

                # Clip to boundary
                print("Clipping land cover to state boundary...")

                with rasterio.open(nlcd_path) as src:
                    # Reproject boundary to match raster CRS
                    boundary_proj = boundary.to_crs(src.crs)

                    # Clip
                    clipped, clip_trans = mask(src,
                                               boundary_proj.geometry,
                                               crop=True,
                                               all_touched=True)

                    # Update metadata
                    clip_meta = src.profile.copy()
                    clip_meta.update({
                        "height": clipped.shape[1],
                        "width": clipped.shape[2],
                        "transform": clip_trans,
                        "compress": "lzw"
                    })

                    # Save
                    with rasterio.open(output_path, 'w', **clip_meta) as dst:
                        dst.write(clipped)

                print(f"Saved land cover to {output_path}")

            finally:
                # Clean up temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    print("Cleaned up temporary files")

            return str(output_path)

        except Exception as e:
            print(f"Error fetching land cover: {e}")
            print(
                "\nLand cover download failed. Manual download instructions:")
            print("1. Visit: https://www.mrlc.gov/data")
            print("2. Select 'NLCD 2021 Land Cover (CONUS)'")
            print("3. Download the full CONUS GeoTIFF")
            print(
                "4. Clip to state boundary (optional) or place full file at:")
            print(f"   {output_path}")
            print("\nThen run the pipeline again.")
            raise

    def fetch_all(self) -> dict:
        """
        Fetch all required data.
        
        Returns:
            Dictionary with 'boundary', 'roads', and optionally 'settlements', 'dem', 'landcover'
        """
        print("=" * 60)
        print("FETCHING ALL DATA")
        print("=" * 60)

        # Fetch boundary
        boundary = self.fetch_state_boundary()

        # Fetch roads
        roads = self.fetch_roads(boundary)

        # Optionally fetch settlements
        data = {'boundary': boundary, 'roads': roads}

        if self.config.get('data.include_settlements', False):
            settlements = self.fetch_settlements(boundary)
            if len(settlements) > 0:
                data['settlements'] = settlements

        # Fetch DEM and land cover if cost-distance is enabled
        if self.config.get('cost_distance.enabled', False):
            print("\nCost-distance mode enabled. Fetching terrain data...")

            try:
                dem_path = self.fetch_dem(boundary)
                data['dem'] = dem_path
            except Exception as e:
                print(f"Warning: Could not fetch DEM: {e}")

            try:
                landcover_path = self.fetch_landcover(boundary)
                data['landcover'] = landcover_path
            except Exception as e:
                print(f"Warning: Could not fetch land cover: {e}")

        print("=" * 60)
        print("DATA FETCH COMPLETE")
        print("=" * 60)

        return data


def main():
    """Main function for testing data fetching."""
    fetcher = DataFetcher()
    data = fetcher.fetch_all()

    print("\nFetched data summary:")
    for key, gdf in data.items():
        print(f"  {key}: {len(gdf)} features")


if __name__ == '__main__':
    main()
