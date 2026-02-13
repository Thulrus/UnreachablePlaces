"""
Data acquisition module for fetching geospatial data.

This module handles:
- Downloading state boundary from US Census TIGER
- Fetching road network from OpenStreetMap
- Optionally fetching settlement data
"""
import os
import geopandas as gpd
import osmnx as ox
import requests
from pathlib import Path
from typing import Optional
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
        
    def fetch_state_boundary(self, state_name: Optional[str] = None) -> gpd.GeoDataFrame:
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
        
        output_path = self.config.get_path('raw_data') / f"{state_name.lower()}_boundary.geojson"
        
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
            state_gdf = gdf[gdf['NAME'].str.upper() == state_name.upper()].copy()
            
            if len(state_gdf) == 0:
                raise ValueError(f"State '{state_name}' not found in dataset")
            
            # Save to file
            state_gdf.to_file(output_path, driver='GeoJSON')
            print(f"Saved boundary to {output_path}")
            
            return state_gdf
            
        except Exception as e:
            print(f"Error fetching state boundary: {e}")
            raise
    
    def fetch_roads(self, boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
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
        output_path = self.config.get_path('raw_data') / f"{state_name.lower()}_roads.geojson"
        
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
                G = ox.graph_from_polygon(polygon, network_type='drive', custom_filter=road_filter)
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
    
    def fetch_settlements(self, boundary: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
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
        output_path = self.config.get_path('raw_data') / f"{state_name.lower()}_settlements.geojson"
        
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
            settlements = settlements[settlements.geometry.type == 'Point'].copy()
            
            print(f"Downloaded {len(settlements)} settlements")
            
            # Save to file
            settlements.to_file(output_path, driver='GeoJSON')
            print(f"Saved settlements to {output_path}")
            
            return settlements
            
        except Exception as e:
            print(f"Error fetching settlements: {e}")
            print("Continuing without settlements...")
            return gpd.GeoDataFrame()
    
    def fetch_all(self) -> dict:
        """
        Fetch all required data.
        
        Returns:
            Dictionary with 'boundary', 'roads', and optionally 'settlements' GeoDataFrames
        """
        print("=" * 60)
        print("FETCHING ALL DATA")
        print("=" * 60)
        
        # Fetch boundary
        boundary = self.fetch_state_boundary()
        
        # Fetch roads
        roads = self.fetch_roads(boundary)
        
        # Optionally fetch settlements
        data = {
            'boundary': boundary,
            'roads': roads
        }
        
        if self.config.get('data.include_settlements', False):
            settlements = self.fetch_settlements(boundary)
            if len(settlements) > 0:
                data['settlements'] = settlements
        
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
