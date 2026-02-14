"""
cost_surface.py

Generates cost surfaces for terrain-aware distance calculations.
Combines slope and land cover factors to create composite cost rasters.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import rasterio
import yaml
from rasterio.warp import Resampling, reproject
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)

# National Land Cover Database 2021 classification
# Source: https://www.mrlc.gov/data/legends/national-land-cover-database-class-legend-and-description
LANDCOVER_COSTS = {
    11: 10.0,  # Open Water - very difficult to traverse
    12: 8.0,  # Perennial Ice/Snow - extremely difficult
    21: 1.1,  # Developed, Open Space - slightly harder than open ground
    22: 1.3,  # Developed, Low Intensity - some obstacles
    23: 1.5,  # Developed, Medium Intensity - more obstacles
    24: 2.0,  # Developed, High Intensity - urban obstacles
    31: 1.2,  # Barren Land - rocky but passable
    41: 2.0,  # Deciduous Forest - moderate difficulty
    42: 2.2,  # Evergreen Forest - slightly denser
    43: 2.1,  # Mixed Forest - between deciduous and evergreen
    52: 1.5,  # Shrub/Scrub - some bushwhacking
    71: 1.2,  # Grassland/Herbaceous - relatively easy
    81: 1.1,  # Pasture/Hay - very easy, maintained
    82: 1.3,  # Cultivated Crops - some obstacles
    90: 3.0,  # Woody Wetlands - difficult terrain
    95: 4.0,  # Emergent Herbaceous Wetlands - very difficult
}


def slope_cost_factor(slope_degrees: np.ndarray, config: dict) -> np.ndarray:
    """
    Calculate cost multipliers based on slope.
    
    Uses piecewise linear interpolation between configured thresholds:
    - 0°: 1.0x (no penalty)
    - 15°: 2.0x (moderate difficulty)
    - 30°: 4.0x (steep)
    - 45°+: 10.0x (very steep)
    
    Args:
        slope_degrees: Array of slope values in degrees
        config: Configuration dictionary with slope thresholds
        
    Returns:
        Array of cost multipliers (same shape as slope_degrees)
    """
    slope_config = config.get('cost_distance', {}).get('slope', {})

    # Get thresholds and costs
    flat_cost = slope_config.get('flat', 1.0)
    moderate_cost = slope_config.get('moderate', 2.0)
    steep_cost = slope_config.get('steep', 4.0)
    very_steep_cost = slope_config.get('very_steep', 10.0)

    # Initialize with flat cost
    cost = np.full_like(slope_degrees, flat_cost, dtype=np.float32)

    # Apply piecewise linear interpolation
    # 0° to 15°
    mask = (slope_degrees > 0) & (slope_degrees <= 15)
    cost[mask] = flat_cost + (moderate_cost -
                              flat_cost) * (slope_degrees[mask] / 15.0)

    # 15° to 30°
    mask = (slope_degrees > 15) & (slope_degrees <= 30)
    cost[mask] = moderate_cost + (steep_cost - moderate_cost) * (
        (slope_degrees[mask] - 15) / 15.0)

    # 30° to 45°
    mask = (slope_degrees > 30) & (slope_degrees <= 45)
    cost[mask] = steep_cost + (very_steep_cost - steep_cost) * (
        (slope_degrees[mask] - 30) / 15.0)

    # 45°+
    mask = slope_degrees > 45
    cost[mask] = very_steep_cost

    return cost


def landcover_cost_factor(landcover: np.ndarray) -> np.ndarray:
    """
    Calculate cost multipliers based on land cover type.
    
    Args:
        landcover: Array of NLCD land cover codes
        
    Returns:
        Array of cost multipliers (same shape as landcover)
    """
    # Default cost for unknown land cover types
    cost = np.ones_like(landcover, dtype=np.float32)

    # Apply costs from lookup table
    for lc_code, lc_cost in LANDCOVER_COSTS.items():
        mask = (landcover == lc_code)
        cost[mask] = lc_cost

    return cost


class CostSurfaceGenerator:
    """
    Generates composite cost surfaces from DEM and land cover data.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the cost surface generator.
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.project_dir = Path(__file__).parent.parent
        self.processed_dir = self.project_dir / self.config['paths'][
            'processed_data']

        # Get cost distance configuration
        self.cost_config = self.config.get('cost_distance', {})
        self.resolution = self.cost_config.get('resolution_m', 250)

        # Get factor weights
        factors = self.cost_config.get('factors', {})
        self.slope_weight = factors.get('slope_weight', 1.0)
        self.landcover_weight = factors.get('landcover_weight', 1.0)

    def calculate_slope(self,
                        dem_path: str,
                        output_path: Optional[str] = None) -> np.ndarray:
        """
        Calculate slope in degrees from a DEM.
        
        Args:
            dem_path: Path to DEM raster file
            output_path: Optional path to save slope raster
            
        Returns:
            Slope array in degrees
        """
        logger.info(f"Calculating slope from {dem_path}")

        with rasterio.open(dem_path) as src:
            dem = src.read(1, masked=True)
            transform = src.transform
            profile = src.profile

            # Calculate gradients (rise/run)
            # Note: transform.a and transform.e give pixel size in map units
            dx = np.abs(transform.a)  # pixel width
            dy = np.abs(transform.e)  # pixel height

            # Sobel filters for gradient estimation
            grad_x = np.gradient(dem, dx, axis=1)
            grad_y = np.gradient(dem, dy, axis=0)

            # Calculate slope magnitude
            slope_radians = np.arctan(np.sqrt(grad_x**2 + grad_y**2))
            slope_degrees = np.degrees(slope_radians)

            # Apply light smoothing to reduce noise
            slope_degrees = gaussian_filter(slope_degrees, sigma=1.0)

            # Save if requested
            if output_path:
                profile.update(dtype=rasterio.float32, count=1, nodata=-9999)
                with rasterio.open(output_path, 'w', **profile) as dst:
                    dst.write(slope_degrees.astype(np.float32), 1)
                logger.info(f"Saved slope raster to {output_path}")

        logger.info(
            f"Slope range: {slope_degrees.min():.1f}° to {slope_degrees.max():.1f}°"
        )
        return slope_degrees

    def resample_landcover(self,
                           landcover_path: str,
                           template_path: str,
                           output_path: Optional[str] = None) -> np.ndarray:
        """
        Resample land cover to match template raster resolution and extent.
        
        Args:
            landcover_path: Path to land cover raster
            template_path: Path to template raster (defines output grid)
            output_path: Optional path to save resampled land cover
            
        Returns:
            Resampled land cover array
        """
        logger.info(f"Resampling land cover from {landcover_path}")

        # Read template to get target grid
        with rasterio.open(template_path) as template:
            template_profile = template.profile
            template_transform = template.transform
            template_shape = (template.height, template.width)

        # Read and resample land cover
        with rasterio.open(landcover_path) as src:
            # Create output array
            landcover = np.zeros(template_shape, dtype=src.dtypes[0])

            # Reproject to match template
            reproject(
                source=rasterio.band(src, 1),
                destination=landcover,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=template_transform,
                dst_crs=template_profile['crs'],
                resampling=Resampling.
                nearest  # Use nearest for categorical data
            )

        # Save if requested
        if output_path:
            template_profile.update(dtype=landcover.dtype, count=1)
            with rasterio.open(output_path, 'w', **template_profile) as dst:
                dst.write(landcover, 1)
            logger.info(f"Saved resampled land cover to {output_path}")

        unique_codes = np.unique(landcover)
        logger.info(f"Land cover codes present: {len(unique_codes)}")
        return landcover

    def generate_cost_surface(
            self,
            dem_path: str,
            landcover_path: str,
            output_path: Optional[str] = None) -> Tuple[np.ndarray, dict]:
        """
        Generate composite cost surface from DEM and land cover.
        
        Args:
            dem_path: Path to DEM raster
            landcover_path: Path to land cover raster
            output_path: Optional path to save cost surface
            
        Returns:
            Tuple of (cost_surface array, profile dict)
        """
        logger.info("Generating composite cost surface")

        # Calculate slope
        slope_degrees = self.calculate_slope(dem_path)
        slope_costs = slope_cost_factor(slope_degrees, self.config)

        # Resample land cover
        landcover = self.resample_landcover(landcover_path, dem_path)
        landcover_costs = landcover_cost_factor(landcover)

        # Combine costs with weights
        # Cost = slope_cost^slope_weight * landcover_cost^landcover_weight
        cost_surface = (slope_costs**self.slope_weight) * (
            landcover_costs**self.landcover_weight)

        # Ensure minimum cost of 1.0
        cost_surface = np.maximum(cost_surface, 1.0)

        logger.info(
            f"Cost surface range: {cost_surface.min():.2f} to {cost_surface.max():.2f}"
        )
        logger.info(f"Cost surface mean: {cost_surface.mean():.2f}")

        # Get profile from DEM
        with rasterio.open(dem_path) as src:
            profile = src.profile
            profile.update(dtype=rasterio.float32, count=1, nodata=-9999)

        # Save if requested
        if output_path:
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(cost_surface.astype(np.float32), 1)
            logger.info(f"Saved cost surface to {output_path}")

        return cost_surface, profile

    def process_state(self, state_name: str) -> str:
        """
        Process DEM and land cover for a state to generate cost surface.
        
        Args:
            state_name: Name of state (e.g., "Utah")
            
        Returns:
            Path to generated cost surface file
        """
        state_lower = state_name.lower()

        # Define paths
        dem_path = self.processed_dir / f"{state_lower}_dem.tif"
        landcover_path = self.processed_dir / f"{state_lower}_landcover.tif"
        slope_path = self.processed_dir / f"{state_lower}_slope.tif"
        cost_path = self.processed_dir / f"{state_lower}_cost_surface.tif"

        # Check inputs exist
        if not dem_path.exists():
            raise FileNotFoundError(f"DEM not found: {dem_path}")
        if not landcover_path.exists():
            raise FileNotFoundError(f"Land cover not found: {landcover_path}")

        # Generate outputs
        logger.info(f"Processing cost surface for {state_name}")

        # Calculate and save slope
        self.calculate_slope(str(dem_path), str(slope_path))

        # Generate cost surface
        cost_surface, profile = self.generate_cost_surface(
            str(dem_path), str(landcover_path), str(cost_path))

        logger.info(f"Cost surface generation complete: {cost_path}")
        return str(cost_path)


def main():
    """Command-line interface for cost surface generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate cost surfaces for distance analysis")
    parser.add_argument("--state", default="Utah", help="State name")
    parser.add_argument("--config",
                        default="config.yaml",
                        help="Configuration file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    generator = CostSurfaceGenerator(args.config)
    cost_path = generator.process_state(args.state)
    print(f"Cost surface saved to: {cost_path}")


if __name__ == "__main__":
    main()
