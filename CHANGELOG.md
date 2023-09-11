# dev

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
