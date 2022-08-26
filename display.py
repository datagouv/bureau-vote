import pydeck as pdk
import pandas as pd
import numpy as np
import math
import geopandas as gpd
import geo

def prepare_layer_communes(communes: gpd.GeoDataFrame, filled=True) -> pdk.Layer:
    displayed = communes.copy().astype({"result_citycode":int})
    displayed["color_r"] = 7*displayed['result_citycode'] % 255
    displayed["color_g"] = 23*displayed['result_citycode'] % 255
    displayed["color_b"] = 67*displayed['result_citycode'] % 255
    
    coordinates = []
    for _, row in displayed.iterrows():
        try:
            coord = [[
                list(x) for x in np.transpose([list(row["geometry"].exterior.coords.xy[0]), list(row["geometry"].exterior.coords.xy[1])])
            ]]
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
        get_fill_color=['color_r', 'color_g', 'color_b'],
        get_line_color=[128, 128, 128],
    )

def prepare_layer_addresses(df: pd.DataFrame) -> pdk.Layer:
    """
    df: pd.DataFrame with at least columns 'Commune' (strings), 'adr_complete' (strings), 'result_score' (floats), 'result_label' (strings), 'latitude' (floats), 'longitude' (floats)
    return a pydeck Layer
    NB: 7, 23 and 67 are coprime with 255. That implies two voting places in the same city will have the same colors if and only if their `code_bv` modulo 255 are the same. Moreover, two successive voting places will have rather different colors.

    """
    data = df[["longitude", "latitude", "id_bv", "result_score", "result_label", "result_citycode", "adr_complete", "Commune"]].copy()
    data['radius'] = 6
    data['id'] = data.index
    data['coordinates'] = np.array(df[['longitude','latitude']]).tolist()
    data["id_bv_r"] = 7*data['id_bv'] % 255
    data["id_bv_g"] = 23*data['id_bv'] % 255
    data["id_bv_b"] = 67*data['id_bv'] % 255
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
        get_fill_color=['id_bv_r', 'id_bv_g', 'id_bv_b'],
        get_radius="radius",
        get_line_color=[0, 0, 0],
    )


def prepare_layer_polygons(geo_addresses: gpd.GeoDataFrame, communes: gpd.GeoDataFrame=gpd.GeoDataFrame(), mode="hull") -> pdk.Layer:
    """
    The detailed format of the GeoDataFrame `geo_addresses` must be either MultiPoint (for convex hull) either Point (for Voronoi). It must also include columns "id_bv" and "result_citycode"
    """
    assert mode.lower() in ["hull", "voronoi"]
    mode = mode.lower()

    coordinates =  []
    
    if mode == "hull":
        displayed = geo_addresses.copy()
        displayed["hulls"] = geo.convex_hull(displayed)
        for _, row in displayed.iterrows():
            try:
                coord = [[
                    list(x) for x in np.transpose([list(row["hulls"].exterior.coords.xy[0]), list(row["hulls"].exterior.coords.xy[1])])
                ]]
                coordinates.append(coord)
            except Exception as e:
                #print(e)
                coordinates.append([])
                pass
        displayed.drop(columns=["geometry", "hulls"], inplace=True)
        
    elif mode == "voronoi":
        hulls = geo.voronoi_hull(geo_addresses)
        hulls = geo.connected_components_polygon_union(hulls)
        # TODO is is really the right place for this computing and clipping?
        if len(communes):
            hulls = geo.clip_to_communes(hulls, communes)
        id_bvs = []
        for _, row in hulls.iterrows():
            id_bvs.append(row["id_bv"])
            try:
                coord = [[
                    list(x) for x in np.transpose([list(row["geometry"].exterior.coords.xy[0]), list(row["geometry"].exterior.coords.xy[1])])
                ]]
                coordinates.append(coord)
            except Exception as e:
                coordinates.append([])
                pass
            
            
        displayed = pd.DataFrame(data={"coordinates": coordinates, "id_bv": id_bvs})
    displayed["id_bv_r"] = 7*displayed['id_bv'] % 255
    displayed["id_bv_g"] = 23*displayed['id_bv'] % 255
    displayed["id_bv_b"] = 67*displayed['id_bv'] % 255
    displayed["coordinates"] = coordinates
    # Define a layer to display on a map
    return pdk.Layer(
        "PolygonLayer",
        pd.DataFrame(displayed),
        pickable=True,
        opacity=0.2,
        stroked=False,
        filled=True,
        radius_scale=6,
        line_width_min_pixels=1,
        get_polygon="coordinates",
        get_fill_color=['id_bv_r', 'id_bv_g', 'id_bv_b'],
        get_line_color=[0, 0, 0],
    )

def display_addresses(addresses:pd.DataFrame, communes: gpd.GeoDataFrame=gpd.GeoDataFrame()) -> pdk.Deck:
    """
    addresses: pd.DataFrame with at least columns  'Commune' (strings), 'adr_complete' (strings), 'result_score' (floats), 'result_label' (strings), 'latitude' (floats), 'longitude' (floats), 'result_citycode' (strings)
    return a pydeck Deck
    """
    addresses_layer = prepare_layer_addresses(addresses)
    if len(communes):
        layers = [
            prepare_layer_communes(communes),
            addresses_layer
        ]
    else:
        layers = [addresses_layer]
    
    # Set the viewport location
    view_state = pdk.ViewState(latitude=43.055403, longitude=1.470104, zoom=8, bearing=0, pitch=0)

    # Render
    return pdk.Deck(
        map_style="light",
        layers=layers,
        initial_view_state=view_state,
        tooltip={"text": "{id_bv} \n{result_score}\n{result_label}\n{adr_complete} {Commune}"}
    )


def display_hulls(addresses: pd.DataFrame, communes: gpd.GeoDataFrame=gpd.GeoDataFrame(), mode="hull") -> pdk.Deck:
    """
    addresses: pd.DataFrame with at least columns  'Commune' (strings), 'adr_complete' (strings), 'result_score' (floats), 'result_label' (strings), 'latitude' (floats), 'longitude' (floats), 'result_citycode' (strings)
    return a pydeck Deck
    """
    assert mode.lower() in ["hull", "voronoi"]
    mode = mode.lower()
    
    if mode == "hull":
        geojson = geo.build_geojson_multipoint(addresses)
    elif mode == "voronoi":
        geojson = geo.build_geojson_point(addresses)

    geojson.drop_duplicates(subset=["geometry"], inplace=True)
    polygons_layer = prepare_layer_polygons(geojson, mode=mode, communes=communes)
        
    if len(communes):
        communes_layers = prepare_layer_communes(communes, filled=False)
        layers = [
            communes_layers,
            polygons_layer,
            prepare_layer_addresses(addresses)
        ]
    else:
        layers = [
            polygons_layer,
            prepare_layer_addresses(addresses),
        ]
        
    # Set the viewport location
    view_state = pdk.ViewState(latitude=43.055403, longitude=1.470104, zoom=8, bearing=0, pitch=0)
    # Render
    return pdk.Deck(
        map_style="light",
        layers=layers,
        initial_view_state=view_state,
        tooltip={"text": "id_bv:{id_bv} \n{result_score}\n{result_label}\n{adr_complete} {Commune}"}
  
    )