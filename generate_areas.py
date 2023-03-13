#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import geopandas as gpd
from display import *
import re

# display just a departement/drom/com
DEP_LIST = ["0"+str(i) for i in range(1,10)]+[str(i) for i in range(10,19)]+["2A","2B"]+[str(i) for i in range(21,96)] + [str(i) for i in range(971,977)]
#DEP_LIST = ["01", "83"]
COMPUTE_BV_BORDERS = False
# path of the address file

commune_shapes_path = "communes-20220101.shp"
communes_france = gpd.read_file(commune_shapes_path)[["geometry", "insee"]].dropna()

for DEP in DEP_LIST:
    communes_dep = communes_france[communes_france.insee.str.startswith(str(DEP))]

    addresses_path = f"parquet/table_{DEP}.parquet"

    # for this departement, determine the radio of addresses you want to plot
    RATIO = 0.4 # 0 <= RATIO <= 1

    # ## Loading the address file, and a file with the shape of communes.
    # ##### Warning: these files are heavy

    df = pd.read_parquet(addresses_path)
    # if id_brut_bv is not None, condition below should always be True
    if "id_bv" not in df.columns:
        pat = re.compile(r"\d+")
        df["id_bv"] = df["id_brut_bv"].apply(lambda row : int("".join(re.findall(pat, row))))


    print(f"LOAD data in memory: {len(df)} rows")


    # ### The code below creates an (unofficial) identifier of bureau de vote. We use it in this code mostly for displaying purpose

    # add this unofficiel "id_bv" field id to recognize and to determine the color of id fields


    #df_dep = df[df.dep_bv==DEP].sample(frac=RATIO, random_state=0)
    os.makedirs("html/dep", exist_ok=True)
    os.makedirs("html/bv", exist_ok=True)

    if COMPUTE_BV_BORDERS:
        for raw_id_bv in df.id_brut_bv.unique():
            df_bv = df[df.id_brut_bv==raw_id_bv]
            r_bv = display_addresses(addresses=df_bv, communes=communes_dep)
            r_bv.to_html(f"html/bv/scatterplot_bv_{raw_id_bv}.html")

            r_voronoi_bv = display_bureau_vote_shapes(addresses=df_bv, communes=communes_dep, mode="voronoi")
            r_voronoi_bv.to_html(f"html/bv/voronoi_bv_{raw_id_bv}.html")

        
    df_dep = df.sample(frac=RATIO, random_state=0)
    
    print("Going to display addresses")
    r = display_addresses(addresses=df_dep, communes=communes_dep)
    r.to_html(f"html/dep/scatterplot_{DEP}_layer_ratio_{RATIO}.html")

    r_voronoi = display_bureau_vote_shapes(addresses=df_dep, communes=communes_dep, mode="voronoi")
    r_voronoi.to_html(f"html/dep/voronoi_{DEP}_layer_ratio_{RATIO}.html")
    


