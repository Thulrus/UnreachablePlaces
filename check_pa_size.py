import geopandas as gpd
import numpy as np

# Load Pennsylvania boundary
pa = gpd.read_file('data/raw/pennsylvania_boundary.geojson')
pa_proj = pa.to_crs('EPSG:5070')

# Get bounds
minx, miny, maxx, maxy = pa_proj.total_bounds

# Calculate dimensions at 250m resolution
resolution = 250
width = int(np.ceil((maxx - minx) / resolution))
height = int(np.ceil((maxy - miny) / resolution))

print(f"Pennsylvania projected bounds:")
print(f"  X: {minx:.0f} to {maxx:.0f} ({maxx-minx:.0f} m)")
print(f"  Y: {miny:.0f} to {maxy:.0f} ({maxy-miny:.0f} m)")
print(f"\nRaster dimensions at 250m:")
print(f"  Width: {width:,} pixels")
print(f"  Height: {height:,} pixels")
print(f"  Total: {width*height:,} pixels ({width*height/1e6:.1f} million)")
print(f"\nEstimated memory (float64):")
print(f"  Per array: {width*height*8/1024**2:.1f} MB")
print(f"  5 arrays: {width*height*8*5/1024**2:.1f} MB")
print(f"  10 arrays: {width*height*8*10/1024**3:.2f} GB")
