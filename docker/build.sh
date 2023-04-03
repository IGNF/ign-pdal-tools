# construit lidar_hd/pdal_tools
PROJECT_NAME=lidar_hd/pdal_tools
VERSION=`cd .. && python -m pdaltools._version`

docker build --no-cache -t $PROJECT_NAME -f Dockerfile .
docker tag $PROJECT_NAME $PROJECT_NAME:$VERSION
