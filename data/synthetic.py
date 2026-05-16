"""
Synthetic datasets for map visualization examples.

Three domain themes, all centred on Bangladesh (a geographically rich, compact area):
  - Power grid: substations + flow arcs with load magnitude
  - Population: district-level density grid
  - Hydrology: river network paths + flood-zone intensity
"""

import numpy as np
import pandas as pd
from shapely.geometry import Point, LineString, Polygon
import geopandas as gpd

RNG = np.random.default_rng(42)

# Bounding box: Bangladesh ± small buffer
LAT_MIN, LAT_MAX = 20.7, 26.7
LON_MIN, LON_MAX = 88.0, 92.7


# ---------------------------------------------------------------------------
# Power grid
# ---------------------------------------------------------------------------

SUBSTATION_NAMES = [
    "Dhaka North", "Dhaka South", "Chittagong", "Sylhet", "Rajshahi",
    "Khulna", "Barisal", "Mymensingh", "Comilla", "Rangpur",
    "Jessore", "Bogra", "Dinajpur", "Pabna", "Noakhali",
]

def substations() -> pd.DataFrame:
    """15 synthetic substations with lat/lon and capacity (MW)."""
    lats = RNG.uniform(LAT_MIN + 0.5, LAT_MAX - 0.5, len(SUBSTATION_NAMES))
    lons = RNG.uniform(LON_MIN + 0.5, LON_MAX - 0.5, len(SUBSTATION_NAMES))
    caps = RNG.integers(100, 1200, len(SUBSTATION_NAMES))
    return pd.DataFrame({
        "name": SUBSTATION_NAMES,
        "lat": lats,
        "lon": lons,
        "capacity_mw": caps,
    })


def power_flows(n_arcs: int = 25) -> pd.DataFrame:
    """Random directed arcs between substations with a load (MW) value."""
    subs = substations()
    src_idx = RNG.integers(0, len(subs), n_arcs)
    dst_idx = RNG.integers(0, len(subs), n_arcs)
    # avoid self-loops
    mask = src_idx == dst_idx
    dst_idx[mask] = (dst_idx[mask] + 1) % len(subs)

    return pd.DataFrame({
        "src_name": subs["name"].iloc[src_idx].values,
        "src_lat":  subs["lat"].iloc[src_idx].values,
        "src_lon":  subs["lon"].iloc[src_idx].values,
        "dst_name": subs["name"].iloc[dst_idx].values,
        "dst_lat":  subs["lat"].iloc[dst_idx].values,
        "dst_lon":  subs["lon"].iloc[dst_idx].values,
        "load_mw":  RNG.integers(20, 800, n_arcs),
    })


# ---------------------------------------------------------------------------
# Population density
# ---------------------------------------------------------------------------

DISTRICTS = [
    ("Dhaka",        23.81, 90.41, 44500),
    ("Chittagong",   22.34, 91.83,  2720),
    ("Sylhet",       24.90, 91.87,   870),
    ("Rajshahi",     24.37, 88.60,  1275),
    ("Khulna",       22.83, 89.55,   800),
    ("Barisal",      22.70, 90.37,   820),
    ("Mymensingh",   24.75, 90.41,  2360),
    ("Comilla",      23.46, 91.18,  4500),
    ("Rangpur",      25.74, 89.27,  1740),
    ("Jessore",      23.17, 89.21,   900),
    ("Bogra",        24.85, 89.37,  1200),
    ("Dinajpur",     25.63, 88.64,   600),
    ("Pabna",        24.00, 89.23,  1100),
    ("Noakhali",     22.87, 91.10,  1900),
    ("Cox's Bazar",  21.44, 92.01,   500),
    ("Tangail",      24.25, 89.92,  1600),
    ("Narsingdi",    23.92, 90.72,  3200),
    ("Gazipur",      23.98, 90.41,  3900),
    ("Narayanganj",  23.62, 90.50,  6800),
    ("Faridpur",     23.60, 89.83,  1050),
]

def population_grid() -> pd.DataFrame:
    """
    ~2000 points sampling population density across districts.
    Each point has lat, lon, density (people / km²).
    """
    rows = []
    for name, clat, clon, peak_density in DISTRICTS:
        n = max(40, int(peak_density / 200))
        lats = RNG.normal(clat, 0.3, n)
        lons = RNG.normal(clon, 0.3, n)
        densities = np.clip(
            RNG.normal(peak_density, peak_density * 0.3, n), 50, peak_density * 1.8
        )
        for la, lo, d in zip(lats, lons, densities):
            rows.append({"district": name, "lat": la, "lon": lo, "density": d})
    return pd.DataFrame(rows)


def district_polygons() -> gpd.GeoDataFrame:
    """Approximate district bounding polygons as rough rectangles."""
    records = []
    for name, clat, clon, peak_density in DISTRICTS:
        half_w = RNG.uniform(0.2, 0.6)
        half_h = RNG.uniform(0.2, 0.5)
        poly = Polygon([
            (clon - half_w, clat - half_h),
            (clon + half_w, clat - half_h),
            (clon + half_w, clat + half_h),
            (clon - half_w, clat + half_h),
        ])
        records.append({
            "district": name,
            "geometry": poly,
            "density": peak_density,
            "population": int(peak_density * RNG.uniform(800, 2500)),
        })
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


# ---------------------------------------------------------------------------
# Hydrology
# ---------------------------------------------------------------------------

def river_network() -> gpd.GeoDataFrame:
    """
    Synthetic river segments as LineStrings flowing roughly south / south-west.
    Each segment has a flow_rate (m³/s) and a river name.
    """
    rivers = {
        "Padma":    [(24.8, 88.7), (24.2, 89.3), (23.7, 89.9), (23.2, 90.5), (22.8, 90.8)],
        "Meghna":   [(24.5, 91.0), (24.0, 90.9), (23.5, 90.7), (23.0, 90.8), (22.6, 90.9)],
        "Jamuna":   [(25.2, 89.8), (24.8, 89.9), (24.3, 89.7), (23.8, 89.8), (23.4, 89.9)],
        "Brahmaputra": [(26.2, 90.1), (25.7, 90.0), (25.3, 89.9), (24.9, 89.8)],
        "Surma":    [(24.9, 91.9), (24.7, 91.6), (24.4, 91.3), (24.2, 91.0)],
        "Karnaphuli": [(22.8, 92.2), (22.4, 91.9), (22.2, 91.7)],
    }
    base_flows = {"Padma": 15000, "Meghna": 8000, "Jamuna": 20000,
                  "Brahmaputra": 18000, "Surma": 3000, "Karnaphuli": 2500}
    records = []
    for name, coords in rivers.items():
        # convert (lat, lon) → (lon, lat) for shapely
        geom = LineString([(lo, la) for la, lo in coords])
        records.append({
            "river": name,
            "geometry": geom,
            "flow_rate": int(base_flows[name] * RNG.uniform(0.8, 1.2)),
            "length_km": int(len(coords) * RNG.uniform(80, 140)),
        })
    return gpd.GeoDataFrame(records, crs="EPSG:4326")


def flood_intensity_points(n: int = 800) -> pd.DataFrame:
    """
    Points representing flood/inundation intensity (0–1 scale).
    Concentrated along river corridors.
    """
    # sample near river centrelines
    river_centres = [
        (23.5, 90.2), (23.8, 90.8), (24.3, 89.8),
        (22.9, 90.7), (24.6, 91.4), (22.5, 91.8),
    ]
    rows = []
    per_centre = n // len(river_centres)
    for clat, clon in river_centres:
        lats = RNG.normal(clat, 0.4, per_centre)
        lons = RNG.normal(clon, 0.3, per_centre)
        intensity = np.clip(RNG.exponential(0.35, per_centre), 0, 1)
        for la, lo, iv in zip(lats, lons, intensity):
            rows.append({"lat": la, "lon": lo, "intensity": iv})
    return pd.DataFrame(rows)


def flood_time_series(n_steps: int = 12) -> pd.DataFrame:
    """
    Hourly snapshots of flood extent — used for animated maps.
    Returns a long-form DataFrame: step, lat, lon, intensity.
    """
    base = flood_intensity_points(300)
    frames = []
    for step in range(n_steps):
        df = base.copy()
        # intensity grows then recedes like a real flood pulse
        factor = np.sin(np.pi * step / (n_steps - 1))
        df["intensity"] = np.clip(df["intensity"] * (0.3 + factor * 0.9), 0, 1)
        df["step"] = step
        df["hour"] = f"T+{step:02d}h"
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Substations:", substations().shape)
    print("Power flows:", power_flows().shape)
    print("Population grid:", population_grid().shape)
    print("District polygons:", district_polygons().shape)
    print("River network:", river_network().shape)
    print("Flood intensity:", flood_intensity_points().shape)
    print("Flood time series:", flood_time_series().shape)
    print("All datasets OK.")
