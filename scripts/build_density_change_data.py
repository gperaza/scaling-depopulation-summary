#!/usr/bin/env python3
"""
Build assets/data/density_change.json — the data behind the interactive version of the
paper's Figure 3a: change in radial POINT density Δσ = σ(2020) − σ(1990) (people/km²) vs.
remoteness r, one line per city + a population-weighted national trend.

This reproduces `plot_delta_density(..., avg=False, scale=True, xlim=10, agg=True,
rem_year=2020, beta=0.5)` from the analysis repo's src/depopulation/radial_f.py (lines
~781–895) — using the repo's own `load_radial_f(core=True)` rather than reimplementing the
`core` first-zero truncation.

RUN WITH THE ANALYSIS REPO'S INTERPRETER (has numpy/pandas + the depopulation package):
  /Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python \
      scripts/build_density_change_data.py
"""

import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ANALYSIS_REPO = "/Users/gperaza/Drive/Research/scaling_depopulation"

sys.path.insert(0, os.path.join(ANALYSIS_REPO, "src"))
import numpy as np  # noqa: E402
from depopulation.radial_f import load_radial_f  # noqa: E402

OUT = os.path.join(PROJECT, "assets", "data", "density_change.json")
YEARS = (1990, 2000, 2010, 2020)
POP_REF = 1e6
BETA = 0.5
XLIM = 10
REM_YEAR = 2020


def main():
    cve_names = json.load(open(os.path.join(ANALYSIS_REPO, "data", "cve_code_names.json")))
    cve_list = list(cve_names.keys())
    assert len(cve_list) == 69, f"expected 69 cities, got {len(cve_list)}"

    radial_f = load_radial_f(cve_list, Path(ANALYSIS_REPO) / "outputs" / "radial_f", core=True)

    r_grid = np.linspace(0.0, XLIM, 100)
    delta_r = r_grid[1] - r_grid[0]
    j = YEARS.index(REM_YEAR)  # 2020 index -> same remoteness factor for all years

    area_agg = {y: np.zeros_like(r_grid) for y in YEARS}
    cumpop_agg = {y: np.zeros_like(r_grid) for y in YEARS}
    cities = {}       # point density Δσ  (avg=False)
    cities_avg = {}   # average density Δσ̄ (avg=True)

    for cve in cve_list:
        rf = radial_f[cve]
        p_ref_year = rf[f"cumpop_{REM_YEAR}"][-1]  # P(2020)
        l_factor = (POP_REF / p_ref_year) ** BETA
        s_factor = POP_REF / p_ref_year / l_factor ** 2  # == 1.0 for beta=0.5

        # scaled ring / disk distances (m -> km, then remoteness-scaled), same for all years
        r_ring_s = l_factor * rf["r_ring"] / 1e3
        r_disk_s = l_factor * rf["r_disk"] / 1e3
        # physical disk area (km²), evaluated at the scaled disk positions
        area_phys = np.pi * (rf["r_disk"][1:] / 1000.0) ** 2

        sigma = {
            y: np.interp(r_grid, r_ring_s, s_factor * rf[f"sigma_{y}"]) * 1e6 for y in YEARS
        }
        area_disk = {y: np.interp(r_grid, r_disk_s[1:], area_phys) for y in YEARS}
        cumpop = {y: np.interp(r_grid, r_disk_s[1:], rf[f"cumpop_{y}"][1:]) for y in YEARS}

        cities[cve] = sigma[2020] - sigma[1990]  # Δσ on r_grid (100 pts)
        # average density σ̄(r) = cumpop(r)/area(r); drop r=0 (zero-area) point -> r_grid[1:] (99 pts)
        cities_avg[cve] = (cumpop[2020][1:] / area_disk[2020][1:]
                           - cumpop[1990][1:] / area_disk[1990][1:])

        for y in YEARS:
            cumpop_agg[y] += cumpop[y]
            area_agg[y] += area_disk[y]

    # national point-density aggregate (avg=False): ring density from summed cumpop / summed area
    area_ring = {y: area_agg[y][1:] - area_agg[y][:-1] for y in YEARS}
    pop_ring = {y: cumpop_agg[y][1:] - cumpop_agg[y][:-1] for y in YEARS}
    x_agg = r_grid[1:] - delta_r / 2
    y_agg = pop_ring[2020] / area_ring[2020] - pop_ring[1990] / area_ring[1990]
    # national average-density aggregate (avg=True): summed cumpop / summed area, on r_grid[1:]
    r_avg = r_grid[1:]
    y_agg_avg = (cumpop_agg[2020][1:] / area_agg[2020][1:]
                 - cumpop_agg[1990][1:] / area_agg[1990][1:])

    # ---- validate ----
    allvals = np.concatenate([v for v in cities.values()] + [y_agg]
                             + [v for v in cities_avg.values()] + [y_agg_avg])
    if not np.all(np.isfinite(allvals)):
        sys.exit("non-finite density values encountered")
    for cve in cve_list:
        assert len(cities[cve]) == 100 and len(cities_avg[cve]) == 99, f"{cve}: bad length"
    assert len(y_agg) == 99 and len(x_agg) == 99 and len(y_agg_avg) == 99 and len(r_avg) == 99

    def rr(a, nd=1):
        return [round(float(v), nd) for v in a]

    out = {
        "point": {
            "r": rr(r_grid, 4),
            "national": {"x": rr(x_agg, 4), "y": rr(y_agg)},
            "cities": {cve: rr(arr) for cve, arr in cities.items()},
        },
        "avg": {
            "r": rr(r_avg, 4),
            "national": {"y": rr(y_agg_avg)},
            "cities": {cve: rr(arr) for cve, arr in cities_avg.items()},
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    pt = np.concatenate([v for v in cities.values()])
    av = np.concatenate([v for v in cities_avg.values()])
    print(f"Wrote {len(cities)} cities (point + avg density) -> {OUT}")
    print(f"POINT  per-city Δσ  range: {pt.min():.0f} .. {pt.max():.0f} | national "
          f"{y_agg.min():.0f} .. {y_agg.max():.0f}, r<3 mean {y_agg[x_agg < 3].mean():.0f}, "
          f"cross r≈{x_agg[np.argmin(np.abs(y_agg))]:.1f}")
    print(f"AVG    per-city Δσ̄ range: {av.min():.0f} .. {av.max():.0f} | national "
          f"{y_agg_avg.min():.0f} .. {y_agg_avg.max():.0f}, r<3 mean {y_agg_avg[r_avg < 3].mean():.0f}, "
          f"cross r≈{r_avg[np.argmin(np.abs(y_agg_avg))]:.1f}")


if __name__ == "__main__":
    main()
