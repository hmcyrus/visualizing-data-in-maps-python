"""
PyDeck layer examples — five deck.gl layers demonstrating different use cases.

Outputs five standalone HTML files to output/:
  pydeck_arc_layer.html         — power flow arcs (ArcLayer)
  pydeck_heatmap_layer.html     — flood intensity heatmap (HeatmapLayer)
  pydeck_column_layer.html      — population density 3D columns (ColumnLayer)
  pydeck_geojson_layer.html     — river network + district borders (GeoJsonLayer)
  pydeck_screengrid_layer.html  — population point density grid (ScreenGridLayer)

Run:
    python examples/03_pydeck_layers.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pydeck as pdk
import pandas as pd
import json

from data.synthetic import (
    power_flows,
    substations,
    flood_intensity_points,
    population_grid,
    district_polygons,
    river_network,
)

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

VIEW = pdk.ViewState(latitude=23.8, longitude=90.4, zoom=6, pitch=40)


# ---------------------------------------------------------------------------
# 1. ArcLayer — power flow between substations
# ---------------------------------------------------------------------------

def make_arc_layer():
    flows = power_flows(25)
    max_load = flows["load_mw"].max()

    # colour arcs by load: low=blue, high=red
    flows["r"] = (255 * flows["load_mw"] / max_load).astype(int)
    flows["g"] = 80
    flows["b"] = (255 * (1 - flows["load_mw"] / max_load)).astype(int)

    layer = pdk.Layer(
        "ArcLayer",
        data=flows,
        get_source_position=["src_lon", "src_lat"],
        get_target_position=["dst_lon", "dst_lat"],
        get_source_color=[0, 180, 255, 180],
        get_target_color=["r", "g", "b", 220],
        get_width="load_mw / 120",
        pickable=True,
        auto_highlight=True,
    )

    sub_layer = pdk.Layer(
        "ScatterplotLayer",
        data=substations(),
        get_position=["lon", "lat"],
        get_radius=8000,
        get_fill_color=[0, 220, 255, 200],
        pickable=True,
    )

    r = pdk.Deck(
        layers=[layer, sub_layer],
        initial_view_state=VIEW,
        map_style="mapbox://styles/mapbox/dark-v9",
        tooltip={"text": "{src_name} → {dst_name}\nLoad: {load_mw} MW"},
    )
    path = os.path.join(OUTPUT, "pydeck_arc_layer.html")
    r.to_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. HeatmapLayer — flood intensity
# ---------------------------------------------------------------------------

def make_heatmap_layer():
    df = flood_intensity_points(800)

    layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["lon", "lat"],
        get_weight="intensity",
        aggregation="MEAN",
        radiusPixels=40,
        intensity=1,
        threshold=0.05,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=VIEW,
        map_style="mapbox://styles/mapbox/light-v9",
    )
    path = os.path.join(OUTPUT, "pydeck_heatmap_layer.html")
    r.to_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 3. ColumnLayer — 3D population density bars
# ---------------------------------------------------------------------------

def make_column_layer():
    from data.synthetic import DISTRICTS
    import numpy as np

    records = [
        {"lon": clon, "lat": clat, "density": density, "district": name}
        for name, clat, clon, density in DISTRICTS
    ]
    df = pd.DataFrame(records)

    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["lon", "lat"],
        get_elevation="density",
        elevation_scale=8,
        radius=15000,
        get_fill_color=["255 - density / 200", "density / 200", 50, 200],
        pickable=True,
        auto_highlight=True,
    )

    view = pdk.ViewState(latitude=23.8, longitude=90.4, zoom=6, pitch=50, bearing=15)
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip={"text": "{district}\nDensity: {density} p/km²"},
    )
    path = os.path.join(OUTPUT, "pydeck_column_layer.html")
    r.to_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 4. GeoJsonLayer — river network + district polygons
# ---------------------------------------------------------------------------

def make_geojson_layer():
    rivers = river_network()
    districts = district_polygons()

    max_flow = rivers["flow_rate"].max()

    district_layer = pdk.Layer(
        "GeoJsonLayer",
        data=json.loads(districts.to_json()),
        opacity=0.15,
        stroked=True,
        filled=True,
        get_fill_color=[100, 160, 220, 60],
        get_line_color=[50, 100, 180, 180],
        get_line_width=1500,
        pickable=True,
    )

    # encode flow_rate into line width via a lookup dict
    river_data = json.loads(rivers.to_json())
    river_layer = pdk.Layer(
        "GeoJsonLayer",
        data=river_data,
        stroked=True,
        filled=False,
        get_line_color=[0, 120, 220, 230],
        get_line_width="properties.flow_rate / 2000",
        line_width_scale=500,
        line_width_min_pixels=2,
        pickable=True,
    )

    r = pdk.Deck(
        layers=[district_layer, river_layer],
        initial_view_state=VIEW,
        map_style="mapbox://styles/mapbox/light-v9",
        tooltip={"text": "River: {river}\nFlow: {flow_rate} m³/s\nDistrict: {district}"},
    )
    path = os.path.join(OUTPUT, "pydeck_geojson_layer.html")
    r.to_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 5. ScreenGridLayer — population point density
# ---------------------------------------------------------------------------

def make_screengrid_layer():
    df = population_grid()

    layer = pdk.Layer(
        "ScreenGridLayer",
        data=df,
        get_position=["lon", "lat"],
        get_weight="density",
        cell_size_pixels=20,
        color_range=[
            [0, 25, 0, 25],
            [0, 85, 0, 85],
            [0, 127, 0, 127],
            [0, 170, 0, 170],
            [0, 190, 0, 190],
            [0, 255, 0, 255],
        ],
        pickable=False,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=VIEW,
        map_style="mapbox://styles/mapbox/dark-v9",
    )
    path = os.path.join(OUTPUT, "pydeck_screengrid_layer.html")
    r.to_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building PyDeck layers...")
    make_arc_layer()
    make_heatmap_layer()
    make_column_layer()
    make_geojson_layer()
    make_screengrid_layer()
    print("Done. Open the HTML files in output/ in any browser.")
