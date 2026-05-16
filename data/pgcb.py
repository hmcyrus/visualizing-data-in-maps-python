"""
PGCB (Power Grid Bangladesh PLC) transmission network dataset.

Substations:   ~70 key nodes with hand-assigned lat/lon from the PGCB
               765/400/230/132 kV grid map (QF-SPL-14).
Lines:         Parsed from grids-formatted.csv (PGCB, 2026).
               400 kV: all 28 lines; 230 kV: all 63; 132 kV: major corridors.

Shared colour convention (used by every example script):
    400 kV  →  #e74c3c  (red)
    230 kV  →  #3498db  (blue)
    132 kV  →  #f39c12  (amber)

Node-type colours:
    substation  →  #95a5a6  (grey)
    thermal_pp  →  #e67e22  (orange)
    hydro_pp    →  #1abc9c  (teal)
    renewable_pp→  #2ecc71  (green)
    hvdc_btp    →  #9b59b6  (purple)
"""

import os
import csv
import re
import pandas as pd

_HERE = os.path.dirname(__file__)

# ---------------------------------------------------------------------------
# Visual convention constants
# ---------------------------------------------------------------------------

VOLTAGE_COLOUR = {
    400: "#e74c3c",
    230: "#3498db",
    132: "#f39c12",
}

VOLTAGE_WIDTH = {400: 3.5, 230: 2.2, 132: 1.2}

NODE_COLOUR = {
    "substation":   "#95a5a6",
    "thermal_pp":   "#e67e22",
    "hydro_pp":     "#1abc9c",
    "renewable_pp": "#2ecc71",
    "hvdc_btp":     "#9b59b6",
}

# ---------------------------------------------------------------------------
# Substation master table
# (name, lat, lon, node_type, zone, capacity_mva)
# ---------------------------------------------------------------------------

_SUB_DATA = [
    # --- 400 kV backbone nodes ---
    ("Aminbazar",       23.877, 90.244, "substation",   "Dhaka",      1560),
    ("Meghnaghat",      23.605, 90.627, "thermal_pp",   "Dhaka",      2250),
    ("Bhulta",          23.853, 90.681, "substation",   "Dhaka",      1040),
    ("Ashuganj",        24.036, 90.983, "thermal_pp",   "Cumilla",     650),
    ("Bibiyana",        24.502, 91.620, "thermal_pp",   "Sylhet",     1040),
    ("Kaliakoir",       24.075, 90.279, "substation",   "Dhaka",      1275),
    ("Payra",           22.352, 90.419, "thermal_pp",   "Barishal",    650),
    ("Gopalganj",       23.003, 89.826, "substation",   "Khulna",     1500),
    ("Rampal",          22.600, 89.763, "thermal_pp",   "Khulna",     1040),
    ("Banskhali",       22.092, 91.963, "substation",   "Chattogram",    0),
    ("Madunaghat",      22.293, 91.836, "substation",   "Chattogram", 2250),
    ("Matarbari",       21.617, 91.867, "thermal_pp",   "Chattogram", 1200),
    ("Mirsarai",        22.868, 91.548, "substation",   "Chattogram",    0),
    ("Korerhat",        22.430, 91.985, "substation",   "Chattogram", 2000),
    ("Bogura",          24.845, 89.372, "substation",   "Rajshahi",   2250),
    ("Rahanpur",        24.758, 88.163, "substation",   "Rajshahi",   1040),
    ("Monakosa",        24.634, 88.072, "substation",   "Rajshahi",      0),
    ("Barapukuria",     25.718, 88.995, "thermal_pp",   "Rangpur",     750),
    ("Rooppur",         24.071, 89.051, "thermal_pp",   "Rajshahi",   2400),  # nuclear
    ("Cumilla",         23.481, 91.181, "substation",   "Cumilla",     675),
    ("Amtali",          22.134, 90.228, "substation",   "Barishal",      0),
    # --- 230 kV backbone nodes ---
    ("Ghorasal",        23.982, 90.469, "thermal_pp",   "Dhaka",       250),
    ("Tongi",           23.894, 90.397, "substation",   "Dhaka",         0),
    ("Ishwardi",        24.140, 88.987, "substation",   "Rajshahi",    675),
    ("Raozan",          22.489, 91.940, "substation",   "Chattogram",    0),
    ("Hathazari",       22.440, 91.790, "substation",   "Chattogram",  600),
    ("Rampura",         23.750, 90.416, "substation",   "Dhaka",         0),
    ("Haripur",         23.668, 90.672, "thermal_pp",   "Dhaka",       675),
    ("Hasnabad",        23.690, 90.709, "substation",   "Dhaka",       675),
    ("Sirajganj",       24.442, 89.718, "substation",   "Rajshahi",      0),
    ("Baghabari",       24.203, 89.548, "substation",   "Rajshahi",    525),
    ("Bheramara",       24.071, 88.988, "hvdc_btp",     "Khulna",      450),
    ("Khulna",          22.832, 89.550, "substation",   "Khulna",        0),
    ("Fenchuganj",      24.540, 91.855, "thermal_pp",   "Sylhet",      600),
    ("Faridpur",        23.604, 89.834, "substation",   "Khulna",      700),
    ("Mongla",          22.472, 89.592, "substation",   "Khulna",        0),
    ("Barishal",        22.710, 90.370, "substation",   "Barishal",    600),
    ("Siddhirganj",     23.712, 90.541, "thermal_pp",   "Dhaka",         0),
    ("Sonagazi",        22.902, 91.375, "thermal_pp",   "Cumilla",       0),
    ("Maniknagar",      23.708, 90.440, "substation",   "Dhaka",         0),
    ("Sikalbaha",       22.339, 91.797, "thermal_pp",   "Chattogram",    0),
    ("Purbasadipur",    25.638, 89.617, "substation",   "Rangpur",       0),
    ("Rajshahi",        24.366, 88.603, "substation",   "Rajshahi",      0),
    ("Maijdee",         22.849, 91.098, "substation",   "Cumilla",       0),
    ("Patuakhali",      22.352, 90.325, "substation",   "Barishal",      0),
    ("Gazaria",         23.474, 90.539, "substation",   "Dhaka",         0),
    ("Kachua",          23.178, 91.150, "substation",   "Cumilla",       0),
    ("Bhola",           22.691, 90.636, "substation",   "Barishal",      0),
    ("Noagaon",         24.781, 88.937, "substation",   "Rajshahi",      0),
    ("Chowmuhani",      22.893, 91.174, "substation",   "Cumilla",     700),
    # --- 132 kV district nodes ---
    ("Rangpur",         25.742, 89.274, "substation",   "Rangpur",       0),
    ("Saidpur",         25.782, 88.898, "substation",   "Rangpur",       0),
    ("Dinajpur",        25.628, 88.638, "substation",   "Rangpur",       0),
    ("Lalmonirhat",     25.918, 89.449, "substation",   "Rangpur",       0),
    ("Kurigram",        25.806, 89.638, "substation",   "Rangpur",       0),
    ("Jamalpur",        24.896, 89.944, "substation",   "Mymensingh",    0),
    ("Sherpur",         25.019, 90.014, "substation",   "Mymensingh",    0),
    ("Mymensingh",      24.749, 90.407, "substation",   "Mymensingh",    0),
    ("Netrokona",       24.873, 90.728, "substation",   "Mymensingh",    0),
    ("Kishoreganj",     24.444, 90.781, "substation",   "Mymensingh",    0),
    ("Sylhet",          24.899, 91.872, "substation",   "Sylhet",        0),
    ("Sunamganj",       25.059, 91.403, "substation",   "Sylhet",        0),
    ("Kulaura",         24.533, 92.031, "substation",   "Sylhet",        0),
    ("Brahmanbaria",    23.958, 91.106, "substation",   "Cumilla",       0),
    ("Narsingdi",       23.920, 90.715, "substation",   "Dhaka",         0),
    ("Joydevpur",       23.999, 90.397, "substation",   "Dhaka",         0),
    ("Tangail",         24.249, 89.924, "substation",   "Dhaka",         0),
    ("Manikganj",       23.864, 90.001, "substation",   "Dhaka",         0),
    ("Pabna",           23.993, 89.232, "substation",   "Rajshahi",      0),
    ("Natore",          24.418, 88.998, "substation",   "Rajshahi",      0),
    ("Joypurhat",       25.099, 89.022, "substation",   "Rajshahi",      0),
    ("Chapai Nawabganj",24.590, 88.271, "substation",   "Rajshahi",      0),
    ("Naogaon",         24.813, 88.936, "substation",   "Rajshahi",      0),
    ("Chandpur",        23.222, 90.661, "substation",   "Cumilla",       0),
    ("Laksam",          23.239, 91.122, "substation",   "Cumilla",       0),
    ("Feni",            23.002, 91.397, "substation",   "Cumilla",       0),
    ("Jessore",         23.172, 89.213, "substation",   "Khulna",        0),
    ("Jhenaidah",       23.070, 89.152, "substation",   "Khulna",        0),
    ("Chuadanga",       23.638, 88.840, "substation",   "Khulna",        0),
    ("Satkhira",        22.717, 89.082, "substation",   "Khulna",        0),
    ("Bagerhat",        22.655, 89.787, "substation",   "Khulna",        0),
    ("Narail",          23.171, 89.503, "substation",   "Khulna",        0),
    ("Magura",          23.491, 89.427, "substation",   "Khulna",        0),
    ("Kaptai",          22.531, 92.218, "hydro_pp",     "Chattogram",  230),
    ("Chandraghona",    22.561, 92.202, "hydro_pp",     "Chattogram",    0),
    ("Cox's Bazar",     21.436, 92.013, "substation",   "Chattogram",    0),
    ("Khagrachari",     23.119, 91.985, "substation",   "Chattogram",    0),
    ("Rangamati",       22.732, 92.199, "substation",   "Chattogram",    0),
    ("Agrabad",         22.334, 91.828, "substation",   "Chattogram",    0),
    ("Halishahar",      22.341, 91.796, "substation",   "Chattogram",    0),
    ("Dohazari",        22.186, 91.934, "substation",   "Chattogram",    0),
    # --- Dhaka metropolitan 132 kV ring ---
    ("Uttara",          23.873, 90.361, "substation",   "Dhaka",         0),
    ("Mirpur",          23.819, 90.363, "substation",   "Dhaka",         0),
    ("Dhanmondi",       23.738, 90.380, "substation",   "Dhaka",         0),
    ("Old Airport",     23.774, 90.403, "substation",   "Dhaka",         0),
    ("Gulshan",         23.793, 90.415, "substation",   "Dhaka",         0),
    ("Shyampur",        23.706, 90.454, "substation",   "Dhaka",         0),
    ("Postogola",       23.690, 90.430, "substation",   "Dhaka",         0),
    ("Kallayanpur",     23.771, 90.352, "substation",   "Dhaka",         0),
    ("Demra",           23.720, 90.464, "substation",   "Dhaka",         0),
    ("Keraniganj",      23.693, 90.395, "substation",   "Dhaka",         0),
    ("Purbachal",       23.843, 90.554, "substation",   "Dhaka",         0),
    ("Basundhara",      23.828, 90.475, "substation",   "Dhaka",         0),
    ("Rajendrapur",     24.013, 90.508, "substation",   "Dhaka",         0),
]

# ---------------------------------------------------------------------------
# Name aliases — normalise CSV name variants to canonical names above
# ---------------------------------------------------------------------------

_ALIAS = {
    "Ashuganj(N)":              "Ashuganj",
    "Ashuganj (N)":             "Ashuganj",
    "Ashuganj N":               "Ashuganj",
    "Bogura(West)":             "Bogura",
    "Bogura(W)":                "Bogura",
    "Bogura(S)":                "Bogura",
    "Bogra":                    "Bogura",
    "BograNew":                 "Bogura",
    "BograOld":                 "Bogura",
    "Comilla(N)":               "Cumilla",
    "Comilla (N)":              "Cumilla",
    "Comilla North":            "Cumilla",
    "Cumilla(N)":               "Cumilla",
    "Comilla(S)":               "Laksam",
    "Comilla (S)":              "Laksam",
    "Cumilla(S)":               "Laksam",
    "Raojan":                   "Raozan",
    "Roopur":                   "Rooppur",
    "RNPP":                     "Rooppur",
    "RNPL":                     "Rooppur",
    "Ishurdi":                  "Ishwardi",
    "Ishurdi line":             "Ishwardi",
    "Gopalganj(N)":             "Gopalganj",
    "Gopalganj (overhead)":     "Gopalganj",
    "Gopalganj (UG)":           "Gopalganj",
    "Gopalganj N":              "Gopalganj",
    "Khulna(S)":                "Khulna",
    "Khula(S)":                 "Khulna",
    "Khula 330MW":              "Khulna",
    "Bheramara HVDC":           "Bheramara",
    "Bheramara 230":            "Bheramara",
    "Bheramana":                "Bheramara",
    "Bheramara PS":             "Bheramara",
    "Kaliakoir (Upto river crossing)": "Kaliakoir",
    "Payra PP":                 "Payra",
    "Payra SS":                 "Payra",
    "Payra (Substation)":       "Payra",
    "Madunaghat 400kV":         "Madunaghat",
    "Madunaght(O)":             "Madunaghat",
    "AES, Haripur":             "Haripur",
    "Siddhirganj 210 MW P/S":   "Siddhirganj",
    "Siddhirganj 210MW":        "Siddhirganj",
    "Aminbazar(With River)":    "Aminbazar",
    "Aminbazar River Crossing": "Aminbazar",
    "Bogura West":              "Bogura",
    "Monakosa":                 "Monakosa",
    "Bangladesh Border":        None,          # cross-border line, no local node
    "Baharampur":               None,
    "Amtali":                   "Amtali",
    "Barguna PP":               "Amtali",
    "BSRM":                     "Mirsarai",
    "Barisal":                  "Barishal",
    "Barisal(N)":               "Barishal",
    "Barishal(N)":              "Barishal",
    "Bogura 230kV":             "Bogura",
    "Old Airport (O/H)":        "Old Airport",
    "Old Airport (U/G)":        "Old Airport",
    "Noagaon (Partial)":        "Noagaon",
    "Sonagazi (EGCB)":          "Sonagazi",
    "Manaknagar":               "Maniknagar",
    "Sitalakhya":               "Siddhirganj",
    "Sreepur":                  "Joydevpur",
    "Sripur":                   "Joydevpur",
    "Lalbagh":                  "Dhanmondi",
    "Cantonment":               "Old Airport",
    "Banani":                   "Gulshan",
    "Motijheel":                "Maniknagar",
    "Narinda":                  "Maniknagar",
    "Gulshan":                  "Gulshan",
    "Uttara":                   "Uttara",
    "Mirpur":                   "Mirpur",
    "Kalurghat":                "Agrabad",
    "Halishahar":               "Halishahar",
    "Chandraghona":             "Chandraghona",
    "Dohazari":                 "Dohazari",
    "Chakaria":                 "Cox's Bazar",
    "Anowara":                  "Banskhali",
    "Kachua":                   "Kachua",
    "Faridpur":                 "Faridpur",
    "Maijdee":                  "Maijdee",
    "Chowmuhani":               "Chowmuhani",
    "Cox's Bazar":              "Cox's Bazar",
    "Khagrachari":              "Khagrachari",
    "Rangamati":                "Rangamati",
    "Sunamganj":                "Sunamganj",
    "Kulaura":                  "Kulaura",
    "Kishoreganj":              "Kishoreganj",
    "Netrokona":                "Netrokona",
    "Sherpur":                  "Sherpur",
    "Jamalpur":                 "Jamalpur",
    "Joypurhat":                "Joypurhat",
    "Naogaon":                  "Naogaon",
    "Chapai":                   "Chapai Nawabganj",
    "Chapai Nawabganj":         "Chapai Nawabganj",
    "Natore":                   "Natore",
    "Pabna":                    "Pabna",
    "Tangail":                  "Tangail",
    "Manikganj":                "Manikganj",
    "Narail":                   "Narail",
    "Magura":                   "Magura",
    "Bagerhat":                 "Bagerhat",
    "Satkhira":                 "Satkhira",
    "Chuadanga":                "Chuadanga",
    "Jhenaidah":                "Jhenaidah",
    "Jessore":                  "Jessore",
    "Jashore":                  "Jessore",
    "Rajshahi(N)":              "Rajshahi",
    "Kurigram":                 "Kurigram",
    "Lalmonirhat":              "Lalmonirhat",
    "Dinajpur":                 "Dinajpur",
    "Saidpur":                  "Saidpur",
    "Rangpur":                  "Rangpur",
    "Brahmanbaria":             "Brahmanbaria",
    "Narsingdi":                "Narsingdi",
    "Joydevpur":                "Joydevpur",
    "Feni":                     "Feni",
    "Feni(N)":                  "Feni",
    "Chandpur":                 "Chandpur",
    "Laksam":                   "Laksam",
    "Kaptai":                   "Kaptai",
    "Sylhet":                   "Sylhet",
    "Mymensingh":               "Mymensingh",
    "Baghabari":                "Baghabari",
    "Sirajganj":                "Sirajganj",
    "Purbasadipur":             "Purbasadipur",
    "Rahanpur":                 "Rahanpur",
    "Mongla":                   "Mongla",
    "Bhola":                    "Bhola",
    "Patuakhali":               "Patuakhali",
    "Gazaria":                  "Gazaria",
    "Sikalbaha":                "Sikalbaha",
    "Fenchuganj":               "Fenchuganj",
    "Maniknagar":               "Maniknagar",
}

# ---------------------------------------------------------------------------
# Build lookup dicts
# ---------------------------------------------------------------------------

def _build_lookup():
    lut = {}
    for row in _SUB_DATA:
        name, lat, lon, ntype, zone, cap = row
        lut[name] = dict(lat=lat, lon=lon, node_type=ntype, zone=zone, capacity_mva=cap)
    return lut

_LOOKUP = _build_lookup()


def _resolve(raw_name: str):
    """Return canonical name or None for cross-border / unknown nodes."""
    name = raw_name.strip()
    if name in _LOOKUP:
        return name
    if name in _ALIAS:
        return _ALIAS[name]
    # try partial / case-insensitive fallback
    name_lc = name.lower()
    for key in _LOOKUP:
        if key.lower() == name_lc:
            return key
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pgcb_substations() -> pd.DataFrame:
    """All substations in the master table as a DataFrame."""
    rows = []
    for name, lat, lon, ntype, zone, cap in _SUB_DATA:
        rows.append(dict(name=name, lat=lat, lon=lon,
                         node_type=ntype, zone=zone, capacity_mva=cap))
    return pd.DataFrame(rows)


def pgcb_lines(voltages=(400, 230, 132)) -> pd.DataFrame:
    """
    Transmission lines from grids-formatted.csv filtered to the requested
    voltage levels, with src/dst coordinates looked up from the master table.
    Rows where either endpoint is unknown (cross-border, industrial) are dropped.
    """
    path = os.path.join(_HERE, "grids-formatted.csv")
    volt_set = {f"{v} kV" for v in voltages}

    raw_rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            v_str = row["Voltage Level"].strip()
            if v_str not in volt_set:
                continue
            raw_rows.append(row)

    records = []
    for row in raw_rows:
        name = row["Name of Lines"].strip()
        v_str = row["Voltage Level"].strip()
        v_kv = int(v_str.split()[0])

        # strip leading LILO / HVDC prefixes before splitting
        clean = re.sub(
            r"^(LILO\s+of\s+|LILO\s+|Link\s+of\s+|Link\s+)", "",
            name, flags=re.IGNORECASE
        ).strip()

        # split "A-B", "A - B", "A at C", keeping parens
        parts = re.split(r"\s+-\s+|\s*-\s*(?=[A-Z(])", clean, maxsplit=1)
        if len(parts) < 2:
            continue

        raw_src = parts[0].strip()
        # strip trailing context " at X", " (overhead)", " (UG)", etc.
        raw_dst = re.split(r"\s+at\s+", parts[1], flags=re.IGNORECASE)[0].strip()

        src_canon = _resolve(raw_src)
        dst_canon = _resolve(raw_dst)
        if src_canon is None or dst_canon is None:
            continue
        if src_canon not in _LOOKUP or dst_canon not in _LOOKUP:
            continue
        if src_canon == dst_canon:
            continue

        src = _LOOKUP[src_canon]
        dst = _LOOKUP[dst_canon]

        try:
            length_km = float(row["Length in Route km"]) if row["Length in Route km"] else 0.0
        except ValueError:
            length_km = 0.0

        records.append(dict(
            name=name,
            src=src_canon,
            dst=dst_canon,
            src_lat=src["lat"], src_lon=src["lon"],
            dst_lat=dst["lat"], dst_lon=dst["lon"],
            voltage_kv=v_kv,
            length_km=length_km,
        ))

    df = pd.DataFrame(records)
    # drop exact duplicates (reversed direction is kept)
    df = df.drop_duplicates(subset=["src", "dst", "voltage_kv"])
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    subs = pgcb_substations()
    print(f"Substations : {len(subs)}")
    print(subs["node_type"].value_counts().to_string())

    for v in (400, 230, 132):
        lines = pgcb_lines(voltages=(v,))
        print(f"\n{v} kV lines resolved: {len(lines)}")
        if len(lines):
            print(lines[["name","src","dst","length_km"]].head(5).to_string(index=False))
