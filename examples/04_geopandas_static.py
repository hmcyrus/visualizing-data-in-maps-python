"""
GeoPandas + Matplotlib + contextily — static publication-quality maps.

Outputs four PNG files to output/:
  geopandas_district_density.png — choropleth with OpenStreetMap basemap
  geopandas_river_network.png    — river widths scaled by flow rate
  geopandas_combined.png         — overlay: districts + rivers + substations
  geopandas_power_grid.png       — PGCB 400/230/132 kV transmission network

Run:
    python examples/04_geopandas_static.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import matplotlib
matplotlib.use("Agg")   # non-interactive backend for headless rendering
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import geopandas as gpd
import contextily as ctx
import numpy as np
from shapely.geometry import Point

from data.synthetic import (
    district_polygons,
    river_network,
    substations,
    flood_intensity_points,
)
from data.pgcb import pgcb_substations, pgcb_lines, VOLTAGE_COLOUR, VOLTAGE_WIDTH, NODE_COLOUR

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(OUTPUT, exist_ok=True)

WEB_MERCATOR = "EPSG:3857"   # contextily expects Web Mercator


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------

def _add_basemap(ax, source=ctx.providers.CartoDB.Positron):
    try:
        ctx.add_basemap(ax, source=source, zoom="auto")
    except Exception:
        pass  # network may be unavailable; skip basemap silently


# ---------------------------------------------------------------------------
# 1. District density choropleth
# ---------------------------------------------------------------------------

def make_district_density():
    gdf = district_polygons().to_crs(WEB_MERCATOR)

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    gdf.plot(
        column="density",
        ax=ax,
        cmap="YlOrRd",
        alpha=0.75,
        edgecolor="white",
        linewidth=0.5,
        legend=True,
        legend_kwds={"label": "Population density (people / km²)", "shrink": 0.6},
    )
    _add_basemap(ax)

    for _, row in gdf.iterrows():
        c = row.geometry.centroid
        ax.annotate(
            row["district"],
            xy=(c.x, c.y),
            fontsize=6,
            ha="center",
            color="black",
        )

    ax.set_axis_off()
    ax.set_title("Population Density by District", fontsize=14, pad=12)

    path = os.path.join(OUTPUT, "geopandas_district_density.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. River network — line width ∝ flow rate
# ---------------------------------------------------------------------------

def make_river_network():
    rivers = river_network().to_crs(WEB_MERCATOR)
    max_flow = rivers["flow_rate"].max()

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))

    norm = mcolors.Normalize(vmin=rivers["flow_rate"].min(), vmax=max_flow)
    cmap = matplotlib.colormaps["Blues"]

    for _, row in rivers.iterrows():
        lw = 1.5 + 6 * row["flow_rate"] / max_flow
        color = cmap(norm(row["flow_rate"]))
        rivers_single = gpd.GeoDataFrame([row], crs=WEB_MERCATOR)
        rivers_single.plot(ax=ax, color=color, linewidth=lw)
        midpoint = row.geometry.interpolate(0.5, normalized=True)
        ax.annotate(
            f"{row['river']}\n{row['flow_rate']:,} m³/s",
            xy=(midpoint.x, midpoint.y),
            fontsize=7,
            color="navy",
            ha="center",
        )

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.5, label="Flow rate (m³/s)")

    _add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_axis_off()
    ax.set_title("River Network — Flow Rate", fontsize=14, pad=12)

    path = os.path.join(OUTPUT, "geopandas_river_network.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 3. Combined overlay
# ---------------------------------------------------------------------------

def make_combined():
    districts = district_polygons().to_crs(WEB_MERCATOR)
    rivers = river_network().to_crs(WEB_MERCATOR)
    subs = substations()
    subs_gdf = gpd.GeoDataFrame(
        subs,
        geometry=[Point(lo, la) for la, lo in zip(subs["lat"], subs["lon"])],
        crs="EPSG:4326",
    ).to_crs(WEB_MERCATOR)

    flood_pts = flood_intensity_points(500)
    flood_gdf = gpd.GeoDataFrame(
        flood_pts,
        geometry=[Point(lo, la) for la, lo in zip(flood_pts["lat"], flood_pts["lon"])],
        crs="EPSG:4326",
    ).to_crs(WEB_MERCATOR)

    fig, ax = plt.subplots(1, 1, figsize=(12, 14))

    # layer order: basemap → district fill → flood → rivers → substations
    districts.plot(ax=ax, color="#dde8f5", edgecolor="#9ab0cf", linewidth=0.8, alpha=0.6)

    flood_gdf.plot(
        ax=ax,
        column="intensity",
        cmap="Blues",
        markersize=4,
        alpha=0.4,
        legend=False,
    )

    max_flow = rivers["flow_rate"].max()
    for _, row in rivers.iterrows():
        lw = 1 + 4 * row["flow_rate"] / max_flow
        gpd.GeoDataFrame([row], crs=WEB_MERCATOR).plot(
            ax=ax, color="#1a6faf", linewidth=lw
        )

    subs_gdf.plot(
        ax=ax,
        column="capacity_mw",
        cmap="YlOrRd",
        markersize=subs_gdf["capacity_mw"] / 40,
        edgecolors="black",
        linewidths=0.5,
        legend=True,
        legend_kwds={"label": "Substation capacity (MW)", "shrink": 0.5},
    )

    _add_basemap(ax, source=ctx.providers.CartoDB.Positron)
    ax.set_axis_off()
    ax.set_title(
        "Combined: Districts · Flood Zones · Rivers · Substations",
        fontsize=13,
        pad=12,
    )

    path = os.path.join(OUTPUT, "geopandas_combined.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 4. PGCB transmission network
# ---------------------------------------------------------------------------

def make_power_grid():
    import matplotlib.patches as mpatches
    from shapely.geometry import LineString

    lines = pgcb_lines(voltages=(400, 230, 132))
    subs  = pgcb_substations()

    # Build line GeoDataFrame
    line_geoms = [
        LineString([(r.src_lon, r.src_lat), (r.dst_lon, r.dst_lat)])
        for _, r in lines.iterrows()
    ]
    lines_gdf = gpd.GeoDataFrame(lines, geometry=line_geoms, crs="EPSG:4326").to_crs(WEB_MERCATOR)

    # Build node GeoDataFrame
    subs_gdf = gpd.GeoDataFrame(
        subs,
        geometry=[Point(r.lon, r.lat) for _, r in subs.iterrows()],
        crs="EPSG:4326",
    ).to_crs(WEB_MERCATOR)

    fig, ax = plt.subplots(1, 1, figsize=(12, 14))

    # Lines — 132 kV drawn first so 400 kV sits on top
    for v, zorder in ((132, 1), (230, 2), (400, 3)):
        subset = lines_gdf[lines_gdf["voltage_kv"] == v]
        if subset.empty:
            continue
        subset.plot(
            ax=ax,
            color=VOLTAGE_COLOUR[v],
            linewidth=VOLTAGE_WIDTH[v],
            alpha=0.88,
            zorder=zorder,
        )

    # Nodes — substations first, special nodes on top
    _MARKER  = {"substation": "o", "thermal_pp": "^", "hydro_pp": "D",
                 "renewable_pp": "s", "hvdc_btp": "*"}
    _MSIZE   = {"substation": 22,  "thermal_pp": 70,  "hydro_pp": 65,
                 "renewable_pp": 55, "hvdc_btp": 130}
    _ZORDER  = {"substation": 10,  "thermal_pp": 11,  "hydro_pp": 12,
                 "renewable_pp": 12, "hvdc_btp": 13}

    for ntype in ("substation", "thermal_pp", "hydro_pp", "renewable_pp", "hvdc_btp"):
        subset = subs_gdf[subs_gdf["node_type"] == ntype]
        if subset.empty:
            continue
        subset.plot(
            ax=ax,
            color=NODE_COLOUR[ntype],
            markersize=_MSIZE[ntype],
            marker=_MARKER[ntype],
            edgecolors="white",
            linewidths=0.5,
            alpha=0.95,
            zorder=_ZORDER[ntype],
        )

    _add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter)

    # Legend
    line_handles = [
        mpatches.Patch(color=VOLTAGE_COLOUR[400], label="400 kV"),
        mpatches.Patch(color=VOLTAGE_COLOUR[230], label="230 kV"),
        mpatches.Patch(color=VOLTAGE_COLOUR[132], label="132 kV"),
    ]
    node_handles = [
        plt.Line2D([0], [0], marker="o", color="none",
                   markerfacecolor=NODE_COLOUR["substation"],   markersize=7,  label="Substation"),
        plt.Line2D([0], [0], marker="^", color="none",
                   markerfacecolor=NODE_COLOUR["thermal_pp"],   markersize=9,  label="Thermal PP"),
        plt.Line2D([0], [0], marker="D", color="none",
                   markerfacecolor=NODE_COLOUR["hydro_pp"],     markersize=8,  label="Hydro PP"),
        plt.Line2D([0], [0], marker="*", color="none",
                   markerfacecolor=NODE_COLOUR["hvdc_btp"],     markersize=12, label="HVDC BtB"),
    ]
    leg = ax.legend(
        handles=line_handles + node_handles,
        loc="lower right",
        framealpha=0.85,
        facecolor="#1a1a2e",
        labelcolor="white",
        edgecolor="#444",
        fontsize=9,
        title="PGCB Grid",
        title_fontsize=10,
    )
    leg.get_title().set_color("white")

    ax.set_axis_off()
    ax.set_title(
        "PGCB Transmission Network — 400 / 230 / 132 kV",
        fontsize=14, pad=12,
    )

    path = os.path.join(OUTPUT, "geopandas_power_grid.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building GeoPandas / matplotlib maps...")
    make_district_density()
    make_river_network()
    make_combined()
    make_power_grid()
    print("Done. PNG files saved in output/.")
