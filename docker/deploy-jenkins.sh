# Ce script deploie l'image docker sur le repo Nexus de l'IGN.
# Il s'utilise à la racine du projet.
# Usage: ./docker/deploy-jenkins.sh "mot-de-passe"
# Le mot de passe est celui de l'utilisateur svc_lidarhd
REGISTRY=docker-registry.ign.fr
PROJECT_NAME=lidar_hd/pdal_tools
VERSION=`python pdaltools/_version.py`

docker login docker-registry.ign.fr -u svc_lidarhd -p $1 && \
docker tag $PROJECT_NAME:$VERSION $REGISTRY/$PROJECT_NAME:$VERSION && \
docker push $REGISTRY/$PROJECT_NAME:$VERSION
