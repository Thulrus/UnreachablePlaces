"""
Command-line interface for the unreachable mapper tool.

This provides a CLI for running the full pipeline or individual steps.
"""
import sys
from pathlib import Path

import click

from .analyze import UnreachabilityAnalyzer
from .config import Config, get_config, set_config
from .cost_surface import CostSurfaceGenerator
from .distance import DistanceCalculator
from .fetch import DataFetcher
from .preprocess import DataPreprocessor
from .visualize import Visualizer


@click.group()
@click.option('--config',
              '-c',
              type=click.Path(exists=True),
              help='Path to configuration file')
@click.pass_context
def cli(ctx, config):
    """
    Unreachable Mapper - Find the most unreachable locations.
    
    This tool computes and visualizes the most unreachable location
    based on Euclidean distance from roads.
    """
    ctx.ensure_object(dict)

    if config:
        ctx.obj['config'] = Config(config)
        set_config(ctx.obj['config'])
    else:
        ctx.obj['config'] = get_config()


@cli.command()
@click.pass_context
def fetch_data(ctx):
    """Fetch geospatial data (state boundary and roads)."""
    click.echo("=" * 60)
    click.echo("FETCHING DATA")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']
        fetcher = DataFetcher(config)
        data = fetcher.fetch_all()

        click.echo("\n✓ Data fetch complete!")
        click.echo(f"  Boundary: {len(data['boundary'])} features")
        click.echo(f"  Roads: {len(data['roads'])} features")

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1


@cli.command()
@click.pass_context
def preprocess(ctx):
    """Preprocess data (reproject, clip, rasterize)."""
    click.echo("=" * 60)
    click.echo("PREPROCESSING DATA")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']

        # Load fetched data
        state_name = config.state_name.lower()
        raw_data_path = config.get_path('raw_data')

        import geopandas as gpd

        boundary_file = raw_data_path / f"{state_name}_boundary.geojson"
        roads_file = raw_data_path / f"{state_name}_roads.geojson"

        if not boundary_file.exists() or not roads_file.exists():
            click.echo("✗ Data not found. Please run 'fetch_data' first.",
                       err=True)
            return 1

        data = {
            'boundary': gpd.read_file(boundary_file),
            'roads': gpd.read_file(roads_file)
        }

        # Preprocess
        preprocessor = DataPreprocessor(config)
        processed = preprocessor.preprocess_all(data)

        click.echo("\n✓ Preprocessing complete!")
        click.echo(f"  Road mask shape: {processed['road_mask'].shape}")

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1


@cli.command()
@click.pass_context
def cost_surface(ctx):
    """Generate cost surface from DEM and land cover (for cost-distance analysis)."""
    click.echo("=" * 60)
    click.echo("GENERATING COST SURFACE")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']

        # Check if cost-distance is enabled
        if not config.get('cost_distance.enabled', False):
            click.echo("✗ Cost-distance is not enabled in configuration.",
                       err=True)
            click.echo("  Set 'cost_distance.enabled: true' in config.yaml",
                       err=True)
            return 1

        # Check if DEM and land cover exist
        state_name = config.state_name.lower()
        raw_data_path = config.get_path('raw_data')

        dem_file = raw_data_path / f"{state_name}_dem.tif"
        landcover_file = raw_data_path / f"{state_name}_landcover.tif"

        if not dem_file.exists():
            click.echo(f"✗ DEM not found: {dem_file}", err=True)
            click.echo(
                "  Run 'fetch-data' with cost_distance.enabled: true first.",
                err=True)
            return 1

        if not landcover_file.exists():
            click.echo(f"✗ Land cover not found: {landcover_file}", err=True)
            click.echo(
                "  Run 'fetch-data' with cost_distance.enabled: true first.",
                err=True)
            return 1

        # Generate cost surface
        generator = CostSurfaceGenerator()
        cost_path = generator.process_state(config.state_name)

        click.echo("\n✓ Cost surface generation complete!")
        click.echo(f"  Output: {cost_path}")

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
@click.pass_context
def compute_distance(ctx):
    """Compute distance field from roads."""
    click.echo("=" * 60)
    click.echo("COMPUTING DISTANCE FIELD")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']

        # Load preprocessed data
        state_name = config.state_name.lower()
        processed_path = config.get_path('processed_data')

        import geopandas as gpd
        import numpy as np
        import rasterio

        boundary_file = processed_path / f"{state_name}_boundary_projected.geojson"
        road_mask_file = processed_path / f"{state_name}_road_mask.tif"

        if not boundary_file.exists() or not road_mask_file.exists():
            click.echo(
                "✗ Preprocessed data not found. Please run 'preprocess' first.",
                err=True)
            return 1

        # Load data
        boundary = gpd.read_file(boundary_file)

        with rasterio.open(road_mask_file) as src:
            road_mask = src.read(1)
            metadata = {
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'crs': src.crs,
                'bounds': src.bounds
            }

        processed = {
            'boundary': boundary,
            'road_mask': road_mask,
            'raster_metadata': metadata
        }

        # Compute distance
        calculator = DistanceCalculator(config)
        distance_data = calculator.compute_all(processed)

        max_dist = np.nanmax(distance_data['distance_field'])
        click.echo(f"\n✓ Distance computation complete!")
        click.echo(f"  Maximum distance: {max_dist/1000:.2f} km")

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1


@cli.command()
@click.pass_context
def find_unreachable(ctx):
    """Find the most unreachable point."""
    click.echo("=" * 60)
    click.echo("FINDING UNREACHABLE POINT")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']

        # Load distance field
        state_name = config.state_name.lower()
        processed_path = config.get_path('processed_data')

        import geopandas as gpd
        import rasterio

        # Check which distance mode was used
        if config.get('cost_distance.enabled', False):
            distance_file = processed_path / f"{state_name}_distance_cost.tif"
        else:
            distance_file = processed_path / f"{state_name}_distance.tif"
        boundary_file = processed_path / f"{state_name}_boundary_projected.geojson"

        if not distance_file.exists():
            click.echo(
                "✗ Distance field not found. Please run 'compute_distance' first.",
                err=True)
            return 1

        # Load data
        with rasterio.open(distance_file) as src:
            distance_field = src.read(1)
            metadata = {
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'crs': src.crs,
                'bounds': src.bounds
            }

        boundary = gpd.read_file(boundary_file)

        distance_data = {
            'distance_field': distance_field,
            'metadata': metadata
        }

        processed_data = {'boundary': boundary}

        # Analyze
        analyzer = UnreachabilityAnalyzer(config)
        results = analyzer.analyze_all(distance_data, processed_data)

        click.echo("\n✓ Analysis complete!")
        click.echo(f"\nMost unreachable point:")
        click.echo(
            f"  Location: {results['most_unreachable_point']['latitude']:.6f}, "
            f"{results['most_unreachable_point']['longitude']:.6f}")
        click.echo(
            f"  Distance: {results['most_unreachable_point']['distance_km']:.2f} km"
        )

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1


@cli.command()
@click.pass_context
def visualize(ctx):
    """Create visualizations (maps)."""
    click.echo("=" * 60)
    click.echo("CREATING VISUALIZATIONS")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']

        # Load all necessary data
        state_name = config.state_name.lower()
        processed_path = config.get_path('processed_data')

        import json

        import geopandas as gpd
        import rasterio

        # Check which distance mode was used
        if config.get('cost_distance.enabled', False):
            distance_file = processed_path / f"{state_name}_distance_cost.tif"
        else:
            distance_file = processed_path / f"{state_name}_distance.tif"
        boundary_file = processed_path / f"{state_name}_boundary_projected.geojson"
        roads_file = processed_path / f"{state_name}_roads_clipped.geojson"
        results_file = config.get('output.results_file',
                                  'outputs/results.json')

        if not all([
                Path(f).exists()
                for f in [distance_file, boundary_file, results_file]
        ]):
            click.echo(
                "✗ Required data not found. Please run previous steps first.",
                err=True)
            return 1

        # Load data
        with rasterio.open(distance_file) as src:
            distance_field = src.read(1)
            metadata = {
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'crs': src.crs,
                'bounds': src.bounds
            }

        boundary = gpd.read_file(boundary_file)
        roads = gpd.read_file(
            roads_file) if roads_file.exists() else gpd.GeoDataFrame()

        with open(results_file, 'r') as f:
            results = json.load(f)

        distance_data = {
            'distance_field': distance_field,
            'metadata': metadata
        }

        processed_data = {'boundary': boundary, 'roads': roads}

        # Visualize
        visualizer = Visualizer(config)
        outputs = visualizer.visualize_all(distance_data, processed_data,
                                           results)

        click.echo("\n✓ Visualizations created!")
        for name, path in outputs.items():
            click.echo(f"  {name}: {path}")

        return 0
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
@click.option('--skip-fetch',
              is_flag=True,
              help='Skip data fetching if already downloaded')
@click.pass_context
def run_all(ctx, skip_fetch):
    """Run the complete pipeline from start to finish."""
    click.echo("=" * 60)
    click.echo("RUNNING COMPLETE PIPELINE")
    click.echo("=" * 60)

    try:
        config = ctx.obj['config']
        click.echo(f"\nConfiguration:")
        click.echo(f"  State: {config.state_name}")
        click.echo(f"  CRS: {config.crs}")
        click.echo(f"  Resolution: {config.resolution}m")
        click.echo()

        # Step 1: Fetch data
        if not skip_fetch:
            click.echo("\n[1/5] Fetching data...")
            fetcher = DataFetcher(config)
            data = fetcher.fetch_all()
        else:
            click.echo(
                "\n[1/5] Skipping data fetch (loading existing data)...")
            state_name = config.state_name.lower()
            raw_data_path = config.get_path('raw_data')

            import geopandas as gpd

            data = {
                'boundary':
                gpd.read_file(raw_data_path /
                              f"{state_name}_boundary.geojson"),
                'roads':
                gpd.read_file(raw_data_path / f"{state_name}_roads.geojson")
            }

        # Step 2: Preprocess
        click.echo("\n[2/5] Preprocessing...")
        preprocessor = DataPreprocessor(config)
        processed = preprocessor.preprocess_all(data)

        # Step 2.5: Generate cost surface if cost-distance enabled
        if config.get('cost_distance.enabled', False):
            click.echo("\n[2.5/5] Generating cost surface...")
            try:
                generator = CostSurfaceGenerator()
                cost_path = generator.process_state(config.state_name)
                click.echo(f"  Cost surface: {cost_path}")
            except Exception as e:
                click.echo(f"  Warning: Could not generate cost surface: {e}")
                click.echo("  Continuing with Euclidean distance...")

        # Step 3: Compute distance
        click.echo("\n[3/5] Computing distance field...")
        calculator = DistanceCalculator(config)
        distance_data = calculator.compute_all(processed)

        # Step 4: Analyze
        click.echo("\n[4/5] Finding unreachable point...")
        analyzer = UnreachabilityAnalyzer(config)
        results = analyzer.analyze_all(distance_data, processed)

        # Step 5: Visualize
        click.echo("\n[5/5] Creating visualizations...")
        visualizer = Visualizer(config)
        outputs = visualizer.visualize_all(distance_data, processed, results)

        # Final summary
        click.echo("\n" + "=" * 60)
        click.echo("PIPELINE COMPLETE!")
        click.echo("=" * 60)
        click.echo(f"\n✓ Most unreachable point in {config.state_name}:")
        click.echo(
            f"    Location: {results['most_unreachable_point']['latitude']:.6f}, "
            f"{results['most_unreachable_point']['longitude']:.6f}")
        click.echo(
            f"    Distance: {results['most_unreachable_point']['distance_km']:.2f} km from nearest road"
        )

        click.echo(f"\n✓ Outputs created:")
        click.echo(f"    Results: {config.get('output.results_file')}")
        for name, path in outputs.items():
            click.echo(f"    {name}: {path}")

        return 0

    except Exception as e:
        click.echo(f"\n✗ Pipeline failed: {e}", err=True)
        import traceback
        traceback.print_exc()
        return 1


@cli.command()
def info():
    """Display project information and configuration."""
    click.echo("=" * 60)
    click.echo("UNREACHABLE MAPPER - PROJECT INFO")
    click.echo("=" * 60)

    try:
        config = get_config()

        click.echo(f"\nConfiguration:")
        click.echo(f"  State: {config.state_name}")
        click.echo(f"  FIPS Code: {config.fips_code}")
        click.echo(f"  CRS: {config.crs}")
        click.echo(f"  Resolution: {config.resolution}m")

        click.echo(f"\nPaths:")
        click.echo(f"  Raw data: {config.get_path('raw_data')}")
        click.echo(f"  Processed data: {config.get_path('processed_data')}")
        click.echo(f"  Outputs: {config.get_path('outputs')}")

        click.echo(f"\nRoad types included:")
        for road_type in config.road_types[:5]:
            click.echo(f"  - {road_type}")
        if len(config.road_types) > 5:
            click.echo(f"  ... and {len(config.road_types) - 5} more")

        click.echo("\nAvailable commands:")
        click.echo("  fetch-data       - Download geospatial data")
        click.echo("  preprocess       - Process and rasterize data")
        click.echo(
            "  cost-surface     - Generate cost surface (if cost-distance enabled)"
        )
        click.echo("  compute-distance - Calculate distance fields")
        click.echo("  find-unreachable - Find most remote location")
        click.echo("  visualize        - Create maps and visualizations")
        click.echo("  run-all          - Execute complete pipeline")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)


def main():
    """Entry point for CLI."""
    try:
        sys.exit(cli(obj={}))
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user")
        sys.exit(130)


if __name__ == '__main__':
    main()
