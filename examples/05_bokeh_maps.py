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
    GlyphRenderer,
    Legend,
    LegendItem,
)
from bokeh.palettes import RdYlBu11
from pyproj import Transformer

from data.synthetic import flood_intensity_points
from data.pgcb import pgcb_substations, pgcb_lines, VOLTAGE_COLOUR, VOLTAGE_WIDTH, NODE_COLOUR

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
    lines = pgcb_lines(voltages=(400, 230, 132))
    subs  = pgcb_substations()

    cx, cy = latlon_to_mercator([23.8], [90.4])
    output_file(os.path.join(OUTPUT, "bokeh_power_grid.html"),
                title="PGCB Transmission Network")

    p = figure(
        x_range=(cx[0] - 420_000, cx[0] + 340_000),
        y_range=(cy[0] - 380_000, cy[0] + 370_000),
        x_axis_type="mercator",
        y_axis_type="mercator",
        width=860,
        height=820,
        title="PGCB Transmission Network — 400 / 230 / 132 kV",
        tools="pan,wheel_zoom,reset",
        toolbar_location="right",
    )
    p.add_tile("CartoDB Dark Matter")

    # --- Transmission lines — one Segment renderer per voltage level ---
    line_renderers = []
    for v in (132, 230, 400):    # draw 132 first so 400 kV appears on top
        vlines = lines[lines["voltage_kv"] == v]
        if vlines.empty:
            continue
        sx, sy = latlon_to_mercator(vlines["src_lat"].values, vlines["src_lon"].values)
        dx, dy = latlon_to_mercator(vlines["dst_lat"].values, vlines["dst_lon"].values)
        src = ColumnDataSource(dict(
            x0=sx, y0=sy, x1=dx, y1=dy,
            line_name=vlines["name"].values,
            src_node=vlines["src"].values,
            dst_node=vlines["dst"].values,
            length_km=vlines["length_km"].values,
            voltage=[v] * len(vlines),
        ))
        r = p.segment(
            x0="x0", y0="y0", x1="x1", y1="y1",
            source=src,
            line_color=VOLTAGE_COLOUR[v],
            line_width=VOLTAGE_WIDTH[v] * 1.8,
            line_alpha=0.85,
        )
        line_renderers.append((f"{v} kV", [r]))

    p.add_tools(HoverTool(
        renderers=[item[1][0] for item in line_renderers],
        tooltips=[
            ("Line",    "@line_name"),
            ("Route",   "@src_node → @dst_node"),
            ("Voltage", "@voltage kV"),
            ("Length",  "@length_km km"),
        ],
    ))

    # --- Nodes — scatter per node_type ---
    _TYPE_LABEL = {
        "substation":   "Substation",
        "thermal_pp":   "Thermal PP",
        "hydro_pp":     "Hydro PP",
        "renewable_pp": "Renewable PP",
        "hvdc_btp":     "HVDC BtB",
    }
    node_renderers = []
    for ntype, label in _TYPE_LABEL.items():
        subset = subs[subs["node_type"] == ntype]
        if subset.empty:
            continue
        xs, ys = latlon_to_mercator(subset["lat"].values, subset["lon"].values)
        sizes = (subset["capacity_mva"].apply(
            lambda c: max(6, min(22, c ** 0.5 * 0.9)) if c > 0 else 7
        ).values)
        nsrc = ColumnDataSource(dict(
            x=xs, y=ys,
            name=subset["name"].values,
            node_type=subset["node_type"].values,
            capacity=subset["capacity_mva"].values,
            zone=subset["zone"].values,
            size=sizes,
        ))
        r = p.scatter(
            "x", "y",
            source=nsrc,
            size="size",
            fill_color=NODE_COLOUR[ntype],
            line_color="white",
            line_width=0.6,
            fill_alpha=0.95,
        )
        node_renderers.append((label, [r]))

    p.add_tools(HoverTool(
        renderers=[item[1][0] for item in node_renderers],
        tooltips=[
            ("Name",     "@name"),
            ("Type",     "@node_type"),
            ("Zone",     "@zone"),
            ("Capacity", "@capacity MVA"),
        ],
    ))

    # --- Legend ---
    legend = Legend(
        items=[LegendItem(label=lbl, renderers=r) for lbl, r in line_renderers + node_renderers],
        location="bottom_right",
        background_fill_color="rgba(20,20,20,0.8)",
        label_text_color="white",
        border_line_color="#555",
        title="PGCB Grid",
        title_text_color="white",
    )
    p.add_layout(legend)

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
