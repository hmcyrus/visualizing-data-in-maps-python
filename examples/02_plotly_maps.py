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

from data.synthetic import (
    district_polygons,
    power_flows,
    substations,
    flood_time_series,
)

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
    subs = substations()
    flows = power_flows(25)

    fig = go.Figure()

    # draw flow lines first so they appear beneath markers
    max_load = flows["load_mw"].max()
    for _, row in flows.iterrows():
        width = 1 + 5 * row["load_mw"] / max_load
        fig.add_trace(go.Scattermap(
            lat=[row["src_lat"], row["dst_lat"], None],
            lon=[row["src_lon"], row["dst_lon"], None],
            mode="lines",
            line={"width": width, "color": "rgba(255,153,0,0.6)"},
            hoverinfo="skip",
            showlegend=False,
        ))

    # substation markers sized by capacity
    fig.add_trace(go.Scattermap(
        lat=subs["lat"],
        lon=subs["lon"],
        mode="markers",
        marker=dict(
            size=subs["capacity_mw"] / 80,
            color=subs["capacity_mw"],
            colorscale="Viridis",
            showscale=True,
            colorbar={"title": "Capacity (MW)"},
        ),
        text=subs["name"],
        hovertemplate="<b>%{text}</b><br>Capacity: %{marker.color} MW<extra></extra>",
        name="Substations",
    ))

    fig.update_layout(
        title="Power Grid — Substations & Flow",
        map=dict(
            style="carto-darkmatter",
            center={"lat": CENTRE_LAT, "lon": CENTRE_LON},
            zoom=6,
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
