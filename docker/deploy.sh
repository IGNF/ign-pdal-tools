# deploy sur le registry avec la bonne version
REGISTRY=docker-registry.ign.fr
PROJECT_NAME=lidar_hd/pdal_tools
VERSION=`cd .. && python -m pdaltools._version`

docker login docker-registry.ign.fr -u svc_lidarhd
docker tag $PROJECT_NAME:$VERSION $REGISTRY/$PROJECT_NAME:$VERSION
docker push $REGISTRY/$PROJECT_NAME:$VERSION
