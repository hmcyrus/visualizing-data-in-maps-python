# Visualizing Data in Maps — Python

A hands-on exploration of the Python geospatial visualization landscape across three real-world domains:

| Domain | Data type |
|---|---|
| **Power grid** | Substation locations + directed flow arcs with load magnitude |
| **Population** | District-level density (choropleth + 3D columns) |
| **Hydrology** | River networks, flood intensity heatmaps, animated progression |

All data is synthetic but geographically realistic (Bangladesh bounding box).

---

## Library Landscape

| Library | Style | Best for |
|---|---|---|
| **Folium** | Interactive HTML | Quick prototypes, Leaflet.js under the hood |
| **Plotly** | Interactive HTML | Publication quality, animations, Dash integration |
| **PyDeck** | Interactive HTML | Big data (WebGL), 3D layers, ArcLayer |
| **GeoPandas + contextily** | Static PNG | GIS workflows, spatial joins, publication figures |
| **Bokeh** | Interactive HTML | Linked plots, BI dashboards |
| **Streamlit** | Web app | Deployment layer wrapping any of the above |

---

## Quick Start

```bash
pip install -r requirements.txt
```

### Run individual examples

```bash
# Folium — heatmap, choropleth, power flow, marker cluster
python examples/01_folium_maps.py

# Plotly — choropleth, scatter map, animated flood
python examples/02_plotly_maps.py

# PyDeck — ArcLayer, HeatmapLayer, ColumnLayer, GeoJsonLayer, ScreenGridLayer
python examples/03_pydeck_layers.py

# GeoPandas + contextily — static PNGs
python examples/04_geopandas_static.py

# Bokeh — tile map with linked tooltips
python examples/05_bokeh_maps.py
```

All HTML/PNG outputs land in `output/` and can be opened directly in any browser.

### Run the Streamlit dashboard

```bash
pip install streamlit-folium   # extra dependency for the Folium tab
streamlit run examples/06_streamlit_app.py
```

The dashboard lets you switch domain × library interactively from the sidebar.

---

## Project Structure

```
.
├── requirements.txt
├── data/
│   └── synthetic.py          # All dataset generators (no external data needed)
├── examples/
│   ├── 01_folium_maps.py
│   ├── 02_plotly_maps.py
│   ├── 03_pydeck_layers.py
│   ├── 04_geopandas_static.py
│   ├── 05_bokeh_maps.py
│   └── 06_streamlit_app.py
└── output/                   # Generated maps (gitignored)
```

---

## Technique Reference

### Folium (`examples/01_folium_maps.py`)

| Map | Technique | Use case |
|---|---|---|
| `folium_heatmap.html` | `HeatMap` plugin | Flood / density intensity |
| `folium_choropleth.html` | `Choropleth` | District-level statistics |
| `folium_power_flow.html` | `PolyLine` | Flow paths with width ∝ load |
| `folium_marker_cluster.html` | `MarkerCluster` | Many point features |

```python
import folium
from folium.plugins import HeatMap

m = folium.Map(location=[23.8, 90.4], zoom_start=7)
HeatMap(data).add_to(m)
m.save("map.html")
```

---

### Plotly (`examples/02_plotly_maps.py`)

| Map | Technique | Use case |
|---|---|---|
| `plotly_choropleth.html` | `px.choropleth_map` | Region-level statistics |
| `plotly_scatter_map.html` | `go.Scattermap` | Points + lines overlay |
| `plotly_flood_animation.html` | `animation_frame=` | Time-series progression |

```python
import plotly.express as px

fig = px.choropleth_map(
    df, geojson=geojson,
    locations="district", featureidkey="properties.district",
    color="density", animation_frame="hour",
)
fig.write_html("map.html")
```

---

### PyDeck (`examples/03_pydeck_layers.py`)

| Map | Layer | Use case |
|---|---|---|
| `pydeck_arc_layer.html` | `ArcLayer` | Origin → destination flows |
| `pydeck_heatmap_layer.html` | `HeatmapLayer` | Continuous density |
| `pydeck_column_layer.html` | `ColumnLayer` | 3D bars per location |
| `pydeck_geojson_layer.html` | `GeoJsonLayer` | Polygons + line geometries |
| `pydeck_screengrid_layer.html` | `ScreenGridLayer` | Pixel-space aggregation |

```python
import pydeck as pdk

layer = pdk.Layer(
    "ArcLayer",
    data=flows,
    get_source_position=["src_lon", "src_lat"],
    get_target_position=["dst_lon", "dst_lat"],
    get_width="load_mw / 100",
)
pdk.Deck(layers=[layer], initial_view_state=view_state).to_html("map.html")
```

---

### GeoPandas + contextily (`examples/04_geopandas_static.py`)

| Map | Technique |
|---|---|
| `geopandas_district_density.png` | `.plot(column=)` + `ctx.add_basemap` |
| `geopandas_river_network.png` | Line width ∝ flow rate |
| `geopandas_combined.png` | Layered overlay: polygons + points + lines |

```python
import geopandas as gpd, contextily as ctx

gdf = gpd.read_file("districts.geojson").to_crs("EPSG:3857")
ax = gdf.plot(column="density", cmap="YlOrRd", legend=True)
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron)
```

---

### Bokeh (`examples/05_bokeh_maps.py`)

| Map | Technique |
|---|---|
| `bokeh_power_grid.html` | `Segment` glyphs + `scatter` on tile map |
| `bokeh_flood_map.html` | Color-mapped scatter with `ColorBar` |

```python
from bokeh.plotting import figure
from bokeh.models import LinearColorMapper, ColorBar

p = figure(x_axis_type="mercator", y_axis_type="mercator")
p.add_tile("CartoDB Positron")
p.scatter("x", "y", source=src,
          fill_color={"field": "intensity", "transform": mapper})
```

---

### Streamlit (`examples/06_streamlit_app.py`)

Wraps all three libraries in a single app. Sidebar selects domain × library.

```bash
streamlit run examples/06_streamlit_app.py
```

Key widgets: `st.pydeck_chart`, `st.plotly_chart`, `st_folium`.

---

## Choosing the Right Library

| Requirement | Recommendation |
|---|---|
| > 500k points | PyDeck (WebGL) |
| Animated time series | Plotly `animation_frame` or Kepler.gl Trip layer |
| Origin → destination arcs | PyDeck `ArcLayer` |
| GIS processing (projections, spatial joins) | GeoPandas first, then render |
| Publish as standalone HTML | Folium or Plotly |
| Linked charts + map | Bokeh or Streamlit |
| Shareable web app | Streamlit |
| Publication figure (PNG/PDF) | GeoPandas + contextily |
