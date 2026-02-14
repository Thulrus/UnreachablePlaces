"""
Distance computation module.

This module computes distance fields from rasterized features.
Supports both Euclidean distance and cost-weighted distance transforms.
"""
import numpy as np
from scipy.ndimage import distance_transform_edt
import rasterio
from pathlib import Path
from typing import Tuple, Optional
import logging

from .config import get_config

logger = logging.getLogger(__name__)


class DistanceCalculator:
    """Handles distance field calculations."""
    
    def __init__(self, config=None):
        """
        Initialize DistanceCalculator.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()
        
    def compute_distance_field(self, mask: np.ndarray, 
                               resolution: Optional[int] = None) -> np.ndarray:
        """
        Compute Euclidean distance transform from binary mask.
        
        The mask should have 1 for features (roads) and 0 for background.
        The output will be distance in meters from any feature.
        
        Args:
            mask: Binary mask array (1 = feature, 0 = background)
            resolution: Pixel resolution in meters. If None, uses config value.
            
        Returns:
            Distance field array where each pixel contains distance to nearest feature
        """
        resolution = resolution or self.config.resolution
        
        print(f"Computing distance field...")
        print(f"  Input shape: {mask.shape}")
        print(f"  Resolution: {resolution}m per pixel")
        
        # Invert mask: distance_transform_edt computes distance from 0 pixels
        # We want distance from 1 pixels (roads), so invert
        inverted_mask = (mask == 0).astype(np.uint8)
        
        # Compute distance in pixels
        distance_pixels = distance_transform_edt(inverted_mask)
        
        # Convert to meters
        distance_meters = distance_pixels * resolution
        
        # Statistics
        max_distance = np.max(distance_meters)
        mean_distance = np.mean(distance_meters)
        
        print(f"  Max distance: {max_distance:.2f} m ({max_distance/1000:.2f} km)")
        print(f"  Mean distance: {mean_distance:.2f} m ({mean_distance/1000:.2f} km)")
        
        return distance_meters
    
    def compute_cost_distance_field(self, mask: np.ndarray, cost_surface: np.ndarray,
                                   resolution: Optional[int] = None) -> np.ndarray:
        """
        Compute cost-weighted distance transform from binary mask.
        
        Uses MCP (Minimum Cost Path) algorithm to compute least-cost distances
        that account for terrain difficulty.
        
        Args:
            mask: Binary mask array (1 = feature/road, 0 = background)
            cost_surface: Cost surface array (relative traversal costs)
            resolution: Pixel resolution in meters. If None, uses config value.
            
        Returns:
            Cost-distance field array where each pixel contains cost-distance to nearest feature
        """
        try:
            from skimage.graph import MCP
        except ImportError:
            raise ImportError(
                "scikit-image is required for cost-distance calculations. "
                "Install with: pip install scikit-image"
            )
        
        resolution = resolution or self.config.resolution
        
        print(f"Computing cost-distance field...")
        print(f"  Input shape: {mask.shape}")
        print(f"  Cost surface range: {cost_surface.min():.2f} to {cost_surface.max():.2f}")
        print(f"  Resolution: {resolution}m per pixel")
        print("  (This may take several minutes...)")
        
        # Find all road pixels as starting points
        road_pixels = np.argwhere(mask == 1)
        
        if len(road_pixels) == 0:
            raise ValueError("No road pixels found in mask")
        
        print(f"  Computing from {len(road_pixels):,} road pixels")
        
        # Create MCP object with cost surface
        # MCP expects costs as accumulated_cost = sum(costs along path)
        # We multiply base distance by cost factors
        mcp = MCP(cost_surface, fully_connected=True)
        
        # Compute cumulative cost from all road pixels
        # This gives us the minimum cost to reach any pixel from nearest road
        cumulative_costs, _ = mcp.find_costs(road_pixels)
        
        # Convert cost units to approximate distance units
        # The cumulative cost is in "cost units" which roughly correspond to
        # distance × terrain_difficulty_factor
        # For display purposes, we scale by resolution to get "effective distance"
        distance_meters = cumulative_costs * resolution
        
        # Statistics
        max_distance = np.max(distance_meters[np.isfinite(distance_meters)])
        mean_distance = np.mean(distance_meters[np.isfinite(distance_meters)])
        
        print(f"  Max cost-distance: {max_distance:.2f} m ({max_distance/1000:.2f} km)")
        print(f"  Mean cost-distance: {mean_distance:.2f} m ({mean_distance/1000:.2f} km)")
        print(f"  Note: Cost-distance is 'effective distance' accounting for terrain")
        
        return distance_meters
    
    def mask_by_boundary(self, distance_field: np.ndarray,
                        boundary_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Mask distance field to only include areas within boundary.
        
        Args:
            distance_field: Distance field array
            boundary_mask: Optional mask array (1 = inside, 0 = outside)
                          If None, assumes entire array is valid
            
        Returns:
            Masked distance field with NaN outside boundary
        """
        if boundary_mask is None:
            return distance_field
        
        print("Masking distance field to boundary...")
        
        # Create masked array
        masked_field = distance_field.copy().astype(np.float32)
        masked_field[boundary_mask == 0] = np.nan
        
        # Count valid pixels
        valid_pixels = np.sum(~np.isnan(masked_field))
        total_pixels = masked_field.size
        
        print(f"  Valid pixels: {valid_pixels:,} ({valid_pixels/total_pixels*100:.1f}%)")
        
        return masked_field
    
    def create_boundary_mask(self, boundary_gdf, raster_shape: Tuple[int, int],
                            transform) -> np.ndarray:
        """
        Create a binary mask from boundary polygon.
        
        Args:
            boundary_gdf: GeoDataFrame with boundary polygon
            raster_shape: Shape of raster (height, width)
            transform: Affine transform
            
        Returns:
            Binary mask (1 = inside boundary, 0 = outside)
        """
        from rasterio.features import rasterize
        
        print("Creating boundary mask...")
        
        # Rasterize boundary
        shapes = [(geom, 1) for geom in boundary_gdf.geometry]
        
        boundary_mask = rasterize(
            shapes=shapes,
            out_shape=raster_shape,
            transform=transform,
            fill=0,
            dtype=np.uint8,
            all_touched=False
        )
        
        return boundary_mask
    
    def save_distance_raster(self, distance_field: np.ndarray, 
                            metadata: dict,
                            output_path: Path):
        """
        Save distance field to GeoTIFF.
        
        Args:
            distance_field: Distance field array
            metadata: Raster metadata dictionary
            output_path: Path to save file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Saving distance raster to {output_path}")
        
        # Ensure 3D array
        if distance_field.ndim == 2:
            distance_field = distance_field[np.newaxis, :, :]
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=metadata['height'],
            width=metadata['width'],
            count=1,
            dtype=np.float32,
            crs=metadata['crs'],
            transform=metadata['transform'],
            compress='lzw',
            nodata=np.nan
        ) as dst:
            dst.write(distance_field.astype(np.float32))
        
        print(f"Saved distance raster")
    
    def compute_all(self, processed_data: dict) -> dict:
        """
        Run full distance computation pipeline.
        
        Automatically selects Euclidean or cost-distance mode based on configuration.
        
        Args:
            processed_data: Dictionary with processed data from preprocessing
            
        Returns:
            Dictionary with distance field and metadata
        """
        print("=" * 60)
        print("COMPUTING DISTANCE FIELD")
        print("=" * 60)
        
        road_mask = processed_data['road_mask']
        metadata = processed_data['raster_metadata']
        boundary = processed_data['boundary']
        
        # Check if cost-distance is enabled
        use_cost_distance = self.config.get('cost_distance.enabled', False)
        
        if use_cost_distance:
            print("\nMode: COST-DISTANCE (terrain-aware)")
            print("Loading cost surface...")
            
            # Load cost surface
            state_name = self.config.state_name.lower()
            processed_path = self.config.get_path('processed_data')
            cost_surface_path = processed_path / f"{state_name}_cost_surface.tif"
            
            if not cost_surface_path.exists():
                print(f"Warning: Cost surface not found at {cost_surface_path}")
                print("Falling back to Euclidean distance...")
                print("Run 'cost-surface' command first to enable cost-distance mode.")
                use_cost_distance = False
            else:
                with rasterio.open(cost_surface_path) as src:
                    cost_surface = src.read(1)
                print(f"  Cost surface loaded: {cost_surface.shape}")
        
        # Compute distance field
        if use_cost_distance:
            print("\n1. Computing cost-weighted distance transform...")
            distance_field = self.compute_cost_distance_field(road_mask, cost_surface)
        else:
            print("\nMode: EUCLIDEAN (straight-line distance)")
            print("\n1. Computing Euclidean distance transform...")
            distance_field = self.compute_distance_field(road_mask)
        
        # Create boundary mask
        print("\n2. Creating boundary mask...")
        boundary_mask = self.create_boundary_mask(
            boundary,
            (metadata['height'], metadata['width']),
            metadata['transform']
        )
        
        # Mask distance field
        print("\n3. Masking to boundary...")
        distance_masked = self.mask_by_boundary(distance_field, boundary_mask)
        
        # Save if configured
        if self.config.get('output.save_intermediate', True):
            print("\n4. Saving distance raster...")
            state_name = self.config.state_name.lower()
            
            # Use different filename for cost-distance vs euclidean
            if use_cost_distance:
                output_filename = f"{state_name}_distance_cost.tif"
            else:
                output_filename = f"{state_name}_distance.tif"
            
            output_path = self.config.get_path('processed_data') / output_filename
            self.save_distance_raster(distance_masked, metadata, output_path)
        
        print("=" * 60)
        print("DISTANCE COMPUTATION COMPLETE")
        print("=" * 60)
        
        return {
            'distance_field': distance_masked,
            'boundary_mask': boundary_mask,
            'metadata': metadata,
            'mode': 'cost-distance' if use_cost_distance else 'euclidean'
        }


def main():
    """Main function for testing distance computation."""
    from .fetch import DataFetcher
    from .preprocess import DataPreprocessor
    
    # Fetch and preprocess data
    fetcher = DataFetcher()
    data = fetcher.fetch_all()
    
    preprocessor = DataPreprocessor()
    processed = preprocessor.preprocess_all(data)
    
    # Compute distance
    calculator = DistanceCalculator()
    result = calculator.compute_all(processed)
    
    print(f"\nDistance field shape: {result['distance_field'].shape}")
    print(f"Max distance: {np.nanmax(result['distance_field']):.2f} m")


if __name__ == '__main__':
    main()
