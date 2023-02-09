# Pdal tools

Crée une image docker qui réalise des opérations simples en utilisant pdal:
* colorisation
* stitching

## Colorisation

* `color.py`: colorise un nuage de point, en allant chercher les images du Geoportail

## Stitching

* `las_clip.py`: découpe un fichier las d'après une bounding box
* `las_merge.py`: merge un las avec ses voisins d'après les noms de fichiers
* `las_add_buffer.py`: ajoute un buffer à un fichier las avec les données de ses voisins (d'après les noms de fichiers)

**WARNING**: Pour `las_merge.py` et `las_add_buffer.py`, les noms de fichiers sont parsés pour trouver les voisins.
Le format de nom de fichiers attendu est : `{prefix1}_{prefix2}_{xcoord}_{ycoord}_{postfix})}`, eg. `Semis_2021_0770_6278_LA93_IGN69.laz`

# Installation / Usage
## Création de l'image docker

`cd docker`

Construit l'image docker

`./build.sh`

Réduit la taille de l'image docker

`./conda_pack.sh`


## Tester

Créer l'environnement Conda

`./script/createCondaEnv.sh`

Les tests unitaires

`./script/test.sh`


## Version

à chaque modification du code, pense à modifier le fichier `VERSION.md`

