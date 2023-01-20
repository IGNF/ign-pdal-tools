# construit lidar_hd/lidar_express
PROJECT_NAME=lidar_hd/lidar_express
VERSION=`cat ../VERSION.md`

docker build --no-cache -t $PROJECT_NAME -f Dockerfile .
docker tag $PROJECT_NAME $PROJECT_NAME:$VERSION
