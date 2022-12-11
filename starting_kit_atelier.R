#############################################################################
#            Atelier sur les adresses du REU : starting kit                 #
#############################################################################

################################
# Imports
################################

##### Packages

library(arrow)
library(dplyr)
library(data.table)
library(magrittr)
library(sf)
library(ggplot2)
library(viridis)

##### Données

extrait_adressesREU <- arrow::read_parquet(
  "extrait_fichier_adresses_REU.parquet"
) %>% setDT()

################################
# Quelques manipulations
################################

##### Sélectionner un échantillon du fichier

sample_REU <- extrait_adressesREU[sample(.N, 5e5)]

##### Convertir les coordonnées Lambert de Geoloc en GPS

adressesREU_geoloc <- copy(extrait_adressesREU) %>%
  select(X, Y) %>%
  st_as_sf(
    coords = c("X", "Y"), 
    crs = 2154,
    na.fail = FALSE
  ) %>% 
  st_transform(crs = 4326)

##### Convertir les coordonnées de la BAN en GPS

adressesREU_BAN <- copy(extrait_adressesREU) %>%
  select(latitude, longitude) %>%
  st_as_sf(
    coords = c("longitude", "latitude"), 
    crs = 4326,
    na.fail = FALSE
  )

################################
# Statistiques descriptives et nouveaux champs
################################

##### Observer les quantiles de score de pertinence pour la BAN

quantiles_geo_score <- quantile(extrait_adressesREU$geo_score, seq(0, 1, 0.2),
                                na.rm = TRUE)


##### Générer des intervalles pour le score de qualité de la BAN

extrait_adressesREU[,`:=`(categorie_geo_score = cut(
  geo_score, 5, ordered_result = TRUE))]

##### Générer des labels qualité pour Geoloc plus explicites

extrait_adressesREU[, `:=`(
  label_QUALITE_XY = fcase(
    QUALITE_XY == 11, "Voie Sûre, Numéro trouvé",
    QUALITE_XY == 12, "Voie Sûre, Position aléatoire dans la voie",
    QUALITE_XY == 21, "Voie probable, Numéro trouvé",
    QUALITE_XY == 22, "Voie probable, Position aléatoire dans la voie",
    QUALITE_XY == 33, "Voie inconnue, Position aléatoire dans la commune"
  ) %>%
    factor(
      levels = c(
        "Voie Sûre, Numéro trouvé",
        "Voie probable, Numéro trouvé",
        "Voie Sûre, Position aléatoire dans la voie",
        "Voie probable, Position aléatoire dans la voie",
        "Voie inconnue, Position aléatoire dans la commune"
      ),
      ordered = TRUE
    )
)
]

##### Générer les distances entre les positions renvoyées par la BAN et par Geoloc

extrait_adressesREU[, `:=`(
  distance = st_distance(
    x = adressesREU_geoloc,
    y = adressesREU_BAN,
    by_element = TRUE
  )
  )]

################################
# Visualisation des différences BAN / Geoloc
################################

##### Générer la proportion d'adresses pour lesquels les 2 référentiels renvoient
##### des localisations à moins de 100m, 200m, ... l'une de l'autre
##### en fonction des indicateurs de qualité

prop_normalisations_proches <- extrait_adressesREU[, .(
  nb_adresses  = .N,
  # part_10moins   = mean(distance <= units::set_units(10, m), na.rm = TRUE),
  # part_20moins   = mean(distance <= units::set_units(20, m), na.rm = TRUE),
  # part_50moins   = mean(distance <= units::set_units(50, m), na.rm = TRUE),
  part_100moins  = mean(distance <= units::set_units(100, m), na.rm = TRUE),
  part_200moins  = mean(distance <= units::set_units(200, m), na.rm = TRUE)
  # part_500moins  = mean(distance <= units::set_units(500, m), na.rm = TRUE),
  # part_1000moins = mean(distance <= units::set_units(1000, m), na.rm = TRUE)
), by = .(label_QUALITE_XY, QUALITE_XY, categorie_geo_score)][
  order(QUALITE_XY, categorie_geo_score)]

##### Visualiser les proportions calculées ci-dessus

ggplot(prop_normalisations_proches[!is.na(QUALITE_XY) & !is.na(categorie_geo_score)]) + 
  geom_bar(
    aes(
      x = categorie_geo_score, y = part_100moins, fill = label_QUALITE_XY
    ), position = "dodge", stat = "identity"
  ) + 
  labs(
    x = "Score de qualité BAN",
    y = "Proportion de distance <100m",
    fill = "Qualité de Geoloc"
  ) +
  scale_fill_viridis_d() +
  scale_y_continuous(labels = scales::percent_format()) +
  theme(legend.position = "bottom") +
  guides(
    fill = guide_legend(
      title.hjust = 0.5,
      title.position = "top", 
      nrow = 3
    )
  )

################################
# Les contours
################################


