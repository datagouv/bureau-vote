from cleaner import (
    clean_dataset,
    clean_failed_geocoding,
    clean_geocoded_types,
    prepare_ids
)
from display import (
    display_addresses,
    display_bureau_vote_shapes
)
import pandas as pd
from geo import (
    add_geoloc
)
import geopandas as gpd
import pydeck as pdk
import sys

if __name__ == '__main__':
    df = pd.read_csv(sys.argv[1], sep=";", dtype=str)
    print('### Dataset Loaded!')
    df = clean_dataset(df)
    # check that names preceded with a "chez" have been removed
    df.drop(columns=['libelle_voie_clean', 'comp_adr_1_clean', 'comp_adr_2_clean', 'lieu-dit-clean'], inplace=True)
    print('### Dataset Cleaned!')
    # Comment if you want to skip geocode stp (this step takes few minutes to run)
    geocoded_df = geo.add_geoloc(df=df)
    print('### Dataset geocoded!')
    geocoded_df = pd.read_csv("concat_adr_bv_geocoded.csv",dtype=str)
    #Clean geocoded dataframe
    geocoded_df = clean_geocoded_types(geocoded_df)
    geocoded_df = clean_failed_geocoding(geocoded_df)
    geocoded_df = prepare_ids(geocoded_df)
    # IMPORTANT: when there is two points at the position lat-lon, keep only one
    geocoded_df = geocoded_df.drop_duplicates(subset=["latitude", "longitude"])
    print('### Geocoded dataset Cleaned!')
    #Load shapes of communes
    communes_france = gpd.read_file("communes-20220101.shp")[["geometry", "insee"]].dropna().\
        rename(columns={"insee": "result_citycode"})
    communes_france["result_citycode"] = communes_france["result_citycode"].apply(lambda row: row.split(".")[0] if "." in row else row)
    communes_ariege = communes_france[communes_france.result_citycode.str.startswith("09")]
    del communes_france
    print('### Shapes communes loaded!')
    #Cartography with color by bureau de vote
    r = display_addresses(addresses=geocoded_df, communes=communes_ariege)
    r.to_html("scatterplot_layer.html")
    print('### Page 1 HTML generated!')
    #Save GeoJSON (with 1 Point per voter address)
    # geojson = geo.build_geojson_point(geocoded_df)
    #geojson.to_file("bv_point.geojson", driver="GeoJSON")
    #Display convex Hull
    # r_hulls = display.display_bureau_vote_shapes(addresses=geocoded_df, communes=communes_ariege, mode="convex")
    # r_hulls.to_html("hull_layer.html")
    #Display Voronoi tessellation
    r_voronoi = display_bureau_vote_shapes(addresses=geocoded_df, communes=communes_ariege, mode="voronoi")
    r_voronoi.to_html("voronoi_layer.html")
    print('### Page 2 HTML generated!')