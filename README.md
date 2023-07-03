# bureau-vote

Ce dépôt contient les travaux conjoints des équipes Etalab et data.gouv.fr, en étroite colaboration avec l'INSEE, au sujet du répertoire électoral unique (REU). Le but de ces travaux était de partir des [données du REU](https://www.data.gouv.fr/fr/datasets/bureaux-de-vote-et-adresses-de-leurs-electeurs/) (adresses de France et leur bureau de vote attribué) pour déterminer des contours des bureaux de vote de France. Une telle donnée permettra à l'avenir - ainsi que pour toutes les élections dont les données sont déjà publiques - d'afficher les résultats des élections à la maille la plus fine qui soit : celle des bureaux de vote.

La méthode choisie est celle des [aires de Voronoï](https://fr.wikipedia.org/wiki/Diagramme_de_Vorono%C3%AF), qui permet de séparer un plan contenant des points d'intérêt (dit germes) en autant de zones autour de ces germes, de sorte que chaque zone enferme un seul germe, et forme l'ensemble des points de plus proches de ce germe que d'aucun autre. D'autres méthodes sont possibles, ainsi que d'autres choix au sein même de cette méthode : il n'y a pas unicité des contours.

## Création des contours

Le notebook python ``Creation_de_contours_a_partir_du_REU.ipynb`` contient toutes les informations permettant de regénérer les contours tels que nous les avons publiés. Les prérequis sont :
- ``python`` et ``jupyter notebook`` installés
- tous les packages listés dans le fichier `requirements.txt`

Il suffit ensuite de dérouler le notebook pour obtenir les contours de la même façon que nous les avons générés. Toutes les fonctions utilisées sont dans ce repo et sont perfectibles : n'hésitez pas à contribuer !

## Travaux préalables

Ce dépôt comprend aussi du code en langage Python permettant de nettoyer et géocoder un extrait (le département de l'Ariège) du format brut des adresses du Répertoire Electoral Unique, ainsi que du code permettant d'afficher sur un fond de carte le standard de publication retenu par l'INSEE [le lien de la documentation sera indiqué ici ultérieurement].

Il s'agit d'un des dépôts de travail en vue de la publication en open data des adresses du Répertoire Electoral Unique, qui n'a pas vocation à être maintenu à l'issue de la diffusion du fichier.

### Visualisation sur un fond de carte du fichier des adresses déjà géocodés, pour n'importe quel département

Déposer les fichiers sources de données à la racine du dépôt, modifier si utile le code en indiquant à la fois le chemin du fichier des adresses et le chemin du fichier de contour des communes (dans notre cas,communes-20220101.shp), indiquer le  créer un environnement virtuel Python3.10 (pratique non nécessaire mais recommandée) puis lancer les commandes :

```
python3.10 -m pip install -r requirements.txt
python3.10 main_atelier.py
```

### Nettoyage, géocodage, visualisation du fichier des adresses, et essais de contours non officiels, pour le département de l'Ariège.

#### Données nécessaires

- Récupérer les données sources
- Récupérer les données des contours des communes ([fichier utilisé dans ce cadre](https://www.data.gouv.fr/fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/))

#### Déploiement

Déposer ces fichiers de données à la racine du dépôt, modifier si utile le code en indiquant le chemin du fichier de contour des communes (dans notre cas,communes-20220101.shp), créer un environnement virtuel Python3.10 (pratique non nécessaire mais recommandée) puis lancer les commandes :

```
python3.10 -m pip install -r requirements.txt
python3.10 main.py <NOM_FICHIER_SOURCE_ADRESSES_REU>
```