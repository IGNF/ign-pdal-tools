# 1.12.2
- comment a test which doesn't work because a fix in GPF

# 1.12.1
- las_comparison : update return value with number of different points and percentage of different points
- standardize_format: 
  - add test for dimension renaming 
  - do not use las2las anymore: was used to remove lasinfo Warning which has been fixed on pdal side

# 1.12.0
- [new feature] create_random_las : create small random las (for test and orther stuff)
- [fix] add_points_to_pointcloud: fix case with tiles that don't contain lines from which to add points.
- [new feature] las_comparison: new tool to compare the attributes of 2 las files with points having the same {x, y, z, gps_time}

# 1.11.1
- fix Dockerfile for custom PDAL compilation: update custom branch, update python-plugins to version 1.6.5

# 1.11.0
- standardize_format: add dimension renaming option

# 1.10.0
- custom PDAL: fix CI for cicd_full (build docker image with custom PDAL, and skip custom PDAL test for local pytest)
- las_rename_dimension: new tool to rename one or many dimensions

# 1.9.1
- las_add_points_to_pointcloud: Fix add points to LAS (use PDAL instead of Laspy)

# 1.9.0
- custom PDAL: in the docker image, compile custom PDAL (waiting for PDAL 2.9)

# 1.8.1
- add_points_in_pointcloud: fix case when there is no points to add in the las file extent (copy input file to the output)
- color: temporarily disable tests on no_data values in downloaded images

# 1.8.0
- remove add_points_in_las.py (replaced by add_points_in_pointcloud.py)
- colorization :
  - orthophotos can be downloaded by blocks and merged, in order for requests to match the maximum download size of the geoplateforme.
  - force image min/max to match full pixel values

# 1.7.11
- Fix bug  "add_points_in_pointcloud.py" : keep all dimension (ex. intensity, etc.) from input pointcloud

# 1.7.10
- Add function to add lines 2.5D (.GeoJSON or .shp) in pointcloud (.LAZ / .LAS)
- Update function to add points (.GeoJSON) in pointcloud: let Z be parametrized

# 1.7.9
- color: handle all request exceptions

# 1.7.8
- Update dependency versions
- make count_occurences usable as a package
- add_points_to_pointcloud does not raise an error when there is no point in the tile

# 1.7.7
- Add parameters and "main" to function "add points (.GeoJSON) in pointcloud (.LAZ / .LAS)"

# 1.7.6
- Add function to add points (.GeoJSON) in pointcloud (.LAZ / .LAS)

# 1.7.5
- Add tools to get tile origin from various point cloud data types (las file, numpy array, min/max values)
- Raise more explicit error when looking a tile origin when the data width is smaller than the buffer size
- Add method to add points from vector files (ex : shp, geojson, ...) inside las

# 1.7.4
- Color: fix images bbox to prevent in edge cases where points were at the edge of the last pixel
- Add possibility to remove points of some classes in standardize

# 1.7.3
- Add method to get a point cloud origin

# 1.7.2
- Add possibility to select extra dimensions to keep in standardization

# 1.7.1
Same as 1.7.0 (new tag needed to publish on pypi due to incorrect package handling)

# 1.7.0
- las_remove_dimension: new tool to remove one or many dimensions
- deploy on ghcr.io instead of dockerhub
- Add tools to run functions on buffered las:
  - update create_las_with_buffer to enable saving which points are from the central las on a new dimension
  - add a remove_points_from_buffer to remove the points that have this new dimension not set to 1
  - add a decorator to run a function on a buffered las and return an output las only with the points from the original input

# 1.6.0
- color: choose streams for RGB colorization, and IRC colorization (doc https://geoservices.ign.fr/services-web-experts-ortho)
- color: detect white images.

# 1.5.2
- refactor tool to propagate header infos from one pipeline to another to use it by itself

# 1.5.1
- fix add_buffer: propagate header infos from input to the output
- update pdal.Writer params to make sure input format is forwarded except for the specified parameters
- add test for colorization with epsg != 2154

# 1.5.0
- switch colorisation source from Geoportail to Geoplateforme
- use absolute value comparison in tests
- linting / add pre-commits
- upgrade python version to 3.11
- replace `pdal info --metadata` subprocess by a python command (used in the `color` module in particular)

# 1.4.1
- fix copy_and_hack_decorator (was not returning the decorated function output)

# 1.4.0
- count_occurences / replace_value: add copy_and_hack decorator to run on tscan output files
- Update to pdal 2.6+ to better handle classification values and flags in replace_attribute_in_las
(was treating values over 31 as {classification under 31 + flag} even when saving to LAS 1.4)

# 1.3.1
- fix color: ensure that tmp orthoimages are deleted after use by using the namedTemporaryFile properly.

# 1.3.0
- color: support colorization for <0.2m clouds (including height=0/width=0)
- color: ceil width/height to have a bbox that contains all points

# 1.2.1
- fix cicd_full github action: deployment was triggered on pushing to dev instead of master only

# 1.2.0
- color: keep downloaded orthoimages by returning them to make them stay in execution scope

# 1.1.1
- unlock: fix main
- tests:
  - add geoportail marker to skip tests relying on geoportail (they are now played on PR to the master branch only)
  - bugfix on standardization test file path

# 1.1.0
- standardization: handle malformed laz input ("Global encoding WKT flag not set for point format 6 - 10")
- color: extract unlock module from colorization and rename colorization function

# 1.0.0
- first public version
- docker: Use staged build to reduce docker image size
- add continuous integration with github actions

# v0.5.6
- makefile: run "clean" before "build" (build the library) in order for the CI to remove old versions of the library

# v0.5.5
- standardisation: set offset to 0

# v0.5.4
- standardisation: fix warnings displayed when using lasinfo (LasTools). Use las2las to save the las again

# v0.5.3
- add_buffer/merge: use filename to get tile extent

# v0.5.2 :
- jenkins script: handle errors
- docker: inherit of an image based on Mamba instead of Conda (mamba is faster than conda to fetch dependencies)
- continuous integration (jenkins): build the docker image and publish on our private repo when merging on master

# v0.5.1
- standardisation : parallelize occurences count

# v0.5.0
- docker: option no-capture-output
- standardisation : add a module to enforce format for a las/laz file
- standardisation : add a module to count occurences for an attribute in a batch of las/laz file
- standardisation : add a module to replace the values of an attribute in a las/laz file

# v0.4.2
standardisation
stitching
