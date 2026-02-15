"""
Preprocessing module for geospatial data.

This module handles:
- Reprojection to distance-preserving CRS
- Clipping roads to state boundary
- Rasterization of vector data
"""
from pathlib import Path
from typing import Optional, Tuple

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds

from .config import get_config


class DataPreprocessor:
    """Handles preprocessing of geospatial data."""

    def __init__(self, config=None):
        """
        Initialize DataPreprocessor.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()
        self.config.ensure_directories()

    def reproject_data(self,
                       gdf: gpd.GeoDataFrame,
                       target_crs: Optional[str] = None) -> gpd.GeoDataFrame:
        """
        Reproject GeoDataFrame to target CRS.
        
        Args:
            gdf: Input GeoDataFrame
            target_crs: Target CRS. If None, uses config value.
            
        Returns:
            Reprojected GeoDataFrame
        """
        target_crs = target_crs or self.config.crs

        if gdf.crs is None:
            print("Warning: Input data has no CRS, assuming EPSG:4326")
            gdf = gdf.set_crs('EPSG:4326')

        if gdf.crs.to_string() == target_crs:
            return gdf

        print(f"Reprojecting from {gdf.crs} to {target_crs}")
        return gdf.to_crs(target_crs)

    def clip_to_boundary(self, roads: gpd.GeoDataFrame,
                         boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Clip roads to state boundary.
        
        Args:
            roads: GeoDataFrame with roads
            boundary: GeoDataFrame with boundary polygon
            
        Returns:
            Clipped roads GeoDataFrame
        """
        print("Clipping roads to boundary...")

        # Ensure same CRS
        if roads.crs != boundary.crs:
            boundary = boundary.to_crs(roads.crs)

        # Clip
        clipped = gpd.clip(roads, boundary)

        print(
            f"Clipped {len(roads)} roads to {len(clipped)} road segments within boundary"
        )

        return clipped

    def create_raster_grid(
            self,
            boundary: gpd.GeoDataFrame,
            resolution: Optional[int] = None) -> Tuple[np.ndarray, dict]:
        """
        Create an empty raster grid based on boundary extent.
        
        Args:
            boundary: GeoDataFrame with boundary polygon
            resolution: Pixel resolution in meters. If None, uses config value.
            
        Returns:
            Tuple of (array, metadata dict with transform, width, height, crs)
        """
        resolution = resolution or self.config.resolution

        # Get bounds
        minx, miny, maxx, maxy = boundary.total_bounds

        # Calculate grid dimensions
        width = int(np.ceil((maxx - minx) / resolution))
        height = int(np.ceil((maxy - miny) / resolution))

        # Create transform
        transform = from_bounds(minx, miny, maxx, maxy, width, height)

        # Create empty array
        array = np.zeros((height, width), dtype=np.uint8)

        metadata = {
            'transform': transform,
            'width': width,
            'height': height,
            'crs': boundary.crs,
            'bounds': (minx, miny, maxx, maxy)
        }

        print(
            f"Created raster grid: {width}x{height} pixels at {resolution}m resolution"
        )

        return array, metadata

    def rasterize_roads(self, roads: gpd.GeoDataFrame,
                        raster_shape: Tuple[int,
                                            int], transform) -> np.ndarray:
        """
        Rasterize road vectors to a binary mask.
        
        Uses chunked processing to handle large road networks without exhausting memory.
        
        Args:
            roads: GeoDataFrame with roads
            raster_shape: Shape of output raster (height, width)
            transform: Affine transform for raster
            
        Returns:
            Binary mask array where 1 = road, 0 = no road
        """
        print(f"Rasterizing {len(roads)} road segments...")

        # Create output array
        road_mask = np.zeros(raster_shape, dtype=np.uint8)

        # Process in chunks to avoid memory issues with large datasets
        # Use smaller chunks for very large datasets
        if len(roads) > 500_000:
            chunk_size = 10000  # Small chunks for huge datasets
        elif len(roads) > 100_000:
            chunk_size = 25000  # Medium chunks
        else:
            chunk_size = 50000  # Default

        n_chunks = int(np.ceil(len(roads) / chunk_size))

        if n_chunks > 1:
            print(
                f"  Processing in {n_chunks} chunks ({chunk_size:,} roads per chunk)"
            )

        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(roads))
            chunk = roads.iloc[start_idx:end_idx]

            if n_chunks > 1:
                print(f"  Chunk {i+1}/{n_chunks}: {len(chunk):,} roads")

            # Create shapes for this chunk
            shapes = [(geom, 1) for geom in chunk.geometry if geom is not None]

            # Rasterize chunk and combine with existing mask
            chunk_mask = rasterize(
                shapes=shapes,
                out_shape=raster_shape,
                transform=transform,
                fill=0,
                dtype=np.uint8,
                all_touched=True  # Include pixels touched by roads
            )

            # Combine with existing mask (OR operation)
            road_mask = np.maximum(road_mask, chunk_mask)

        road_pixels = np.sum(road_mask)
        total_pixels = road_mask.size
        coverage = (road_pixels / total_pixels) * 100

        print(f"Rasterized: {road_pixels:,} pixels ({coverage:.2f}% coverage)")

        return road_mask

    def save_raster(self, array: np.ndarray, metadata: dict,
                    output_path: Path):
        """
        Save raster array to GeoTIFF file.
        
        Args:
            array: Numpy array
            metadata: Dictionary with raster metadata (transform, crs, etc.)
            output_path: Path to save file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Determine number of bands and data type
        if array.ndim == 2:
            count = 1
            array = array[np.newaxis, :, :]  # Add band dimension
        else:
            count = array.shape[0]

        with rasterio.open(output_path,
                           'w',
                           driver='GTiff',
                           height=metadata['height'],
                           width=metadata['width'],
                           count=count,
                           dtype=array.dtype,
                           crs=metadata['crs'],
                           transform=metadata['transform'],
                           compress='lzw') as dst:
            dst.write(array)

        print(f"Saved raster to {output_path}")

    def preprocess_all(self, data: dict) -> dict:
        """
        Run full preprocessing pipeline.
        
        Args:
            data: Dictionary with 'boundary' and 'roads' GeoDataFrames
            
        Returns:
            Dictionary with processed data and rasters
        """
        print("=" * 60)
        print("PREPROCESSING DATA")
        print("=" * 60)

        # Reproject boundary
        print("\n1. Reprojecting boundary...")
        boundary = self.reproject_data(data['boundary'])

        # Reproject roads
        print("\n2. Reprojecting roads...")
        roads = self.reproject_data(data['roads'])

        # Clip roads to boundary
        print("\n3. Clipping roads...")
        roads_clipped = self.clip_to_boundary(roads, boundary)

        # Create raster grid
        print("\n4. Creating raster grid...")
        road_mask, metadata = self.create_raster_grid(boundary)

        # Rasterize roads
        print("\n5. Rasterizing roads...")
        road_mask = self.rasterize_roads(
            roads_clipped, (metadata['height'], metadata['width']),
            metadata['transform'])

        # Save intermediate results if configured
        if self.config.get('output.save_intermediate', True):
            print("\n6. Saving intermediate results...")

            # Save processed vectors
            processed_dir = self.config.get_path('processed_data')
            state_name = self.config.state_name.lower()
            state_folder = processed_dir / state_name
            state_folder.mkdir(parents=True, exist_ok=True)

            boundary.to_file(state_folder / "boundary_projected.geojson")
            roads_clipped.to_file(state_folder / "roads_clipped.geojson")

            # Save road mask raster
            self.save_raster(road_mask, metadata,
                             state_folder / "road_mask.tif")

        print("=" * 60)
        print("PREPROCESSING COMPLETE")
        print("=" * 60)

        return {
            'boundary': boundary,
            'roads': roads_clipped,
            'road_mask': road_mask,
            'raster_metadata': metadata
        }


def main():
    """Main function for testing preprocessing."""
    from .fetch import DataFetcher

    # Fetch data
    fetcher = DataFetcher()
    data = fetcher.fetch_all()

    # Preprocess
    preprocessor = DataPreprocessor()
    processed = preprocessor.preprocess_all(data)

    print("\nProcessed data summary:")
    print(f"  Boundary: {len(processed['boundary'])} features")
    print(f"  Roads: {len(processed['roads'])} features")
    print(f"  Road mask shape: {processed['road_mask'].shape}")


if __name__ == '__main__':
    main()
