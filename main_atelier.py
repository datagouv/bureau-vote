#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import geopandas as gpd
from display import *
import re

# path of the address file
addresses_path = "extrait_fichier_adresses_REU.parquet"
commune_shapes_path = "communes-20220101.shp"

# choose an example of departement
DEP = "83"
# for this departement, determine the radio of addresses you want to plot
RATIO = 0.1 # 0 <= RATIO <= 1

# ## Loading the address file, and a file with the shape of communes.
# ##### Warning: these files are heavy

df = pd.read_parquet(addresses_path)
communes_france = gpd.read_file(commune_shapes_path)[["geometry", "insee"]].dropna()


# ### The code below creates an (unofficial) identifier of bureau de vote. We use it in this code mostly for displaying purpose


def prepare_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare not-official `id_bv` (integers) column, under the assumption there is less than 10000 bv per city

    Args:
        df (pd.DataFrame): a dataframe including columns "Code_BV" and "result_citycode"

    Returns:
        pd.DataFrame: a dataframe similar to the input, with a supplementary column "id_bv" (integers) unique for every bureau de vote
    """
    assert ("code_bv" in df.columns) and (
        "code_commune_ref" in df.columns
    ), "There is no identifiers for bureau de vote"
    df_copy = df.copy()

    def prepare_id_bv(row):
        """
        Combine the unique id of a city (citycode) and the number of the bureau de vote inside the city to compute a nationalwide id of bureau de vote

        Args:
            row (_type_): _description_

        Returns:
            id_bv: integer serving as unique id of a bureau de vote
        """
        max_bv_per_city = 10000  # assuming there is always less than this number of bv in a city. This is important to grant the uniqueness of id_bv
        max_code_commune = 10**5
        try:
            code_bv = int(row["code_bv"])
        except:
            # keep as Code_BV the first number found in the string (if there is one)
            found = re.search(r"\d+", row["code_bv"])
            if found:
                code_bv = int(found.group())
            else:
                code_bv = max_bv_per_city  # this code will indicate parsing errors but won't raise exception
        try:
            code_commune = int(row["code_commune_ref"])
        except:
            found = re.search(r"\d+", row["code_commune_ref"])
            if found:
                code_commune = int(found.group())
            else:
                code_commune = max_code_commune
        return max_bv_per_city * code_commune + code_bv

    df_copy["id_bv"] = df_copy.apply(prepare_id_bv, axis=1)
    return df_copy


# add this unofficiel "id_bv" field id to recognize and to determine the color of id fields
df_prepared = prepare_ids(df)

communes_dep = communes_france[communes_france.insee.str.startswith(str(DEP))]

df_dep = df_prepared[df_prepared.dep_bv==DEP].sample(frac=RATIO, random_state=0)


r = display_addresses(addresses=df_dep, communes=communes_dep)
r.to_html(f"scatterplot_{DEP}_layer_ratio_{RATIO}.html")

r_voronoi = display_bureau_vote_shapes(addresses=df_dep, communes=communes_dep, mode="voronoi")
r_voronoi.to_html(f"voronoi_{DEP}_layer_ratio_{RATIO}.html")



