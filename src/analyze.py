"""
Analysis module for finding unreachable locations.

This module extracts the most unreachable point(s) from the distance field.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from rasterio.transform import Affine

from .config import get_config


class UnreachabilityAnalyzer:
    """Analyzes distance fields to find unreachable locations."""

    def __init__(self, config=None):
        """
        Initialize UnreachabilityAnalyzer.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()

    def create_land_mask(self, landcover: np.ndarray) -> np.ndarray:
        """
        Create a mask of valid land areas (excluding water bodies, etc.).
        
        This prevents water bodies from being identified as "unreachable locations"
        while still allowing them to act as barriers in cost-distance calculations.
        
        Args:
            landcover: Land cover classification array (NLCD codes)
            
        Returns:
            Boolean mask where True = valid land, False = excluded (water/ice/etc)
        """
        # NLCD codes to exclude from being "unreachable locations"
        # These are non-land features that aren't interesting destinations
        excluded_codes = self.config.get(
            'analysis.exclude_landcover',
            [
                11,  # Open Water
                12,  # Perennial Ice/Snow
            ])

        # Create mask: True for valid land, False for excluded areas
        mask = np.ones(landcover.shape, dtype=bool)
        for code in excluded_codes:
            mask &= (landcover != code)

        return mask

    def find_maximum(
            self,
            distance_field: np.ndarray,
            land_mask: Optional[np.ndarray] = None) -> Tuple[int, int, float]:
        """
        Find the pixel with maximum distance.
        
        Args:
            distance_field: Distance field array (may contain NaN for masked areas)
            land_mask: Optional boolean mask where True = valid land to consider
            
        Returns:
            Tuple of (row, col, distance)
        """
        print("Finding maximum distance pixel...")

        # Apply land mask if provided
        working_field = distance_field.copy()
        if land_mask is not None:
            # Set excluded areas to NaN
            working_field[~land_mask] = np.nan
            print(f"  Applying land mask (excluding water/ice)")

        # Find maximum ignoring NaN
        max_distance = np.nanmax(working_field)

        # Find pixel coordinates of maximum IN THE MASKED FIELD
        max_indices = np.where(working_field == max_distance)

        # Take first occurrence if multiple maxima
        row = max_indices[0][0]
        col = max_indices[1][0]

        print(f"  Found at pixel ({row}, {col})")
        print(f"  Distance: {max_distance:.2f} m ({max_distance/1000:.2f} km)")

        return row, col, max_distance

    def pixel_to_coords(self, row: int, col: int,
                        transform: Affine) -> Tuple[float, float]:
        """
        Convert pixel coordinates to geographic coordinates.
        
        Args:
            row: Row index
            col: Column index
            transform: Affine transform
            
        Returns:
            Tuple of (x, y) coordinates
        """
        # Get center of pixel
        x, y = transform * (col + 0.5, row + 0.5)

        return x, y

    def find_top_n_unreachable(
        self,
        distance_field: np.ndarray,
        n: int = 5,
        min_separation_km: float = 25.0,
        resolution_m: float = 250.0,
        land_mask: Optional[np.ndarray] = None
    ) -> List[Tuple[int, int, float]]:
        """
        Find the top N most unreachable pixels with minimum separation.
        
        This ensures the top N locations are spatially distributed rather than
        all clustered around a single remote area.
        
        Args:
            distance_field: Distance field array
            n: Number of top locations to find
            min_separation_km: Minimum separation between locations (km)
            resolution_m: Pixel resolution in meters
            land_mask: Optional boolean mask where True = valid land to consider
            
        Returns:
            List of (row, col, distance) tuples, spatially separated
        """
        print(f"Finding top {n} most unreachable pixels...")
        print(f"  Minimum separation: {min_separation_km} km")

        # Convert min separation to pixels
        min_separation_pixels = int((min_separation_km * 1000) / resolution_m)
        print(
            f"  ({min_separation_pixels} pixels at {resolution_m}m resolution)"
        )

        # Create a working copy of the distance field
        working_field = distance_field.copy()

        # Apply land mask if provided
        if land_mask is not None:
            working_field[~land_mask] = np.nan
            print(f"  Applying land mask (excluding water/ice)")

        # Create coordinate grids for distance calculation
        rows, cols = np.meshgrid(np.arange(working_field.shape[0]),
                                 np.arange(working_field.shape[1]),
                                 indexing='ij')

        results = []

        for i in range(n):
            # Find current maximum
            max_distance = np.nanmax(working_field)

            # Check if we have valid data left
            if np.isnan(max_distance) or max_distance <= 0:
                print(
                    f"  Warning: Only found {i} valid locations (requested {n})"
                )
                break

            # Find pixel coordinates of maximum
            max_indices = np.where(working_field == max_distance)
            row = max_indices[0][0]
            col = max_indices[1][0]

            results.append((int(row), int(col), float(max_distance)))
            print(
                f"  #{i+1}: {max_distance/1000:.2f} km at pixel ({row}, {col})"
            )

            # Mask out area within min_separation_pixels
            # Calculate distance from this point to all pixels
            distances = np.sqrt((rows - row)**2 + (cols - col)**2)

            # Set all pixels within separation radius to NaN
            mask = distances < min_separation_pixels
            working_field[mask] = np.nan

        return results

    def analyze_all(self, distance_data: dict, processed_data: dict) -> Dict:
        """
        Run full analysis pipeline.
        
        Args:
            distance_data: Dictionary with distance field and metadata
            processed_data: Dictionary with processed boundary data
            
        Returns:
            Dictionary with analysis results
        """
        print("=" * 60)
        print("ANALYZING UNREACHABILITY")
        print("=" * 60)

        distance_field = distance_data['distance_field']
        metadata = distance_data['metadata']
        transform = metadata['transform']
        crs = metadata['crs']
        boundary = processed_data['boundary']

        # Create land mask if landcover data is available
        land_mask = None
        if 'landcover' in distance_data:
            print("\nCreating land mask to exclude water bodies...")
            landcover = distance_data['landcover']
            land_mask = self.create_land_mask(landcover)
            excluded_pixels = np.sum(~land_mask)
            total_pixels = land_mask.size
            print(
                f"  Excluding {excluded_pixels:,} pixels ({excluded_pixels/total_pixels*100:.1f}%)"
            )

        # Find maximum unreachable point
        print("\n1. Finding most unreachable point...")
        row, col, max_distance = self.find_maximum(distance_field, land_mask)

        # Convert to geographic coordinates
        print("\n2. Converting to geographic coordinates...")
        x, y = self.pixel_to_coords(row, col, transform)

        print(f"  Projected coords ({crs}): ({x:.2f}, {y:.2f})")

        # Convert to lat/lon for readability
        import geopandas as gpd
        from shapely.geometry import Point

        point_gdf = gpd.GeoDataFrame(geometry=[Point(x, y)], crs=crs)
        point_wgs84 = point_gdf.to_crs('EPSG:4326')
        lon, lat = point_wgs84.geometry.iloc[0].x, point_wgs84.geometry.iloc[
            0].y

        print(f"  Lat/Lon (EPSG:4326): ({lat:.6f}, {lon:.6f})")

        # Get top N settings from config
        top_n = self.config.get('analysis.top_n', 5)
        min_separation_km = self.config.get('analysis.min_separation_km', 25.0)
        resolution_m = self.config.resolution

        # Find top N unreachable points with spatial separation
        print(f"\n3. Finding top {top_n} most unreachable points...")
        top_n_points = self.find_top_n_unreachable(
            distance_field,
            n=top_n,
            min_separation_km=min_separation_km,
            resolution_m=resolution_m,
            land_mask=land_mask)

        # Convert all to geographic coordinates
        top_n_geo = []
        for i, (r, c, dist) in enumerate(top_n_points, 1):
            x_i, y_i = self.pixel_to_coords(r, c, transform)
            point_gdf_i = gpd.GeoDataFrame(geometry=[Point(x_i, y_i)], crs=crs)
            point_wgs84_i = point_gdf_i.to_crs('EPSG:4326')
            lon_i, lat_i = point_wgs84_i.geometry.iloc[
                0].x, point_wgs84_i.geometry.iloc[0].y

            top_n_geo.append({
                'rank': i,
                'distance_m': float(dist),
                'distance_km': float(dist / 1000),
                'pixel_row': int(r),
                'pixel_col': int(c),
                'x_projected': float(x_i),
                'y_projected': float(y_i),
                'latitude': float(lat_i),
                'longitude': float(lon_i)
            })

            print(f"  #{i}: {dist/1000:.2f} km at ({lat_i:.6f}, {lon_i:.6f})")

        # Calculate statistics
        print("\n4. Computing statistics...")
        valid_distances = distance_field[~np.isnan(distance_field)]

        stats = {
            'max_distance_m': float(np.max(valid_distances)),
            'max_distance_km': float(np.max(valid_distances) / 1000),
            'mean_distance_m': float(np.mean(valid_distances)),
            'mean_distance_km': float(np.mean(valid_distances) / 1000),
            'median_distance_m': float(np.median(valid_distances)),
            'median_distance_km': float(np.median(valid_distances) / 1000),
            'std_distance_m': float(np.std(valid_distances)),
            'total_pixels': int(distance_field.size),
            'valid_pixels': int(len(valid_distances))
        }

        print(f"  Max: {stats['max_distance_km']:.2f} km")
        print(f"  Mean: {stats['mean_distance_km']:.2f} km")
        print(f"  Median: {stats['median_distance_km']:.2f} km")

        # Compile results
        results = {
            'state': self.config.state_name,
            'crs': str(crs),
            'resolution_m': self.config.resolution,
            'analysis_settings': {
                'top_n': top_n,
                'min_separation_km': min_separation_km
            },
            'most_unreachable_point': {
                'distance_m': float(max_distance),
                'distance_km': float(max_distance / 1000),
                'pixel_row': int(row),
                'pixel_col': int(col),
                'x_projected': float(x),
                'y_projected': float(y),
                'latitude': float(lat),
                'longitude': float(lon)
            },
            f'top_{top_n}_unreachable': top_n_geo,
            'statistics': stats
        }

        # Save results
        print("\n5. Saving results...")
        results_file = self.config.get('output.results_file',
                                       'outputs/results.json')
        results_path = Path(results_file)
        results_path.parent.mkdir(parents=True, exist_ok=True)

        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"  Saved to {results_path}")

        print("=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

        return results


def main():
    """Main function for testing analysis."""
    from .distance import DistanceCalculator
    from .fetch import DataFetcher
    from .preprocess import DataPreprocessor

    # Run full pipeline
    fetcher = DataFetcher()
    data = fetcher.fetch_all()

    preprocessor = DataPreprocessor()
    processed = preprocessor.preprocess_all(data)

    calculator = DistanceCalculator()
    distance_data = calculator.compute_all(processed)

    # Analyze
    analyzer = UnreachabilityAnalyzer()
    results = analyzer.analyze_all(distance_data, processed)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(f"Most unreachable point in {results['state']}:")
    print(f"  Location: {results['most_unreachable_point']['latitude']:.6f}, "
          f"{results['most_unreachable_point']['longitude']:.6f}")
    print(
        f"  Distance from road: {results['most_unreachable_point']['distance_km']:.2f} km"
    )


if __name__ == '__main__':
    main()
