"""
Methods to display the addresses of voters, the shapes of communes and the interpolated shapes of bureaux de votes 
"""

import pydeck as pdk
import pandas as pd
import numpy as np
import geopandas as gpd
import geo
from typing import Dict, List

def prepare_layer_communes(communes: gpd.GeoDataFrame, filled=True) -> pdk.Layer:
    """
    Get a layer with the shapes of the communes

    Args:
        communes (gpd.GeoDataFrame): the shapes of the communes, and a column with the citycode
        filled (bool, optional): if True, fills the communes shapes with colours. Defaults to True.

    Returns:
        pdk.Layer: a pydeck Layer with the polygonal shapes of the communes
    """
    assert (
        "result_citycode" in communes.columns or "insee" in communes.columns
    ), "the code commune must be given, in order to associate deterministic colours to communes"
    if "result_citycode" in communes.columns:
        col = "result_citycode"
    else:
        col = "insee"
    displayed = communes.copy()
    # Corsica: remove "a" and "b" in code commune
    corsica_mask = displayed[col].str.contains("a|b|A|B", regex=True)
    displayed[col] = displayed[col].str.split("a|b", regex=True, expand=True)
    displayed = displayed.astype({col: int})
    displayed["color_r"] = 7 * displayed[col] % 255
    displayed["color_g"] = 23 * displayed[col] % 255
    displayed["color_b"] = 67 * displayed[col] % 255

    coordinates = []
    for _, row in displayed.iterrows():
        try:
            coord = [
                [
                    list(x)
                    for x in np.transpose(
                        [
                            list(row["geometry"].exterior.coords.xy[0]),
                            list(row["geometry"].exterior.coords.xy[1]),
                        ]
                    )
                ]
            ]
            coordinates.append(coord)
        except Exception as e:
            print(e)
            coordinates.append([])
            pass
    displayed["coordinates"] = coordinates

    return pdk.Layer(
        "PolygonLayer",
        pd.DataFrame(displayed),
        pickable=False,
        opacity=0.05,
        stroked=True,
        filled=filled,
        radius_scale=6,
        line_width_min_pixels=1,
        get_polygon="coordinates",
        get_fill_color=["color_r", "color_g", "color_b"],
        get_line_color=[128, 128, 128],
    )


def prepare_layer_addresses(df: pd.DataFrame) -> pdk.Layer:
    """
    Put a table of addresses on a map

    Args:
        df (pd.DataFrame): must include columns 'Commune' (strings), 'adr_complete' (strings), 'result_score' (floats), 'result_label' (strings), 'latitude' (floats), 'longitude' (floats)

    Returns:
        pdk.Layer: every input address is figured with a point on the map
    """
    data = df.copy()
    data["radius"] = 6
    data["coordinates"] = np.array(df[["longitude", "latitude"]]).tolist()
    #    NB: 7, 23 and 67 are coprime with 255. That implies two voting places in the same city will have the same colors if and only if their id_bv modulo 255 are the same. Moreover, two successive voting places will have rather different colors.
    data["id_bv_r"] = 7 * data["id_bv"] % 255
    data["id_bv_g"] = 23 * data["id_bv"] % 255
    data["id_bv_b"] = 67 * data["id_bv"] % 255
    data.drop(columns=["latitude", "longitude"], inplace=True, errors="ignore")
    # Define a layer to display on a map
    return pdk.Layer(
        "ScatterplotLayer",
        data,
        pickable=True,
        opacity=0.9,
        filled=True,
        radius_min_pixels=1,
        radius_max_pixels=6,
        line_width_min_pixels=2,
        get_position="coordinates",
        get_fill_color=["id_bv_r", "id_bv_g", "id_bv_b"],
        get_radius="radius",
        get_line_color=[0, 0, 0],
    )


def prepare_layer_polygons(
    geo_addresses: gpd.GeoDataFrame,
    communes: gpd.GeoDataFrame = gpd.GeoDataFrame(),
    mode="voronoi",
) -> pdk.Layer:
    """
    Draw polygons around the addresses, so that addresses sharing the same bureau de vote are within the same polygon

    :warning: The geometries of the `geo_addresses` must be either MultiPoint (if we want convex hull) or Point (if we want Voronoi cells)

    Args:
        geo_addresses (gpd.GeoDataFrame): must include columns "id_bv" and "result_citycode". The geometries must be shapely Point (in the case of voronoi cells) or MultiPoint (in the case of convex hulls)
        communes (gpd.GeoDataFrame, optional): the shapes of communes, if available
        mode (str, optional): The way we want to compute polygons around the addresses : can be "convex" or "voronoi". Defaults to "voronoi".

    Returns:
        pdk.Layer: calculated bureau de vote shapes are figured with polygons on the map
    """
    assert mode.lower() in [
        "convex",
        "voronoi",
    ], "the implemented methods are voronoi cells or convex hulls"
    mode = mode.lower()

    coordinates = []

    if mode == "convex":
        displayed = geo_addresses.copy()
        displayed["hulls"] = geo.convex_hull(displayed)
        for _, row in displayed.iterrows():
            try:
                coord = [
                    [
                        list(x)
                        for x in np.transpose(
                            [
                                list(row["hulls"].exterior.coords.xy[0]),
                                list(row["hulls"].exterior.coords.xy[1]),
                            ]
                        )
                    ]
                ]
                coordinates.append(coord)
            except Exception as e:
                # print(e)
                coordinates.append([])
                pass
        displayed.drop(columns=["geometry", "hulls"], inplace=True)

    elif mode == "voronoi":
        hulls = geo.get_clipped_voronoi_shapes(geo_addresses, communes)
        id_bvs = []
        for _, row in hulls.iterrows():
            id_bvs.append(row["id_bv"])
            try:
                coord = [
                    [
                        list(x)
                        for x in np.transpose(
                            [
                                list(row["geometry"].exterior.coords.xy[0]),
                                list(row["geometry"].exterior.coords.xy[1]),
                            ]
                        )
                    ]
                ]
                coordinates.append(coord)
            except Exception as e:
                coordinates.append([])
                pass

        displayed = pd.DataFrame(data={"coordinates": coordinates, "id_bv": id_bvs})
    displayed["id_bv_r"] = 7 * displayed["id_bv"] % 255
    displayed["id_bv_g"] = 23 * displayed["id_bv"] % 255
    displayed["id_bv_b"] = 67 * displayed["id_bv"] % 255
    displayed["coordinates"] = coordinates
    # Define a layer to display on a map
    return pdk.Layer(
        "PolygonLayer",
        pd.DataFrame(displayed),
        pickable=False,
        opacity=0.2,
        stroked=False,
        filled=True,
        radius_scale=6,
        line_width_min_pixels=1,
        get_polygon="coordinates",
        get_fill_color=["id_bv_r", "id_bv_g", "id_bv_b"],
        get_line_color=[0, 0, 0],
    )


def prepare_tooltip(columns: List[str]) -> Dict:
    """
    Prepare a tooltip indicating a specific subset of columns

    Args:
        columns (List[str]): a list of columns of the data

    Returns:
        Dict: _description_
    """
    legend = ""
    for col in ["id_bv", "result_score", "geo_score", "commune_bv", "geo_adresse" "result_label", "adr_complete", "Commune"]:
        if col in columns:
            legend += f"{col}: "+"{"+f"{col}"+"} \n" 
    tooltip = {
        "text": legend
    }
    return tooltip


def display_addresses(
    addresses: pd.DataFrame, communes: gpd.GeoDataFrame = gpd.GeoDataFrame()
) -> pdk.Deck:
    """
    Display a map with one point per address

    Args:
        addresses (pd.DataFrame): _description_
        communes (gpd.GeoDataFrame, optional): the shapes of communes, if available

    Returns:
        pdk.Deck: _description_
    """
    addresses_layer = prepare_layer_addresses(addresses)
    if len(communes):
        layers = [prepare_layer_communes(communes), addresses_layer]
    else:
        layers = [addresses_layer]

    # Set the viewport location
    view_state = pdk.ViewState(
        latitude=43.055403, longitude=1.470104, zoom=6, bearing=0, pitch=0
    )

    # Render
    return pdk.Deck(
        map_style="light",
        layers=layers,
        initial_view_state=view_state,
        tooltip=prepare_tooltip(addresses.columns),
    )


def display_bureau_vote_shapes(
    addresses: pd.DataFrame,
    communes: gpd.GeoDataFrame = gpd.GeoDataFrame(),
    mode="voronoi",
) -> pdk.Deck:
    """
    Display on the same map the addresses and the corresponding interpolated bureau de vote shapes

    Args:
        addresses (pd.DataFrame): must include columns 'Commune' (strings), 'adr_complete' (strings), 'result_score' (floats), 'result_label' (strings), 'latitude' (floats), 'longitude' (floats)
        communes (gpd.GeoDataFrame, optional): the shapes of communes, if available
        mode (str, optional): The way we want to compute polygons around the addresses : can be "convex" or "voronoi". Defaults to "voronoi".

    Returns:
        pdk.Deck: pydeck with layers 'addresses' (one point per adress), 'communes' (one shape per commune), 'polygons' (one shape per bureau de vote, with the commune)
    """
    assert mode.lower() in ["convex", "voronoi"]
    mode = mode.lower()

    if mode == "convex":
        geojson = geo.build_geojson_multipoint(addresses)
    elif mode == "voronoi":
        geojson = geo.build_geojson_point(addresses)

    geojson.drop_duplicates(subset=["geometry"], inplace=True)
    polygons_layer = prepare_layer_polygons(geojson, mode=mode, communes=communes)

    if len(communes):
        communes_layers = prepare_layer_communes(communes, filled=False)
        layers = [communes_layers, polygons_layer, prepare_layer_addresses(addresses)]
    else:
        layers = [
            polygons_layer,
            prepare_layer_addresses(addresses),
        ]

    # Set the viewport location
    view_state = pdk.ViewState(
        latitude=43.055403, longitude=1.470104, zoom=6, bearing=0, pitch=0
    )
    # Render
    return pdk.Deck(
        map_style="light",
        layers=layers,
        initial_view_state=view_state,
        tooltip=prepare_tooltip(addresses.columns),
    )
