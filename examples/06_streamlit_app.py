"""
Streamlit dashboard — multi-layer map explorer.

Combines all three domains (power grid, population, hydrology) into a single
interactive app with sidebar controls.

Run:
    streamlit run examples/06_streamlit_app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import pydeck as pdk
import plotly.express as px
import folium
from streamlit_folium import st_folium   # pip install streamlit-folium
import pandas as pd
import json

from data.synthetic import (
    substations,
    power_flows,
    population_grid,
    district_polygons,
    river_network,
    flood_intensity_points,
    flood_time_series,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Map Visualization Explorer",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Map Visualization Explorer")
st.caption("Bangladesh domain — power grid · population · hydrology")

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Controls")

    domain = st.selectbox(
        "Domain",
        ["Power Grid", "Population Density", "Hydrology"],
    )

    library = st.selectbox(
        "Library",
        ["PyDeck", "Plotly", "Folium"],
    )

    if domain == "Power Grid":
        n_arcs = st.slider("Number of flow arcs", 5, 40, 20)
    elif domain == "Hydrology":
        n_flood_pts = st.slider("Flood sample points", 200, 1000, 500, step=100)
        animate = st.checkbox("Animate flood progression", value=False)

    show_basemap_info = st.checkbox("Show library notes", value=True)

# ---------------------------------------------------------------------------
# Cached data
# ---------------------------------------------------------------------------

@st.cache_data
def get_flows(n):
    return power_flows(n)

@st.cache_data
def get_pop_grid():
    return population_grid()

@st.cache_data
def get_districts():
    return district_polygons()

@st.cache_data
def get_rivers():
    return river_network()

@st.cache_data
def get_flood(n):
    return flood_intensity_points(n)

@st.cache_data
def get_flood_ts():
    return flood_time_series(12)

# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

VIEW = pdk.ViewState(latitude=23.8, longitude=90.4, zoom=6, pitch=30)


def render_power_pydeck(n_arcs):
    flows = get_flows(n_arcs)
    max_load = flows["load_mw"].max()
    flows = flows.copy()
    flows["r"] = (255 * flows["load_mw"] / max_load).astype(int)
    flows["b"] = (255 * (1 - flows["load_mw"] / max_load)).astype(int)

    arc = pdk.Layer(
        "ArcLayer",
        data=flows,
        get_source_position=["src_lon", "src_lat"],
        get_target_position=["dst_lon", "dst_lat"],
        get_source_color=[0, 180, 255, 160],
        get_target_color=["r", 80, "b", 220],
        get_width="load_mw / 100",
        pickable=True,
    )
    dots = pdk.Layer(
        "ScatterplotLayer",
        data=substations(),
        get_position=["lon", "lat"],
        get_radius=9000,
        get_fill_color=[0, 200, 255, 200],
        pickable=True,
    )
    return pdk.Deck(
        layers=[arc, dots],
        initial_view_state=VIEW,
        tooltip={"text": "{src_name} → {dst_name}\n{load_mw} MW"},
    )


def render_power_plotly(n_arcs):
    flows = get_flows(n_arcs)
    subs = substations()
    fig = px.scatter_map(
        subs, lat="lat", lon="lon",
        size="capacity_mw", color="capacity_mw",
        color_continuous_scale="Viridis",
        hover_name="name",
        zoom=6, center={"lat": 23.8, "lon": 90.4},
        map_style="carto-darkmatter",
        title="Substations (sized by capacity)",
    )
    return fig


def render_power_folium(n_arcs):
    flows = get_flows(n_arcs)
    m = folium.Map(location=[23.8, 90.4], zoom_start=7, tiles="CartoDB dark_matter")
    max_load = flows["load_mw"].max()
    for _, row in flows.iterrows():
        folium.PolyLine(
            [(row["src_lat"], row["src_lon"]), (row["dst_lat"], row["dst_lon"])],
            weight=1 + 6 * row["load_mw"] / max_load,
            color="#ff9900",
            opacity=0.6,
            tooltip=f"{row['src_name']} → {row['dst_name']}: {row['load_mw']} MW",
        ).add_to(m)
    for _, s in substations().iterrows():
        folium.CircleMarker([s["lat"], s["lon"]], radius=5,
                            color="#00ccff", fill=True,
                            tooltip=s["name"]).add_to(m)
    return m


def render_pop_pydeck():
    from data.synthetic import DISTRICTS
    import pandas as pd
    df = pd.DataFrame(
        [{"lon": c, "lat": b, "density": d, "district": a}
         for a, b, c, d in DISTRICTS]
    )
    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["lon", "lat"],
        get_elevation="density",
        elevation_scale=10,
        radius=18000,
        get_fill_color=["255 - density/200", "density/200", 80, 210],
        pickable=True,
    )
    view = pdk.ViewState(latitude=23.8, longitude=90.4, zoom=6, pitch=50, bearing=10)
    return pdk.Deck(layers=[layer], initial_view_state=view,
                    tooltip={"text": "{district}\n{density} p/km²"})


def render_pop_plotly():
    gdf = get_districts()
    geojson = json.loads(gdf.to_json())
    return px.choropleth_map(
        gdf, geojson=geojson,
        locations="district", featureidkey="properties.district",
        color="density", color_continuous_scale="YlOrRd",
        map_style="carto-positron",
        zoom=6, center={"lat": 23.8, "lon": 90.4},
        title="District Population Density",
    )


def render_pop_folium():
    import folium
    gdf = get_districts()
    geojson = json.loads(gdf.to_json())
    m = folium.Map(location=[23.8, 90.4], zoom_start=7, tiles="CartoDB positron")
    folium.Choropleth(
        geo_data=geojson,
        data=gdf,
        columns=["district", "density"],
        key_on="feature.properties.district",
        fill_color="YlOrRd",
        legend_name="Population density (p/km²)",
    ).add_to(m)
    return m


def render_hydro_pydeck(n_pts):
    df = get_flood(n_pts)
    layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        get_position=["lon", "lat"],
        get_weight="intensity",
        radiusPixels=45,
    )
    return pdk.Deck(layers=[layer], initial_view_state=VIEW)


def render_hydro_plotly(animate):
    if animate:
        df = get_flood_ts()
        return px.scatter_map(
            df, lat="lat", lon="lon",
            color="intensity", animation_frame="hour",
            size="intensity", size_max=12,
            color_continuous_scale="Blues",
            map_style="carto-positron",
            zoom=6, center={"lat": 23.8, "lon": 90.4},
            title="Flood Progression",
        )
    df = get_flood(500)
    return px.density_map(
        df, lat="lat", lon="lon", z="intensity",
        radius=18, zoom=6,
        center={"lat": 23.8, "lon": 90.4},
        map_style="carto-positron",
        title="Flood Intensity Density Map",
        color_continuous_scale="Blues",
    )


def render_hydro_folium(n_pts):
    from folium.plugins import HeatMap
    df = get_flood(n_pts)
    m = folium.Map(location=[23.8, 90.4], zoom_start=7, tiles="CartoDB positron")
    HeatMap(df[["lat", "lon", "intensity"]].values.tolist(),
            radius=18, blur=15,
            gradient={0.2: "blue", 0.5: "lime", 1.0: "red"}).add_to(m)
    return m


# ---------------------------------------------------------------------------
# Main render dispatch
# ---------------------------------------------------------------------------

col1, col2 = st.columns([4, 1])

with col1:
    if domain == "Power Grid":
        if library == "PyDeck":
            st.pydeck_chart(render_power_pydeck(n_arcs), use_container_width=True)
        elif library == "Plotly":
            st.plotly_chart(render_power_plotly(n_arcs), use_container_width=True)
        else:
            st_folium(render_power_folium(n_arcs), use_container_width=True, height=600)

    elif domain == "Population Density":
        if library == "PyDeck":
            st.pydeck_chart(render_pop_pydeck(), use_container_width=True)
        elif library == "Plotly":
            st.plotly_chart(render_pop_plotly(), use_container_width=True)
        else:
            st_folium(render_pop_folium(), use_container_width=True, height=600)

    else:  # Hydrology
        if library == "PyDeck":
            st.pydeck_chart(render_hydro_pydeck(n_flood_pts), use_container_width=True)
        elif library == "Plotly":
            st.plotly_chart(render_hydro_plotly(animate), use_container_width=True)
        else:
            st_folium(render_hydro_folium(n_flood_pts), use_container_width=True, height=600)

# ---------------------------------------------------------------------------
# Sidebar notes
# ---------------------------------------------------------------------------

if show_basemap_info:
    with col2:
        notes = {
            "PyDeck": (
                "**PyDeck** (deck.gl)\n\n"
                "- WebGL rendering — handles millions of points\n"
                "- ArcLayer, HeatmapLayer, ColumnLayer, GeoJsonLayer\n"
                "- 3D pitch & bearing\n"
                "- Best for large data + 3D effects"
            ),
            "Plotly": (
                "**Plotly**\n\n"
                "- Publication-quality aesthetics\n"
                "- Animated frames (`animation_frame=`)\n"
                "- choropleth_map, scatter_map, density_map\n"
                "- Integrates cleanly with Dash"
            ),
            "Folium": (
                "**Folium** (Leaflet.js)\n\n"
                "- Fastest to prototype\n"
                "- HeatMap, MarkerCluster, Choropleth plugins\n"
                "- Outputs standalone HTML\n"
                "- Best for quick proofs of concept"
            ),
        }
        st.markdown(notes[library])
