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
    flood_intensity_points,
    population_grid,
    district_polygons,
    river_network,
)
from data.pgcb import pgcb_substations, pgcb_lines, VOLTAGE_COLOUR, VOLTAGE_WIDTH, NODE_COLOUR

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

VIEW = pdk.ViewState(latitude=23.8, longitude=90.4, zoom=6, pitch=40)


# ---------------------------------------------------------------------------
# 1. ArcLayer — power flow between substations
# ---------------------------------------------------------------------------

def _hex_rgba(hex_colour: str, alpha: int = 200):
    h = hex_colour.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)] + [alpha]


def make_arc_layer():
    lines = pgcb_lines(voltages=(400, 230, 132))
    subs  = pgcb_substations()

    # Per-voltage RGBA columns (deck.gl reads per-row colour arrays)
    _V_ALPHA = {400: 230, 230: 200, 132: 155}
    lines["r"]   = lines["voltage_kv"].map(lambda v: _hex_rgba(VOLTAGE_COLOUR[v], _V_ALPHA[v])[0])
    lines["g"]   = lines["voltage_kv"].map(lambda v: _hex_rgba(VOLTAGE_COLOUR[v], _V_ALPHA[v])[1])
    lines["b"]   = lines["voltage_kv"].map(lambda v: _hex_rgba(VOLTAGE_COLOUR[v], _V_ALPHA[v])[2])
    lines["a"]   = lines["voltage_kv"].map(lambda v: _V_ALPHA[v])
    lines["arc_width"] = lines["voltage_kv"].map(VOLTAGE_WIDTH)

    arc_layer = pdk.Layer(
        "ArcLayer",
        data=lines,
        get_source_position=["src_lon", "src_lat"],
        get_target_position=["dst_lon", "dst_lat"],
        get_source_color=["r", "g", "b", "a"],
        get_target_color=["r", "g", "b", "a"],
        get_width="arc_width",
        pickable=True,
        auto_highlight=True,
    )

    # Node colours from hex → RGB columns
    subs["nr"] = subs["node_type"].map(lambda t: _hex_rgba(NODE_COLOUR.get(t, "#95a5a6"))[0])
    subs["ng"] = subs["node_type"].map(lambda t: _hex_rgba(NODE_COLOUR.get(t, "#95a5a6"))[1])
    subs["nb"] = subs["node_type"].map(lambda t: _hex_rgba(NODE_COLOUR.get(t, "#95a5a6"))[2])
    subs["radius"] = subs["capacity_mva"].apply(
        lambda c: max(5_000, min(20_000, c * 9)) if c > 0 else 5_500
    )

    node_layer = pdk.Layer(
        "ScatterplotLayer",
        data=subs,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=["nr", "ng", "nb", 220],
        stroked=True,
        get_line_color=[255, 255, 255, 80],
        line_width_min_pixels=1,
        pickable=True,
    )

    r = pdk.Deck(
        layers=[arc_layer, node_layer],
        initial_view_state=VIEW,
        map_style="mapbox://styles/mapbox/dark-v9",
        tooltip={
            "html": (
                "<b>{name}</b><br/>"
                "{src} → {dst}<br/>"
                "{voltage_kv} kV | {length_km} km<br/>"
                "Type: {node_type} | Zone: {zone}<br/>"
                "Capacity: {capacity_mva} MVA"
            ),
            "style": {"backgroundColor": "rgba(20,20,20,0.85)", "color": "white"},
        },
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
