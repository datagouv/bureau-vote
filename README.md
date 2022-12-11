# bureau-vote

Ce dépôt comprend à la fois du code en langage Python permettant de nettoyer et géocoder un extrait (le département de l'Ariège) du format brut des adresses du Répertoire Electoral Unique, ainsi que du code permettant d'afficher sur un fond de carte le standard de publication retenu par l'INSEE [le lien de la documentation sera indiqué ici ultérieurement].

Il s'agit d'un des dépôts de travail en vue de la publication en open data des adresses du Répertoire Electoral Unique, qui n'a pas vocation à être maintenu à l'issue de la diffusion du fichier.

## Visualisation sur un fond de carte du fichier des adresses déjà géocodés, pour n'importe quel département

Déposer les fichiers sources de données à la racine du dépôt, modifier si utile le code en indiquant à la fois le chemin du fichier des adresses et le chemin du fichier de contour des communes (dans notre cas,communes-20220101.shp), créer un environnement virtuel Python3.10 (pratique non nécessaire mais recommandée) puis lancer les commandes :

```
python3.10 install -r requirements.txt
python3.10 -m pip main_atelier.py
```

## Nettoyage, géocodage, visualisation du fichier des adresses, et essais de contours non officiels, pour le département de l'Ariège.

### Données nécessaires

- Récupérer les données sources
- Récupérer les données des contours des communes ([fichier utilisé dans ce cadre](https://www.data.gouv.fr/fr/datasets/decoupage-administratif-communal-francais-issu-d-openstreetmap/))

### Déploiement

Déposer ces fichiers de données à la racine du dépôt, modifier si utile le code en indiquant le chemin du fichier de contour des communes (dans notre cas,communes-20220101.shp), créer un environnement virtuel Python3.10 (pratique non nécessaire mais recommandée) puis lancer les commandes :

```
python3.10 install -r requirements.txt
python3.10 -m pip main.py <NOM_FICHIER_SOURCE_ADRESSES_REU>
```


## Maintenance du dépôt

La maitenance de ce dépôt de travail est assurée par l'équipe Lab IA de la Direction Interministérielle du Numérique (DINUM) :

lab-ia@data.gouv.fr
