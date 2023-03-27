#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely import Polygon
from geo import build_geojson_point, get_clipped_voronoi_shapes
pd.set_option('display.max_columns', None)

# display just a departement/drom/com
DEP_LIST = ["0"+str(i) for i in range(1,10)]+[str(i) for i in range(10,20)]+["2A","2B"]+[str(i) for i in range(21,96)] + [str(i) for i in range(971,977)]
# DEP_LIST = ["83", "75"]
# path of the address file
# commune_shapes_path = r"C:\Users\Dinum\Documents\Projets\Elections\communes-20220101-shp\communes-20220101.shp"
# communes_france = gpd.read_file(commune_shapes_path)[["geometry", "insee"]].dropna()
# dans le fichier communes-5m.geojson, arrondissements + dep 975
commune_shapes_path = r"C:\Users\Dinum\Documents\Projets\Elections\communes-5m.geojson"
communes_france = gpd.read_file(commune_shapes_path)
communes_france = communes_france.rename({'code':'insee'}, axis=1)[['insee', 'geometry']]

for DEP in DEP_LIST:
    print(DEP)
    if f"voronoi_contours_{DEP}.geojson" not in os.listdir("geojson/"):
        communes_dep = communes_france[communes_france.insee.str.startswith(str(DEP))]
        codes2drop = ('13055', '75056', '69123')
        communes_dep = communes_dep.loc[~(communes_dep['insee'].str.startswith(codes2drop))]

        addresses_path = f"parquet/table_{DEP}.parquet"
        # ## Loading the address file, and a file with the shape of communes.
        # ##### Warning: these files are heavy

        addresses_df = pd.read_parquet(addresses_path)
        # if id_brut_bv is not None, condition below should always be True
        # The lines below creates an (unofficial) identifier of bureau de vote. We use it in this code mostly for displaying purpose
        addresses_df['id_bv'] = addresses_df['id_brut_bv']
        addresses_df['commune_bv'] = addresses_df['code_commune_ref']
        # pour gérer (temporairement) les villes à arrondissements
        # les géométries des arrondissements ne sont pas dans communes-20220101.shp
        # addresses_df['commune_bv'] = addresses_df['commune_bv'].apply(
        #     lambda c: '13055' if c.startswith('132')
        #     else '69123' if c.startswith('693')
        #     else '75056' if c.startswith('751')
        #     else c
        # )
        # addresses_df['code_commune_ref'] = addresses_df['code_commune_ref'].apply(
        #     lambda c: '13055' if c.startswith('132')
        #     else '69123' if c.startswith('693')
        #     else '75056' if c.startswith('751')
        #     else c
        # )
        print(f"LOAD dep {DEP} in memory: {len(addresses_df)} rows")
        geo_addresses = build_geojson_point(addresses_df)
        hulls = get_clipped_voronoi_shapes(geo_addresses, communes_dep)
        id_bvs = []
        coordinates = []
        # the block below just aims at formatting the cordinates into a list of [x, y]
        for _, row in hulls.iterrows():
            id_bvs.append(row["id_bv"])
            try:
                coord = Polygon(
                    [
                        list(x)
                        for x in np.transpose(
                            [
                                list(row["geometry"].exterior.coords.xy[0]),
                                list(row["geometry"].exterior.coords.xy[1]),
                            ]
                        )
                    ]
                )
                coordinates.append(coord)
            except Exception as e:
                coordinates.append([])
                pass

        voronoi_polygons = gpd.GeoDataFrame(pd.DataFrame(data={"coordinates": coordinates, "id_bv": id_bvs}),
                                            geometry='coordinates'
                                            )
        # handling overlaps
        for main_idx in voronoi_polygons.index:
            for side_idx in voronoi_polygons.index:
                if main_idx != side_idx:
                    if voronoi_polygons.loc[main_idx, 'coordinates'].contains(voronoi_polygons.loc[side_idx, 'coordinates']):
                        voronoi_polygons.loc[main_idx, 'coordinates'] = voronoi_polygons.loc[main_idx, 'coordinates'].difference(voronoi_polygons.loc[side_idx, 'coordinates'])
        # grouping polygons into multipolygons for each BdV
        voronoi_polygons = voronoi_polygons.dissolve('id_bv').reset_index(names='id_bv').reset_index(names='id')
        # int ID as requested for downstream processes
        voronoi_polygons['id'] = voronoi_polygons['id'].astype(int)
        with open(f"geojson/voronoi_contours_{DEP}.geojson", 'w') as f:
            f.write(voronoi_polygons.to_json())
    else:
        print("Already processed")