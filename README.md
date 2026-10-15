# ign-pdal-tools

Python utilities for working with LiDAR point clouds and LAS/LAZ files with [PDAL](https://pdal.io/). The tools were developed for the [LidarHD project](https://www.ign.fr/institut/lidar-hd-vers-une-nouvelle-cartographie-3d-du-territoire) at [IGN](https://www.ign.fr). The library is maintained to meet the team's needs and may change over time.

## What it does

### Imagery

* [color.py](pdaltools/color.py) adds RGB, infrared, or vegetation-index values to a point cloud using imagery from Geoplateforme or a local raster.
* [download_image.py](pdaltools/download_image.py) downloads georeferenced GeoTIFF imagery from Geoplateforme and combines tiled requests for large extents.

### Point-cloud editing

* [add_points_in_pointcloud.py](pdaltools/add_points_in_pointcloud.py) adds vector points or samples along vector lines to a LAS/LAZ file. It supports an altitude attribute for 2D input and configurable classification and spacing.
* [las_clip.py](pdaltools/las_clip.py) crops a LAS/LAZ file to a 2D bounding box.
* [replace_area_in_pointcloud.py](pdaltools/replace_area_in_pointcloud.py) replaces points within areas defined by a vector file with points from another cloud.
* [las_add_extra_dims_from_las.py](pdaltools/las_add_extra_dims_from_las.py) copies missing or selected dimensions from a donor file by matching points. It also supports processing matching filenames in two directories.
* [las_remove_dimensions.py](pdaltools/las_remove_dimensions.py) removes dimensions, and [las_rename_dimension.py](pdaltools/las_rename_dimension.py) renames them.
* [replace_attribute_in_las.py](pdaltools/replace_attribute_in_las.py) maps values in a LAS/LAZ attribute using a JSON correspondence map.

### LAS/LAZ information and quality checks

* [las_info.py](pdaltools/las_info.py) reads metadata, bounds, tile origins, and EPSG information.
* [pcd_info.py](pdaltools/pcd_info.py) provides tile-origin utilities for point-cloud coordinate bounds.
* [check_las.py](pdaltools/check_las.py) checks whether PDAL can read a file, with an optional retry and a decorator for validating generated files.
* [las_comparison.py](pdaltools/las_comparison.py) compares selected or all dimensions in two files, with optional numeric tolerances.
* [count_occurences](pdaltools/count_occurences) counts attribute values across LAS/LAZ files. Use [count_occurences_for_attribute.py](pdaltools/count_occurences/count_occurences_for_attribute.py) to create JSON counts and [merge_occurences_counts.py](pdaltools/count_occurences/merge_occurences_counts.py) to combine results.
* [estimate_and_compare_trajectory.py](pdaltools/estimate_and_compare_trajectory.py) estimates a sensor trajectory from multiple returns and can compare it with a reference trajectory.

### Format and pipeline utilities

* [standardize_format.py](pdaltools/standardize_format.py) rewrites a LAS/LAZ file in the library's standard format.
* [run_pdal_pipeline.py](pdaltools/run_pdal_pipeline.py) runs a PDAL pipeline provided as JSON against an input file and writes the output file.
* [unlock_file.py](pdaltools/unlock_file.py) works around malformed TerraSolid LAS 1.4 files with point formats 6-10 that lack the global-encoding WKT flag.
* [create_random_laz.py](pdaltools/create_random_laz.py) generates synthetic LAZ files with configurable point format, CRS, classifications, and extra dimensions for testing.

### Neighboring tiles

* [las_merge.py](pdaltools/las_merge.py) merges a tile with its neighboring tiles.
* [las_add_buffer.py](pdaltools/las_add_buffer.py) adds points from neighboring tiles along a tile's border.
* Both tools use filenames to determine tile extents and locate neighbors. The expected pattern is `{prefix1}_{prefix2}_{xcoord}_{ycoord}_{postfix}`, for example `Semis_2021_0770_6278_LA93_IGN69.laz`. By default, coordinates are in kilometers and tiles are 1 km by 1 km.

## Python examples

Read LAS metadata:

```python
from pdaltools import las_info

metadata = las_info.las_info_metadata("input.laz")
```

Infer a tile origin from point-cloud bounds:

```python
from pdaltools import las_info, pcd_info

metadata = las_info.las_info_metadata("input.laz")
bounds = las_info.get_bounds_from_header_info(metadata)
origin_x, origin_y = pcd_info.infer_tile_origin(*bounds, tile_width=1000)
```

## Install and use

Install from PyPI:

```sh
pip install ign-pdal-tools
```

For development, `make install` creates or updates the `pdaltools` mamba environment from [environment.yml](environment.yml).

To build and run the tools in Docker, see [Dockerfile](Dockerfile) and the Makefile targets below.

## Development

* Create or update the environment: `make install`
* Run the standard test suite: `make testing` (excludes tests marked `geopf`)
* Run all tests, including `geopf` tests: `make testing_full`
* Install pre-commit hooks: `make install-precommit`
* Record changes in [CHANGELOG.md](CHANGELOG.md) and update the version in [pdaltools/_version.py](pdaltools/_version.py) when appropriate.

Build and package commands are defined in the [Makefile](Makefile):

* `make build` builds the Python package.
* `make deploy` uploads the built package to PyPI.
* `make docker-build` builds the Docker image.
* `make docker-test` runs the tests in Docker.
* `make docker-build-custom-pdal` builds an image with the custom PDAL version configured in the Makefile.