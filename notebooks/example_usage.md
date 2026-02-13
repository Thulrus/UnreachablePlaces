# Example: Using Unreachable Mapper API

This notebook demonstrates how to use the Unreachable Mapper as a Python API.

## Import modules

```python
from src.config import Config, get_config
from src.fetch import DataFetcher
from src.preprocess import DataPreprocessor
from src.distance import DistanceCalculator
from src.analyze import UnreachabilityAnalyzer
from src.visualize import Visualizer

import matplotlib.pyplot as plt
%matplotlib inline
```

## Configure the project

```python
# Use default config
config = get_config()

print(f"State: {config.state_name}")
print(f"Resolution: {config.resolution}m")
print(f"CRS: {config.crs}")
```

## Step 1: Fetch Data

```python
fetcher = DataFetcher(config)
data = fetcher.fetch_all()

print(f"Boundary: {len(data['boundary'])} features")
print(f"Roads: {len(data['roads'])} features")
```

## Step 2: Preprocess

```python
preprocessor = DataPreprocessor(config)
processed = preprocessor.preprocess_all(data)

print(f"Road mask shape: {processed['road_mask'].shape}")
print(f"Road coverage: {processed['road_mask'].sum() / processed['road_mask'].size * 100:.2f}%")
```

## Step 3: Compute Distance Field

```python
calculator = DistanceCalculator(config)
distance_data = calculator.compute_all(processed)

import numpy as np
print(f"Max distance: {np.nanmax(distance_data['distance_field']) / 1000:.2f} km")
print(f"Mean distance: {np.nanmean(distance_data['distance_field']) / 1000:.2f} km")
```

## Step 4: Find Unreachable Point

```python
analyzer = UnreachabilityAnalyzer(config)
results = analyzer.analyze_all(distance_data, processed)

point = results['most_unreachable_point']
print(f"Most unreachable point:")
print(f"  Lat/Lon: {point['latitude']:.6f}, {point['longitude']:.6f}")
print(f"  Distance: {point['distance_km']:.2f} km")
```

## Step 5: Visualize

```python
visualizer = Visualizer(config)
outputs = visualizer.visualize_all(distance_data, processed, results)

for name, path in outputs.items():
    print(f"{name}: {path}")
```

## View Results

```python
# Display the static map
from IPython.display import Image, display
display(Image(filename=str(outputs['static_map'])))
```

```python
# Display the interactive map
from IPython.display import IFrame
IFrame(src=str(outputs['interactive_map']), width=800, height=600)
```

## Custom Analysis

You can also work with the data directly:

```python
import geopandas as gpd
from shapely.geometry import Point

# Get top 10 points
top_10 = results['top_10_unreachable']

# Create a GeoDataFrame
points = [Point(p['longitude'], p['latitude']) for p in top_10]
gdf = gpd.GeoDataFrame(
    top_10,
    geometry=points,
    crs='EPSG:4326'
)

# Plot
fig, ax = plt.subplots(figsize=(10, 8))
processed['boundary'].to_crs('EPSG:4326').plot(ax=ax, facecolor='none', edgecolor='black')
gdf.plot(ax=ax, color='red', markersize=gdf['rank'].apply(lambda x: 200/x))
plt.title('Top 10 Most Unreachable Points')
plt.show()
```

## Experiment with Different Resolutions

```python
# Try higher resolution (slower but more accurate)
config.config['raster']['resolution'] = 100

# Re-run preprocessing and distance calculation
processed_hires = preprocessor.preprocess_all(data)
distance_hires = calculator.compute_all(processed_hires)
results_hires = analyzer.analyze_all(distance_hires, processed_hires)

print(f"High-res max distance: {results_hires['most_unreachable_point']['distance_km']:.2f} km")
```

---

For more examples, see the README.md file.
