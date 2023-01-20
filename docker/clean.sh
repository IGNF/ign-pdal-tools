# supprime toutes les images contenant lidarexpress
docker rmi -f `docker images | grep lidarexpress | tr -s ' ' | cut -d ' ' -f 3`
docker rmi -f `docker images -f "dangling=true" -q`
