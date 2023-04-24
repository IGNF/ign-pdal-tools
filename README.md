# Pdal tools

Bibliothèque python qui réalise des opérations simples en utilisant pdal:
* colorisation
* stitching
* standardisation

La lib peut être utilisée dans une image docker (cf. dossier `./docker`)

# Opérations
## Colorisation

* `color.py`: colorise un nuage de point, en allant chercher les images du Geoportail

## Stitching

* `las_clip.py`: découpe un fichier las d'après une bounding box
* `las_merge.py`: merge un las avec ses voisins d'après les noms de fichiers
* `las_add_buffer.py`: ajoute un buffer à un fichier las avec les données de ses voisins (d'après les noms de fichiers)

**WARNING**: Pour `las_merge.py` et `las_add_buffer.py`, les noms de fichiers sont parsés pour trouver les voisins.
Le format de nom de fichiers attendu est : `{prefix1}_{prefix2}_{xcoord}_{ycoord}_{postfix})}`, eg. `Semis_2021_0770_6278_LA93_IGN69.laz`

## Standardisation

* `standardize_format.py`: réécrit un fichier las dans un format standard (cf. code)
* `count_occurences`: pour un attribut donné (développé en premier
lieu pour de la classification), compte les occurences de chaque valeur sur un
ensemble de fichiers las.
    * `count_occurences_for_attribute.py`: compte les occurences sur un ou plusieurs fichiers et les
et les sauve dans un fichier json
    * `merge_occurences_counts.py` : permet d'assembler des comptes (fichiers json) en un seul fichier
de compte d'occurences (utilisé en cas de parallélisation)
* `replace_attribute_in_las.py`: à partir d'un fichier json contenant un tableau de
correspondances, remplace les occurences de chaque valeur par la valeur associée
dans le tableau.

# Installation / Usage

## Bibliothèque

Les opérations pour générer la bibliothèque python et la déployer sur pypi sont réalisées via le fichier Makefile à la racine du projet:
* `make build` : construit la bibliothèque
* `make install` : installe la bibliothèque de façon éditable
* `make deploy` : déploie sur pipy

## Image docker


Construit l'image docker

`make docker-build`

Réduit la taille de l'image docker.

Mais pour l'instant, on ne l'utilise pas car il y des soucis avec Proj. TODO: Identifier à quel appel de code on a ce pb.


`cd docker`
`./conda_pack.sh`


Déploie l'image docker sur le nexus ign

`./deploy.sh`

## Tester

Créer l'environnement Conda

`./script/createCondaEnv.sh`

Les tests unitaires

`./script/test.sh`


## Version

à chaque modification du code, pense à modifier le fichier `pdaltools/_VERSION.py`

