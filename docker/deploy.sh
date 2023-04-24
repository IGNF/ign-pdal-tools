# Déploie l'image docker sur le repo Nexus de l'IGN.
# Ce script s'utilise dans le dossier docker
# Usage: ./deploy.sh
# Ensuite, il faut entrer le mot de passe de l'utilisateur svc_lidarhd
REGISTRY=docker-registry.ign.fr
PROJECT_NAME=lidar_hd/pdal_tools
VERSION=`cd .. && python -m pdaltools._version`

docker login docker-registry.ign.fr -u svc_lidarhd
docker tag $PROJECT_NAME:$VERSION $REGISTRY/$PROJECT_NAME:$VERSION
docker push $REGISTRY/$PROJECT_NAME:$VERSION
