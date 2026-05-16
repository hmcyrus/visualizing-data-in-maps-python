"""
Plotly map examples — three techniques.

Outputs three standalone HTML files to output/:
  plotly_choropleth.html     — district density choropleth (Plotly Express)
  plotly_scatter_map.html    — power-flow scatter/lines on a map
  plotly_flood_animation.html — animated flood progression over time

Run:
    python examples/02_plotly_maps.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import plotly.express as px
import plotly.graph_objects as go
import json

from data.synthetic import district_polygons, flood_time_series
from data.pgcb import pgcb_substations, pgcb_lines, VOLTAGE_COLOUR, VOLTAGE_WIDTH, NODE_COLOUR

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

CENTRE_LAT, CENTRE_LON = 23.8, 90.4


# ---------------------------------------------------------------------------
# 1. Choropleth — district population density
# ---------------------------------------------------------------------------

def make_choropleth():
    gdf = district_polygons()
    geojson = json.loads(gdf.to_json())

    fig = px.choropleth_map(
        gdf,
        geojson=geojson,
        locations="district",
        featureidkey="properties.district",
        color="density",
        color_continuous_scale="YlOrRd",
        map_style="carto-positron",
        zoom=6,
        center={"lat": CENTRE_LAT, "lon": CENTRE_LON},
        opacity=0.7,
        labels={"density": "Pop. density (p/km²)"},
        title="Population Density by District",
        hover_data=["population"],
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})

    path = os.path.join(OUTPUT, "plotly_choropleth.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. Scatter map — substations + flow lines
# ---------------------------------------------------------------------------

def make_scatter_map():
    lines = pgcb_lines(voltages=(400, 230, 132))
    subs  = pgcb_substations()

    fig = go.Figure()

    # Transmission lines — one trace per voltage level (None-separated segments)
    for v in (132, 230, 400):   # draw lowest voltage first so 400 kV is on top
        vlines = lines[lines["voltage_kv"] == v]
        if vlines.empty:
            continue
        lats, lons = [], []
        for _, row in vlines.iterrows():
            lats += [row["src_lat"], row["dst_lat"], None]
            lons += [row["src_lon"], row["dst_lon"], None]
        fig.add_trace(go.Scattermap(
            lat=lats, lon=lons,
            mode="lines",
            line={"width": VOLTAGE_WIDTH[v] * 1.6, "color": VOLTAGE_COLOUR[v]},
            name=f"{v} kV",
            opacity=0.85,
            hoverinfo="skip",
        ))

    # Nodes — one trace per node_type
    _TYPE_LABEL = {
        "substation":   "Substation",
        "thermal_pp":   "Thermal PP",
        "hydro_pp":     "Hydro PP",
        "renewable_pp": "Renewable PP",
        "hvdc_btp":     "HVDC BtB",
    }
    for ntype in ("substation", "thermal_pp", "hydro_pp", "renewable_pp", "hvdc_btp"):
        subset = subs[subs["node_type"] == ntype]
        if subset.empty:
            continue
        sizes = subset["capacity_mva"].apply(
            lambda c: max(8, min(22, c / 90)) if c > 0 else 8
        ).values
        fig.add_trace(go.Scattermap(
            lat=subset["lat"],
            lon=subset["lon"],
            mode="markers",
            marker=dict(size=sizes, color=NODE_COLOUR[ntype], opacity=0.95),
            name=_TYPE_LABEL[ntype],
            text=subset["name"],
            customdata=list(zip(subset["capacity_mva"], subset["zone"])),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Type: " + _TYPE_LABEL[ntype] + "<br>"
                "Capacity: %{customdata[0]} MVA<br>"
                "Zone: %{customdata[1]}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="PGCB Transmission Network — 400 / 230 / 132 kV",
        map=dict(
            style="carto-darkmatter",
            center={"lat": CENTRE_LAT, "lon": CENTRE_LON},
            zoom=6,
        ),
        legend=dict(
            bgcolor="rgba(30,30,30,0.75)",
            font=dict(color="white"),
            title=dict(text="Legend", font=dict(color="white")),
        ),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
    )

    path = os.path.join(OUTPUT, "plotly_scatter_map.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 3. Animated map — flood progression
# ---------------------------------------------------------------------------

def make_flood_animation():
    df = flood_time_series(n_steps=12)
    # bin intensity to a readable label
    df["level"] = pd.cut(
        df["intensity"],
        bins=[0, 0.25, 0.5, 0.75, 1.0],
        labels=["Low", "Moderate", "High", "Severe"],
    ).astype(str)

    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        color="intensity",
        animation_frame="hour",
        size="intensity",
        size_max=14,
        color_continuous_scale="Blues",
        range_color=[0, 1],
        map_style="carto-positron",
        zoom=6,
        center={"lat": CENTRE_LAT, "lon": CENTRE_LON},
        title="Flood Intensity Progression (T+00h → T+11h)",
        labels={"intensity": "Intensity"},
        hover_data={"lat": ":.3f", "lon": ":.3f", "intensity": ":.2f"},
        opacity=0.7,
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0})

    path = os.path.join(OUTPUT, "plotly_flood_animation.html")
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------

import pandas as pd   # needed by make_flood_animation

if __name__ == "__main__":
    print("Building Plotly maps...")
    make_choropleth()
    make_scatter_map()
    make_flood_animation()
    print("Done. Open the HTML files in output/ in any browser.")
