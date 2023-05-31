# dev

# v0.5.6
- makefile: execute la règle "clean" avant le "build" de la lib. Comme ça l'integration continue supprime les anciennes versions de la lib.

# v0.5.5
- standardisation: offset à 0

# v0.5.4
- standardisation: fix warnings (vus avec lasinfo). Utilise las2las pour sauvegarder à nouveau le LAS.

# v0.5.3
- add_buffer / merge : use filename to get tile extent

# v0.5.2 :
- script jenkins: gestion des erreurs
- docker : hérite d'une image basée sur Mamba au lieu de Conda (Mamba est plus rapide pour récupérer les dépendances)
- integration continue (jenkins): contruit l'image docker et publie sur le Nexus quand on merge dans la branche master

# v0.5.1
- standardisation : parallélisation du compte des occurences

# v0.5.0
- docker: option no-capture-output
- standardisation : ajout d'un module permettant de fixer le format d'un fichier las/laz
- standardisation : ajout d'un module permettant de compter les occurences d'un attribut dans un ensemble de fichiers las/laz
- standardisation : ajout d'un module permettant de remplacer les valeurs d'un attribut dans un fichier las/laz

# v0.4.2
standardisation
stitching
