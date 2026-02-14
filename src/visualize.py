"""
Visualization module for creating maps and visualizations.

This module creates:
- Static maps with matplotlib
- Interactive maps with folium
"""
from pathlib import Path
from typing import Dict, Optional

import branca.colormap as cm
import folium
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from folium import plugins
from matplotlib.colors import LinearSegmentedColormap

from .config import get_config


class Visualizer:
    """Creates visualizations of unreachability analysis."""

    def __init__(self, config=None):
        """
        Initialize Visualizer.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or get_config()
        self.config.ensure_directories()

    def create_static_map(self,
                          distance_field: np.ndarray,
                          boundary: gpd.GeoDataFrame,
                          roads: gpd.GeoDataFrame,
                          unreachable_point: Dict,
                          metadata: Dict,
                          output_path: Optional[Path] = None) -> Path:
        """
        Create a static map using matplotlib.
        
        Args:
            distance_field: Distance field array
            boundary: Boundary GeoDataFrame
            roads: Roads GeoDataFrame
            unreachable_point: Dictionary with unreachable point info
            metadata: Raster metadata
            output_path: Path to save figure. If None, uses default.
            
        Returns:
            Path to saved figure
        """
        print("Creating static map...")

        if output_path is None:
            state_name = self.config.state_name.lower()
            output_path = self.config.get_path(
                'maps') / f"{state_name}_unreachability_map.png"

        # Create figure
        figsize = self.config.get('visualization.figsize', [12, 10])
        fig, ax = plt.subplots(figsize=figsize)

        # Get transform for extent
        transform = metadata['transform']
        bounds = metadata['bounds']
        extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

        # Plot distance field as heatmap
        cmap = self.config.get('visualization.colormap', 'YlOrRd')

        # Convert distance to km for display
        distance_km = distance_field / 1000

        im = ax.imshow(distance_km,
                       extent=extent,
                       origin='upper',
                       cmap=cmap,
                       interpolation='bilinear',
                       alpha=0.8)

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label('Distance from Road (km)',
                       rotation=270,
                       labelpad=20,
                       fontsize=12)

        # Plot boundary
        boundary.boundary.plot(ax=ax,
                               color='black',
                               linewidth=2,
                               label='State Boundary')

        # Plot roads (sample if too many)
        if len(roads) > 10000:
            roads_sample = roads.sample(n=10000, random_state=42)
            print(
                f"  Plotting sample of {len(roads_sample)} roads (out of {len(roads)})"
            )
        else:
            roads_sample = roads

        roads_sample.plot(ax=ax,
                          color='black',
                          linewidth=0.3,
                          alpha=0.3,
                          label='Roads')

        # Plot unreachable point
        point_x = unreachable_point['x_projected']
        point_y = unreachable_point['y_projected']

        ax.plot(point_x,
                point_y,
                'r*',
                markersize=20,
                markeredgecolor='white',
                markeredgewidth=1.5,
                label='Most Unreachable Point',
                zorder=5)

        # Add annotation
        distance_km_val = unreachable_point['distance_km']
        ax.annotate(f"{distance_km_val:.2f} km from nearest road",
                    xy=(point_x, point_y),
                    xytext=(15, 15),
                    textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5',
                              facecolor='white',
                              alpha=0.8),
                    arrowprops=dict(arrowstyle='->',
                                    connectionstyle='arc3,rad=0'),
                    fontsize=10,
                    fontweight='bold')

        # Set labels and title
        ax.set_xlabel('Easting (m)', fontsize=12)
        ax.set_ylabel('Northing (m)', fontsize=12)
        ax.set_title(
            f'Most Unreachable Location in {self.config.state_name}\n'
            f'Euclidean Distance from Roads',
            fontsize=14,
            fontweight='bold',
            pad=20)

        # Add legend
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

        # Add grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

        # Tight layout
        plt.tight_layout()

        # Save
        dpi = self.config.get('visualization.dpi', 300)
        plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
        print(f"  Saved static map to {output_path}")

        plt.close()

        return output_path

    def create_interactive_map(self,
                               distance_field: np.ndarray,
                               boundary: gpd.GeoDataFrame,
                               roads: gpd.GeoDataFrame,
                               unreachable_point: Dict,
                               results: Dict,
                               output_path: Optional[Path] = None) -> Path:
        """
        Create an interactive map using folium.
        
        Args:
            distance_field: Distance field array
            boundary: Boundary GeoDataFrame
            roads: Roads GeoDataFrame
            unreachable_point: Dictionary with unreachable point info
            results: Full results dictionary with top 10 points
            output_path: Path to save HTML. If None, uses default.
            
        Returns:
            Path to saved HTML file
        """
        print("Creating interactive map...")

        if output_path is None:
            state_name = self.config.state_name.lower()
            output_path = self.config.get_path(
                'maps') / f"{state_name}_unreachability_interactive.html"

        # Convert to WGS84 for folium
        boundary_wgs84 = boundary.to_crs('EPSG:4326')

        # Get center of boundary for map center
        center_lat = unreachable_point['latitude']
        center_lon = unreachable_point['longitude']

        # Create base map
        m = folium.Map(location=[center_lat, center_lon],
                       zoom_start=7,
                       tiles='OpenStreetMap',
                       control_scale=True)

        # Add different tile layers with proper attribution
        folium.TileLayer(
            tiles=
            'https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}.jpg',
            attr=
            'Map tiles by Stadia Maps, under CC BY 3.0. Data by OpenStreetMap, under ODbL',
            name='Terrain').add_to(m)
        folium.TileLayer(
            tiles=
            'https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}.png',
            attr=
            'Map tiles by Stadia Maps, under CC BY 3.0. Data by OpenStreetMap, under ODbL',
            name='Toner').add_to(m)
        folium.TileLayer('CartoDB positron', name='Light').add_to(m)

        # Add boundary
        boundary_layer = folium.FeatureGroup(name='State Boundary', show=True)
        folium.GeoJson(boundary_wgs84,
                       style_function=lambda x: {
                           'fillColor': 'transparent',
                           'color': 'black',
                           'weight': 3,
                           'fillOpacity': 0
                       }).add_to(boundary_layer)
        boundary_layer.add_to(m)

        # Add most unreachable point
        unreachable_layer = folium.FeatureGroup(name='Most Unreachable Point',
                                                show=True)

        folium.Marker(
            location=[center_lat, center_lon],
            popup=folium.Popup(
                f"<b>Most Unreachable Point</b><br>"
                f"Distance: {unreachable_point['distance_km']:.2f} km<br>"
                f"Lat: {center_lat:.6f}<br>"
                f"Lon: {center_lon:.6f}",
                max_width=300),
            tooltip=
            f"Most Unreachable: {unreachable_point['distance_km']:.2f} km from road",
            icon=folium.Icon(color='red', icon='star',
                             prefix='fa')).add_to(unreachable_layer)

        unreachable_layer.add_to(m)

        # Add top 10 unreachable points
        top10_layer = folium.FeatureGroup(name='Top 10 Unreachable Points',
                                          show=False)

        for point in results['top_10_unreachable']:
            rank = point['rank']
            lat = point['latitude']
            lon = point['longitude']
            dist_km = point['distance_km']

            color = 'red' if rank == 1 else 'orange' if rank <= 3 else 'lightred'

            folium.CircleMarker(
                location=[lat, lon],
                radius=10 - rank * 0.5,
                popup=f"<b>Rank #{rank}</b><br>Distance: {dist_km:.2f} km",
                tooltip=f"#{rank}: {dist_km:.2f} km",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7).add_to(top10_layer)

        top10_layer.add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add fullscreen option
        plugins.Fullscreen().add_to(m)

        # Add title
        title_html = f'''
            <div style="position: fixed; 
                        top: 10px; left: 50px; width: 400px; height: 90px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px; opacity: 0.9;">
                <h4 style="margin: 0;">{self.config.state_name} Unreachability Map</h4>
                <p style="margin: 5px 0;">Most remote point: <b>{unreachable_point['distance_km']:.2f} km</b> from nearest road</p>
                <p style="margin: 0; font-size: 11px; color: #666;">
                    Location: {center_lat:.4f}, {center_lon:.4f}
                </p>
            </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))

        # Save
        m.save(str(output_path))
        print(f"  Saved interactive map to {output_path}")

        return output_path

    def visualize_all(self, distance_data: dict, processed_data: dict,
                      results: dict) -> dict:
        """
        Create all visualizations.
        
        Args:
            distance_data: Dictionary with distance field and metadata
            processed_data: Dictionary with processed geodata
            results: Analysis results dictionary
            
        Returns:
            Dictionary with paths to created visualizations
        """
        print("=" * 60)
        print("CREATING VISUALIZATIONS")
        print("=" * 60)

        distance_field = distance_data['distance_field']
        metadata = distance_data['metadata']
        boundary = processed_data['boundary']
        roads = processed_data['roads']
        unreachable_point = results['most_unreachable_point']

        outputs = {}

        # Static map
        if self.config.get('output.static_map', True):
            print("\n1. Creating static map...")
            static_path = self.create_static_map(distance_field, boundary,
                                                 roads, unreachable_point,
                                                 metadata)
            outputs['static_map'] = static_path

        # Interactive map
        if self.config.get('output.interactive_map', True):
            print("\n2. Creating interactive map...")
            interactive_path = self.create_interactive_map(
                distance_field, boundary, roads, unreachable_point, results)
            outputs['interactive_map'] = interactive_path

        print("=" * 60)
        print("VISUALIZATION COMPLETE")
        print("=" * 60)

        return outputs


def main():
    """Main function for testing visualization."""
    from .analyze import UnreachabilityAnalyzer
    from .distance import DistanceCalculator
    from .fetch import DataFetcher
    from .preprocess import DataPreprocessor

    # Run full pipeline
    print("Running full pipeline for visualization test...\n")

    fetcher = DataFetcher()
    data = fetcher.fetch_all()

    preprocessor = DataPreprocessor()
    processed = preprocessor.preprocess_all(data)

    calculator = DistanceCalculator()
    distance_data = calculator.compute_all(processed)

    analyzer = UnreachabilityAnalyzer()
    results = analyzer.analyze_all(distance_data, processed)

    # Create visualizations
    visualizer = Visualizer()
    outputs = visualizer.visualize_all(distance_data, processed, results)

    print("\n" + "=" * 60)
    print("VISUALIZATIONS CREATED")
    print("=" * 60)
    for name, path in outputs.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
