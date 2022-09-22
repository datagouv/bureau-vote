"""
Utils methods to geocode addresses, and to compute polygonal shapes around the addresses
"""
import pandas as pd
import os
import numpy as np
import geopandas as gpd
import pytess
from typing import List
from shapely.geometry import Polygon
import requests


def add_geoloc(df: pd.DataFrame) -> pd.DataFrame:
    """
    Locally save the raw base of addresses and call the API-adresse to geocode them (in particular: add coordinates and found city)

    Args:
        df (pd.DataFrame): a file with columns "adr_complete" (street number + street type + street name/locality name), "Commune" (commune name), "CP" (postcode)

    Returns:
        pd.DataFrame: a dataframe with the input columns, and also latitudes, longitudes, result_postcode, result_citycode, etc.
    """
    df.to_csv("concat_adr_bv.csv", index=False)
    # os.system(
    #     "curl -X POST -F data=@concat_adr_bv.csv -F columns=adr_complete -F columns=Commune -F postcode=CP https://api-adresse.data.gouv.fr/search/csv/ > concat_adr_bv_geocoded.csv"
    # )
    f = open('concat_adr_bv.csv', 'rb')
    files = {'data': ('concat_adr_bv', f)}
    payload = {'columns': ['adr_complete', 'Commune'], 'postcode': 'CP'}
    r = requests.post('https://api-adresse.data.gouv.fr/search/csv/', files=files, data=payload, stream=True)
    with open('concat_adr_bv_geocoded.csv', 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            fd.write(chunk)

    geocoded = pd.read_csv("concat_adr_bv_geocoded.csv", dtype=str)
    geocoded["latitude"] = geocoded["latitude"].astype(float)
    geocoded["longitude"] = geocoded["longitude"].astype(float)
    geocoded["result_score"] = geocoded["result_score"].astype(float)
    geocoded = geocoded[geocoded["result_label"].notna()]
    return geocoded


def build_geojson_point(addresses: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Turn the dataframes with coordinates into a GeoDataFrame containing a Point object for each address
    NB: when there is several addresses at the same point, the function keeps only one sample

    Args:
        addresses (pd.DataFrame): a dataframe that have already been processed with API-adresse, and that also contain ids for bureau de vote (function `cleaner.prepare_ids`)
    Returns:
        gpd.GeoDataFrame: includes columns: "geometry" (shapely Point), "result_citycode" (as string), "label" (commune name, as string) and "id_bv" (unique id we impose per bureau de vote, int)
    """

    geojson = {"type": "FeatureCollection", "features": []}
    for _, row in addresses.iterrows():
        if row["result_label"]:
            props = {
                "label": row["result_label"],
                "id_bv": row["id_bv"],
                "result_citycode": row["result_citycode"],
            }
            geojson["features"].append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            float(row["longitude"]),
                            float(row["latitude"]),
                        ],
                    },
                    "properties": props,
                }
            )
    gdf = gpd.GeoDataFrame.from_features(geojson)
    # IMPORTANT: when there is several addresses at the same point keep only one sample
    return gdf.drop_duplicates(subset=["geometry"])


def build_geojson_multipoint(addresses: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Turn the dataframes with coordinates into a GeoDataFrame containing a MultiPoint (list of point) object for each bureau de vote

    Args:
        addresses (pd.DataFrame): a dataframe that have already been processed with API-adresse, and that also contain ids for bureau de vote (function `cleaner.prepare_ids`)
    Returns:
        gpd.GeoDataFrame: includes columns: "geometry" (shapely MultiPoint), "result_citycode" (as string) and "id_bv" (unique id we impose per bureau de vote, int)
    """

    geojson = {"type": "FeatureCollection", "features": []}
    assert (
        "id_bv" in addresses.columns
    ), "There is no identifier for the 'bureaux de vote' in this dataframe"

    def get_coordinates_list(data: pd.DataFrame) -> np.array:
        return np.array(data[["longitude", "latitude"]]).tolist()

    for id_bv, data in addresses.groupby("id_bv"):
        cp = data.result_citycode.min()

        geojson["features"].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPoint",
                    "coordinates": get_coordinates_list(data),
                },
                "properties": {"id_bv": id_bv, "result_citycode": cp},
            }
        )
    gdf = gpd.GeoDataFrame.from_features(geojson)
    return gdf


def convex_hull(gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """
    Compute the convex hulls of input geometries

    Args:
        gdf (gpd.GeoDataFrame):

    Returns:
        gpd.GeoSeries: each row is a Polygon, a Point or a LineString
    """
    return gpd.GeoSeries(gdf.geometry).convex_hull


def clip_to_communes(
    gdf: gpd.GeoDataFrame, communes: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Clip the polygons of input geodataframe to the boundaries of specified communes.

    Args:
        gdf (gpd.GeoDataFrame): must include columns "geometry" and "result_citycode"
        communes (gpd.GeoDataFrame): must include columns `geometry` and "result_citycode"

    Returns:
        gpd.GeoDataFrame: the input GeoDataFrames have been clipped according to the input `communes` shapes
    """
    gdf_copy = gdf.copy()
    multipolygons_communes_dict = {}
    multipolygons_communes_list = list()
    # precompute the MultiPolygon of each of the commune that is relevant for our input geodataframe
    for cp in np.intersect1d(
        communes.result_citycode.unique(), gdf.result_citycode.unique()
    ):
        multipolygons_communes_dict[cp] = communes[
            communes.result_citycode == cp
        ].geometry.unary_union
    # align the precomputed MultiPolygons with the input GeoDataFrame `gdf`
    for _, row in gdf_copy.iterrows():
        cp = row["result_citycode"]
        multipolygons_communes_list.append(multipolygons_communes_dict[cp])
    # and now clip the geometries!
    gdf_copy.geometry = gdf_copy.geometry.intersection(
        gpd.GeoSeries(multipolygons_communes_list), align=False
    )
    return gdf_copy


def polygon_union(
    gdf: gpd.GeoDataFrame,
    pivot_column: str = "id_bv",
    columns: List[str] = ["result_citycode"],
) -> gpd.GeoDataFrame:
    """
    Assuming the geometry of the input GeoDataFrame geometry consists of polygons, make the union of these polygons given a pivot column.
    Some columns of the input GeoDataFrame can be kept in the output, under the assumption that :
    (i) for a given pivot value, and a given column of "columns", the value of the column on this pivot value stays constant

    Args:
        gdf (gpd.GeoDataFrame): must contain the column `pivot_column` and the ancillary columns `columns`
        pivot_column (str): the column that must be used as pivot. Defaults to "id_bv".
        columns (List[str], optional): The list of other columns (not `pivot_column` nor "geometry") to keep in the output. Defaults to ["result_citycode"].

    Returns:
        gpd.GeoDataFrame: consists of the geometry of merged polygons (that are Polygon or MultiPolygon), `pivot_column` and the ancillary columns `columns`
    """
    geometries = list()
    # "data" consists of the properties of the output GeoDataFrame
    data = {pivot_column: []}
    for column in columns:
        data[column] = list()

    for pivot in gdf[pivot_column].unique():
        # WARNING: the 2 lines below assumes that, for a given pivot value, and a given column of "columns", the value of the column on this pivot value stays constant
        # in particular, it is right for the column "result_citycode" when the union is done on "id_bv")
        for column in columns:
            val = gdf[gdf[pivot_column] == pivot][column].min()
            data[column].append(val)
        s = gdf[gdf[pivot_column] == pivot].geometry
        geometries.append(s.unary_union)
        data[pivot_column].append(pivot)
    return gpd.GeoDataFrame(geometry=geometries, data=data)


def get_clipped_voronoi_shapes(
    gdf: gpd.GeoDataFrame, communes: gpd.GeoDataFrame = gpd.GeoDataFrame()
) -> gpd.GeoDataFrame:
    """
    Compute voronoi cells, clip them to the shapes of communes, and merge the clipped cells that share the same "id_bv"

    Args:
        gdf (gpd.GeoDataFrame): must include "geometry", "result_citycode" (string) and "id_bv" (unique id we determine for each bureau de vote, int)
        communes (gpd.GeoDataFrame, optional): _description_. Defaults to gpd.GeoDataFrame().

    Returns:
        gpd.GeoDataFrame:
    """

    hulls = voronoi_hull(gdf)
    if len(communes):
        hulls = clip_to_communes(hulls, communes)
    return connected_components_polygon_union(hulls)


def connected_components_polygon_union(
    gdf: gpd.GeoDataFrame,
    pivot_column: str = "id_bv",
    columns: List[str] = ["result_citycode"],
) -> gpd.GeoDataFrame:
    """
    Assuming the geometry of the input GeoDataFrame geometry consists of polygons, return the connected components of the union of these polygons given a pivot column
    Some columns of the input GeoDataFrame can be kept in the output, under the assumption that :
    (i) for a given pivot value, and a given column of "columns", the value of the column on this pivot value stays constant

    Args:
        gdf (gpd.GeoDataFrame): must contain the column `pivot_column` and the ancillary columns `columns`
        pivot_column (str): the column that must be used as pivot. Defaults to "id_bv".
        columns (List[str], optional): The list of other columns (not `pivot_column` nor "geometry") to keep in the output. Defaults to ["result_citycode"].

    Returns:
        gpd.GeoDataFrame: consists of the geometry of merged connected components (that are necessary Polygon), `pivot_column` and the ancillary columns `columns`
    """
    geometries = list()
    # "data" consists of the properties of the output GeoDataFrame
    data = {pivot_column: []}
    for column in columns:
        data[column] = list()

    def save_columns_values(pivot):
        data[pivot_column].append(pivot)
        for column in columns:
            val = gdf[gdf[pivot_column] == pivot][column].min()
            data[column].append(val)

    for pivot in gdf[pivot_column].unique():
        # WARNING: the 2 lines below assumes that, for a given pivot value, and a given column of "columns", the value of the column on this pivot value stays constant
        # in particular, it is right for the column "result_citycode" when the union is done on "id_bv")
        s = gdf[
            gdf[pivot_column] == pivot
        ].geometry  # normally these shapes are Polygon, but could be Point if there is only one found voter in a bureau de vote
        if len(s) == 1 and s.iloc[0].type == "Point":
            geometries.append(s)
            save_columns_values(pivot)
        else:
            merged_shape = s.unary_union
            if merged_shape.type == "Polygon":
                geometries.append(merged_shape)
                save_columns_values(pivot)

            elif merged_shape.type == "MultiPolygon":
                for _, row in (
                    gpd.GeoDataFrame(geometry=[merged_shape])
                    .explode(index_parts=False)
                    .iterrows()
                ):
                    geometries.append(row["geometry"])
                    save_columns_values(pivot)
    return gpd.GeoDataFrame(geometry=geometries, data=data)


def voronoi_hull(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Compute voronoi cells around each of the input addresses, within an arbitrary large bounding box (hence, it is useful to clip afterwards the cells on limits relevant to our use cases)
    It is a based on the voronoi method implemented in the library pytess

    Args:
        gdf (gpd.GeoDataFrame): must include "geometry", "result_citycode" (string) and "id_bv" (unique id we determine for each bureau de vote, int)

    Returns:
        gpd.GeoDataFrame: include "geometry", "result_citycode" and "id_bv"
    """
    assert (
        "id_bv" in gdf.columns and "result_citycode" in gdf.columns
    ), "Some necessary columns are missing"
    gdf_copy = gdf.copy()

    id_bvs, citycodes = [], []
    polygons = []
    gdf_copy.drop_duplicates(
        subset=["geometry"], inplace=True
    )  # delete duplicates of geolocated points
    for citycode in gdf_copy.result_citycode.unique():
        gdf_city = gdf_copy[gdf_copy.result_citycode == citycode]
        if len(gdf_city) >= 3:
            points_city, id_bvs_city = [], []
            for k in gdf_city.index:
                points_city.append(
                    (
                        gdf_city.geometry[k].coords.xy[0][0],
                        gdf_city.geometry[k].coords.xy[1][0],
                    )
                )
                id_bvs_city.append(gdf_city.id_bv[k])
            # the condition "if k" exclude the corner of bounding box from the pytess.voronoi output
            # the size of 'buffer_percent' defines the size of the virtual bounding box we compute Voronoi in
            #  pytess.voronoi returns a list of 2-tuples, with the first item in each tuple being the original input point (or None for each corner of the bounding box buffer), and the second item being the point's corressponding Voronoi polygon.

            voronoi_city_dict = {
                k: v for (k, v) in pytess.voronoi(points_city, buffer_percent=600) if k
            }
            polygons_city = []
            if (
                type(points_city) == list
            ):  # this list is supposed to be like [(lat, lon), (lat, lon), (lat, lon), ...]
                for point in points_city:
                    try:
                        polygons_city.append(Polygon(voronoi_city_dict[point]))
                    except:
                        polygons_city.append(None)
            id_bvs.extend(id_bvs_city)
            citycodes.extend([citycode] * len(gdf_city))
            polygons.extend(polygons_city)

    return gpd.GeoDataFrame(
        geometry=polygons, data={"id_bv": id_bvs, "result_citycode": citycodes}
    )
