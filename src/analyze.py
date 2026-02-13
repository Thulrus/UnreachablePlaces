"""
Analysis module for finding unreachable locations.

This module extracts the most unreachable point(s) from the distance field.
"""
import numpy as np
import json
from pathlib import Path
from typing import Tuple, Dict, List
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
        
    def find_maximum(self, distance_field: np.ndarray) -> Tuple[int, int, float]:
        """
        Find the pixel with maximum distance.
        
        Args:
            distance_field: Distance field array (may contain NaN for masked areas)
            
        Returns:
            Tuple of (row, col, distance)
        """
        print("Finding maximum distance pixel...")
        
        # Find maximum ignoring NaN
        max_distance = np.nanmax(distance_field)
        
        # Find pixel coordinates of maximum
        max_indices = np.where(distance_field == max_distance)
        
        # Take first occurrence if multiple maxima
        row = max_indices[0][0]
        col = max_indices[1][0]
        
        print(f"  Found at pixel ({row}, {col})")
        print(f"  Distance: {max_distance:.2f} m ({max_distance/1000:.2f} km)")
        
        return row, col, max_distance
    
    def pixel_to_coords(self, row: int, col: int, transform: Affine) -> Tuple[float, float]:
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
    
    def find_top_n_unreachable(self, distance_field: np.ndarray, 
                              n: int = 10) -> List[Tuple[int, int, float]]:
        """
        Find the top N most unreachable pixels.
        
        Args:
            distance_field: Distance field array
            n: Number of top locations to find
            
        Returns:
            List of (row, col, distance) tuples
        """
        print(f"Finding top {n} most unreachable pixels...")
        
        # Flatten and remove NaN
        flat_field = distance_field.flatten()
        valid_mask = ~np.isnan(flat_field)
        valid_values = flat_field[valid_mask]
        valid_indices = np.where(valid_mask)[0]
        
        # Get top N indices
        top_n_indices = np.argsort(valid_values)[-n:][::-1]
        
        # Convert back to 2D coordinates
        results = []
        for idx in top_n_indices:
            flat_idx = valid_indices[idx]
            row, col = np.unravel_index(flat_idx, distance_field.shape)
            distance = distance_field[row, col]
            results.append((int(row), int(col), float(distance)))
        
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
        
        # Find maximum unreachable point
        print("\n1. Finding most unreachable point...")
        row, col, max_distance = self.find_maximum(distance_field)
        
        # Convert to geographic coordinates
        print("\n2. Converting to geographic coordinates...")
        x, y = self.pixel_to_coords(row, col, transform)
        
        print(f"  Projected coords ({crs}): ({x:.2f}, {y:.2f})")
        
        # Convert to lat/lon for readability
        import geopandas as gpd
        from shapely.geometry import Point
        
        point_gdf = gpd.GeoDataFrame(
            geometry=[Point(x, y)],
            crs=crs
        )
        point_wgs84 = point_gdf.to_crs('EPSG:4326')
        lon, lat = point_wgs84.geometry.iloc[0].x, point_wgs84.geometry.iloc[0].y
        
        print(f"  Lat/Lon (EPSG:4326): ({lat:.6f}, {lon:.6f})")
        
        # Find top 10 unreachable points
        print("\n3. Finding top 10 most unreachable points...")
        top_10 = self.find_top_n_unreachable(distance_field, n=10)
        
        # Convert all to geographic coordinates
        top_10_geo = []
        for i, (r, c, dist) in enumerate(top_10, 1):
            x_i, y_i = self.pixel_to_coords(r, c, transform)
            point_gdf_i = gpd.GeoDataFrame(geometry=[Point(x_i, y_i)], crs=crs)
            point_wgs84_i = point_gdf_i.to_crs('EPSG:4326')
            lon_i, lat_i = point_wgs84_i.geometry.iloc[0].x, point_wgs84_i.geometry.iloc[0].y
            
            top_10_geo.append({
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
            'top_10_unreachable': top_10_geo,
            'statistics': stats
        }
        
        # Save results
        print("\n5. Saving results...")
        results_file = self.config.get('output.results_file', 'outputs/results.json')
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
    from .fetch import DataFetcher
    from .preprocess import DataPreprocessor
    from .distance import DistanceCalculator
    
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
    print(f"  Distance from road: {results['most_unreachable_point']['distance_km']:.2f} km")


if __name__ == '__main__':
    main()
