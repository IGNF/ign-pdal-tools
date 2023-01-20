# Pdal tools

Crée une image docker qui
- colorise un nuage de point, en allant chercher les images du Geoportail


# Création de l'image docker

`cd docker`

Construit l'image docker

`./build.sh`

Réduit la taille de l'image docker

`./conda_pack.sh`


# Tester

Créer l'environnement Conda

`./script/createCondaEnv.sh`

Les tests unitaires

`./script/test.sh`


# Version

à chaque modification du code, pense à modifier le fichier `VERSION.md`

