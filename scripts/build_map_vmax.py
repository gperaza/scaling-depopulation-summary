#!/usr/bin/env python3
"""
Build assets/data/map_vmax.json — the colour-scale extent of each city's population-change
map, so the interactive figure can show a per-city colorbar (±vmax people per grid cell).

Each per-city map (analysis repo `scripts/figure_all_maps.py`) is drawn by
`pop_change_map(..., adjust_vmax=False)`, i.e. the diverging colour scale runs to
±vmax where **vmax = max |POB_URB_2020 − POB_URB_1990|** over the cells inside the map's
core extent (`DIST < r_disk[-1]/1000`). This replicates that computation (lines ~645–666 of
src/depopulation/radial_f.py) from the mesh.

RUN WITH THE ANALYSIS REPO'S INTERPRETER (needs geopandas/pandas + the depopulation package):
  /Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python scripts/build_map_vmax.py
"""

import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ANALYSIS_REPO = "/Users/gperaza/Drive/Research/scaling_depopulation"

sys.path.insert(0, os.path.join(ANALYSIS_REPO, "src"))
import geopandas as gpd  # noqa: E402
from depopulation.radial_f import load_radial_f  # noqa: E402

OUT = os.path.join(PROJECT, "assets", "data", "map_vmax.json")


def main():
    cve_names = json.load(open(os.path.join(ANALYSIS_REPO, "data", "cve_code_names.json")))
    cve_list = list(cve_names.keys())

    mesh = gpd.read_parquet(os.path.join(ANALYSIS_REPO, "outputs", "mesh.geoparquet"))
    radial_f = load_radial_f(cve_list, Path(ANALYSIS_REPO) / "outputs" / "radial_f", core=True)

    vmax = {}
    for cve in cve_list:
        rmax = radial_f[cve]["r_disk"][-1] / 1000.0  # core extent, km (same as figure_all_maps)
        # replicate pop_change_map's vmax computation
        mesh_met = mesh.loc[cve, ["POB_URB", "geometry"]]
        mask = mesh.loc[cve, "DIST"] < rmax
        mesh_met = mesh_met[mask]
        mesh_met = mesh_met.unstack(level=0)
        mesh_met.loc[:, ("POB_URB")] = mesh_met.loc[:, ("POB_URB")].fillna(0).values
        mesh_met.columns = [f"{a}_{b}" for a, b in mesh_met.columns]
        diff = mesh_met["POB_URB_2020"] - mesh_met["POB_URB_1990"]
        vmax[cve] = float(abs(diff).max())

    assert len(vmax) == 69, f"expected 69 cities, got {len(vmax)}"
    assert all(v > 0 for v in vmax.values()), "a city has vmax <= 0"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({cve: round(v) for cve, v in vmax.items()}, f, ensure_ascii=False)

    vals = sorted(vmax.values())
    print(f"Wrote {len(vmax)} cities -> {OUT}")
    print(f"vmax range: {vals[0]:.0f} .. {vals[-1]:.0f} | median {vals[len(vals)//2]:.0f}")
    print(f"CDMX vmax: {vmax['09.1.01']:.0f}")


if __name__ == "__main__":
    main()
