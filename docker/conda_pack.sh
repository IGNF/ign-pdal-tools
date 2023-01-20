# reduit la taille de l'image lidar_hd/lidar_express:latest d'environ 1Go
PROJECT_NAME=lidar_hd/lidar_express
VERSION=`cat ../VERSION.md`

docker build --no-cache -t $PROJECT_NAME ./conda_pack
docker tag $PROJECT_NAME $PROJECT_NAME:$VERSION
