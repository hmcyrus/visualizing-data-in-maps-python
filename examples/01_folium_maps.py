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
)
from data.pgcb import pgcb_substations, pgcb_lines, VOLTAGE_COLOUR, VOLTAGE_WIDTH, NODE_COLOUR

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
    lines = pgcb_lines(voltages=(400, 230, 132))
    subs  = pgcb_substations()

    m = folium.Map(location=CENTRE, zoom_start=7, tiles="CartoDB dark_matter")

    # One FeatureGroup per voltage level — user can toggle each in the layer panel
    volt_groups = {}
    for v in (400, 230, 132):
        fg = folium.FeatureGroup(name=f"{v} kV lines", show=True)
        fg.add_to(m)
        volt_groups[v] = fg

    for _, row in lines.iterrows():
        v      = row["voltage_kv"]
        colour = VOLTAGE_COLOUR[v]
        weight = VOLTAGE_WIDTH[v] * 2.0
        tip = (
            f"<b>{row['src']} → {row['dst']}</b><br>"
            f"{v} kV &nbsp;|&nbsp; {row['length_km']:.0f} km"
        )
        folium.PolyLine(
            locations=[(row["src_lat"], row["src_lon"]),
                       (row["dst_lat"], row["dst_lon"])],
            weight=weight,
            color=colour,
            opacity=0.85,
            tooltip=tip,
        ).add_to(volt_groups[v])

    # Node FeatureGroups per type
    _TYPE_LABEL = {
        "substation":    "Substations",
        "thermal_pp":    "Thermal PPs",
        "hydro_pp":      "Hydro PPs",
        "renewable_pp":  "Renewable PPs",
        "hvdc_btp":      "HVDC BtB",
    }
    node_groups = {}
    for ntype, label in _TYPE_LABEL.items():
        fg = folium.FeatureGroup(name=label, show=True)
        fg.add_to(m)
        node_groups[ntype] = fg

    for _, sub in subs.iterrows():
        ntype  = sub["node_type"]
        colour = NODE_COLOUR.get(ntype, "#95a5a6")
        radius = max(4, min(11, sub["capacity_mva"] / 180)) if sub["capacity_mva"] > 0 else 5
        cap_str = f"{sub['capacity_mva']} MVA" if sub["capacity_mva"] > 0 else "—"
        tip = (
            f"<b>{sub['name']}</b><br>"
            f"{_TYPE_LABEL.get(ntype, ntype)} | {sub['zone']}<br>"
            f"Capacity: {cap_str}"
        )
        folium.CircleMarker(
            location=[sub["lat"], sub["lon"]],
            radius=radius,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.92,
            weight=1,
            tooltip=tip,
        ).add_to(node_groups.get(ntype, node_groups["substation"]))

    # Voltage legend (bottom-left HTML overlay)
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
         background:rgba(20,20,20,0.82);padding:10px 14px;border-radius:7px;
         color:#eee;font-family:sans-serif;font-size:12px;line-height:1.7;">
      <b style="font-size:13px;">Voltage Level</b><br>
      <span style="color:#e74c3c;font-size:18px;">&#9644;</span>&nbsp;400 kV<br>
      <span style="color:#3498db;font-size:18px;">&#9644;</span>&nbsp;230 kV<br>
      <span style="color:#f39c12;font-size:18px;">&#9644;</span>&nbsp;132 kV
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False).add_to(m)
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
