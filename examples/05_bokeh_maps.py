"""
Bokeh tile map examples — interactive embedded maps.

Outputs two standalone HTML files to output/:
  bokeh_power_grid.html  — substations + flow lines on a tile map (linked tooltip)
  bokeh_flood_map.html   — flood intensity scatter on a tile map with color bar

Run:
    python examples/05_bokeh_maps.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
from bokeh.plotting import figure, output_file, save
from bokeh.models import (
    ColumnDataSource,
    HoverTool,
    ColorBar,
    LinearColorMapper,
    MultiLine,
    Segment,
    TileSource,
)
from bokeh.transform import linear_cmap
from bokeh.palettes import Viridis256, YlOrRd9, RdYlBu11
from pyproj import Transformer

from data.synthetic import substations, power_flows, flood_intensity_points

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

# Bokeh tile maps use Web Mercator (EPSG:3857)
_to_mercator = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def latlon_to_mercator(lats, lons):
    xs, ys = _to_mercator.transform(lons, lats)
    return xs, ys


# ---------------------------------------------------------------------------
# 1. Power grid — substations + flow lines
# ---------------------------------------------------------------------------

def make_power_grid():
    subs = substations()
    flows = power_flows(25)

    xs, ys = latlon_to_mercator(subs["lat"].values, subs["lon"].values)
    subs_src = ColumnDataSource(dict(
        x=xs, y=ys,
        name=subs["name"],
        capacity=subs["capacity_mw"],
        size=np.sqrt(subs["capacity_mw"]) * 1.5,
    ))

    # arcs as segments
    src_x, src_y = latlon_to_mercator(flows["src_lat"].values, flows["src_lon"].values)
    dst_x, dst_y = latlon_to_mercator(flows["dst_lat"].values, flows["dst_lon"].values)
    max_load = flows["load_mw"].max()
    flow_src = ColumnDataSource(dict(
        x0=src_x, y0=src_y,
        x1=dst_x, y1=dst_y,
        load=flows["load_mw"],
        src_name=flows["src_name"],
        dst_name=flows["dst_name"],
        lw=(1 + 6 * flows["load_mw"] / max_load).values,
    ))

    output_file(os.path.join(OUTPUT, "bokeh_power_grid.html"),
                title="Power Grid Map")

    p = figure(
        x_range=(-100_000 + latlon_to_mercator([23.8], [90.4])[0][0],
                  100_000 + latlon_to_mercator([23.8], [90.4])[0][0]),
        y_range=(-200_000 + latlon_to_mercator([23.8], [90.4])[1][0],
                  200_000 + latlon_to_mercator([23.8], [90.4])[1][0]),
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=800,
        height=700,
        title="Power Grid — Substations & Flow",
        tools="pan,wheel_zoom,reset,hover,tap",
        toolbar_location="right",
    )
    p.add_tile("CartoDB Dark Matter")

    # flow lines
    p.segment(
        x0="x0", y0="y0", x1="x1", y1="y1",
        source=flow_src,
        line_color="rgba(255,153,0,0.55)",
        line_width="lw",
    )

    # substation circles
    cap_mapper = LinearColorMapper(palette=Viridis256,
                                   low=subs["capacity_mw"].min(),
                                   high=subs["capacity_mw"].max())
    circles = p.scatter(
        "x", "y",
        source=subs_src,
        size="size",
        fill_color={"field": "capacity", "transform": cap_mapper},
        line_color="white",
        line_width=0.5,
        alpha=0.9,
    )
    color_bar = ColorBar(color_mapper=cap_mapper, label_standoff=8,
                         title="Capacity (MW)")
    p.add_layout(color_bar, "right")

    p.add_tools(HoverTool(renderers=[circles], tooltips=[
        ("Substation", "@name"),
        ("Capacity", "@capacity MW"),
    ]))

    path = os.path.join(OUTPUT, "bokeh_power_grid.html")
    save(p)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. Flood intensity scatter
# ---------------------------------------------------------------------------

def make_flood_map():
    df = flood_intensity_points(600)
    xs, ys = latlon_to_mercator(df["lat"].values, df["lon"].values)

    src = ColumnDataSource(dict(
        x=xs, y=ys,
        intensity=df["intensity"],
        lat=df["lat"],
        lon=df["lon"],
    ))

    output_file(os.path.join(OUTPUT, "bokeh_flood_map.html"),
                title="Flood Intensity Map")

    cx, cy = latlon_to_mercator([23.8], [90.4])
    p = figure(
        x_range=(cx[0] - 400_000, cx[0] + 400_000),
        y_range=(cy[0] - 500_000, cy[0] + 500_000),
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=800,
        height=700,
        title="Flood Intensity Distribution",
        tools="pan,wheel_zoom,reset,hover",
        toolbar_location="right",
    )
    p.add_tile("CartoDB Positron")

    mapper = LinearColorMapper(
        palette=list(reversed(RdYlBu11)),
        low=0.0,
        high=1.0,
    )

    p.scatter(
        "x", "y",
        source=src,
        size=8,
        fill_color={"field": "intensity", "transform": mapper},
        fill_alpha=0.65,
        line_color=None,
    )

    color_bar = ColorBar(color_mapper=mapper, label_standoff=8,
                         title="Intensity (0–1)")
    p.add_layout(color_bar, "right")
    p.add_tools(HoverTool(tooltips=[
        ("Lat / Lon", "@lat{0.3f} / @lon{0.3f}"),
        ("Intensity", "@intensity{0.2f}"),
    ]))

    path = os.path.join(OUTPUT, "bokeh_flood_map.html")
    save(p)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building Bokeh maps...")
    make_power_grid()
    make_flood_map()
    print("Done. Open the HTML files in output/ in any browser.")
