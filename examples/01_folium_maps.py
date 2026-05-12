"""
Folium map examples — four techniques in one script.

Outputs four standalone HTML files to output/:
  folium_heatmap.html        — flood intensity heatmap
  folium_choropleth.html     — district population density choropleth
  folium_power_flow.html     — power-flow polylines between substations
  folium_marker_cluster.html — clustered substation markers

Run:
    python examples/01_folium_maps.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import folium
from folium.plugins import HeatMap, MarkerCluster
import json

from data.synthetic import (
    flood_intensity_points,
    district_polygons,
    substations,
    power_flows,
)

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

CENTRE = [23.8, 90.4]   # Bangladesh


# ---------------------------------------------------------------------------
# 1. HeatMap — flood intensity
# ---------------------------------------------------------------------------

def make_heatmap():
    df = flood_intensity_points(800)
    m = folium.Map(location=CENTRE, zoom_start=7, tiles="CartoDB positron")

    heat_data = df[["lat", "lon", "intensity"]].values.tolist()
    HeatMap(
        heat_data,
        min_opacity=0.3,
        radius=18,
        blur=15,
        gradient={0.2: "blue", 0.5: "lime", 0.8: "orange", 1.0: "red"},
    ).add_to(m)

    folium.LayerControl().add_to(m)
    path = os.path.join(OUTPUT, "folium_heatmap.html")
    m.save(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. Choropleth — district population density
# ---------------------------------------------------------------------------

def make_choropleth():
    gdf = district_polygons()
    geojson = json.loads(gdf.to_json())

    m = folium.Map(location=CENTRE, zoom_start=7, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=geojson,
        data=gdf,
        columns=["district", "density"],
        key_on="feature.properties.district",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.4,
        legend_name="Population density (people / km²)",
        highlight=True,
    ).add_to(m)

    # tooltip on hover
    style = lambda _: {"fillColor": "transparent", "color": "transparent"}
    highlight = lambda _: {"fillColor": "#ffff00", "color": "#666", "weight": 2}
    folium.GeoJson(
        geojson,
        style_function=style,
        highlight_function=highlight,
        tooltip=folium.GeoJsonTooltip(
            fields=["district", "density", "population"],
            aliases=["District", "Density (p/km²)", "Population"],
        ),
    ).add_to(m)

    path = os.path.join(OUTPUT, "folium_choropleth.html")
    m.save(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 3. PolyLine — power flow arcs
# ---------------------------------------------------------------------------

def make_power_flow():
    flows = power_flows(25)
    m = folium.Map(location=CENTRE, zoom_start=7, tiles="CartoDB dark_matter")

    max_load = flows["load_mw"].max()

    for _, row in flows.iterrows():
        weight = 1 + 7 * row["load_mw"] / max_load
        opacity = 0.4 + 0.5 * row["load_mw"] / max_load
        folium.PolyLine(
            locations=[(row["src_lat"], row["src_lon"]),
                       (row["dst_lat"], row["dst_lon"])],
            weight=weight,
            color="#ff9900",
            opacity=opacity,
            tooltip=(
                f"{row['src_name']} → {row['dst_name']}<br>"
                f"Load: {row['load_mw']} MW"
            ),
        ).add_to(m)

    # substation markers
    subs = substations()
    for _, sub in subs.iterrows():
        folium.CircleMarker(
            location=[sub["lat"], sub["lon"]],
            radius=5,
            color="#00ccff",
            fill=True,
            fill_color="#00ccff",
            fill_opacity=0.9,
            tooltip=f"{sub['name']} — {sub['capacity_mw']} MW",
        ).add_to(m)

    path = os.path.join(OUTPUT, "folium_power_flow.html")
    m.save(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 4. MarkerCluster — substation density
# ---------------------------------------------------------------------------

def make_marker_cluster():
    subs = substations()
    m = folium.Map(location=CENTRE, zoom_start=7)

    cluster = MarkerCluster(name="Substations").add_to(m)

    for _, sub in subs.iterrows():
        popup = folium.Popup(
            f"<b>{sub['name']}</b><br>Capacity: {sub['capacity_mw']} MW",
            max_width=200,
        )
        folium.Marker(
            location=[sub["lat"], sub["lon"]],
            popup=popup,
            tooltip=sub["name"],
            icon=folium.Icon(color="orange", icon="bolt", prefix="fa"),
        ).add_to(cluster)

    folium.LayerControl().add_to(m)
    path = os.path.join(OUTPUT, "folium_marker_cluster.html")
    m.save(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building Folium maps...")
    make_heatmap()
    make_choropleth()
    make_power_flow()
    make_marker_cluster()
    print("Done. Open the HTML files in output/ in any browser.")
