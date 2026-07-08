#!/usr/bin/env python3
"""
Build assets/data/radial_density.json — the data behind the interactive, animated version of
the paper's Figure 5 ("Rescaled radial probability densities").

For every city it stores the four census-year radial probability densities ρ(r) on the SAME
2020-remoteness x-axis (paper convention), plus the cumulative urban-expansion factor G(year)
from 1990. The web component animates the paper's scaling relation
    ρ(r, t_j) = (1/Φ_ij) · ρ(r/Φ_ij, t_i)      (main.tex eq:rho_scaling)
i.e. a self-similar radial stretch x→x·s, ρ→ρ/s with s = G(min(τ,y))/G(y): at τ=1990 all four
years collapse onto the 1990 shape, each freezes at its true shape when τ reaches its year.

Reproduces `radial_f_collapse_single(..., func="rho")` (src/depopulation/r_scaling.py:246-290):
    rem_s = P_2020**0.5 ; idx = searchsorted(cdf_y, 1.0)
    x_y = r_ring[:idx+1] / rem_s        (remoteness)
    y_y = rho_y[:idx+1] * rem_s         (pdf, ∫ y dx = 1 in remoteness units)
G is the cumulative product of the consecutive-period expansion factors Φ (column `L` of
outputs/scaling_factors.csv): G[1990]=1, G[2000]=Φ(90-00), G[2010]=…·Φ(00-10), G[2020]=…·Φ(10-20).

RUN WITH THE ANALYSIS REPO'S INTERPRETER (numpy/pandas + the depopulation package):
  /Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python scripts/build_radial_density.py
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
import pandas as pd  # noqa: E402
from depopulation.radial_f import load_radial_f, gen_pop_ar  # noqa: E402

OUT = os.path.join(PROJECT, "assets", "data", "radial_density.json")
YEARS = (1990, 2000, 2010, 2020)
BETA = 0.5
MAXN = 170  # max points kept per curve (downsample; curves are smooth)


def downsample(x, y):
    n = len(x)
    if n <= MAXN:
        return x, y, 0
    idx = np.unique(np.linspace(0, n - 1, MAXN).round().astype(int))
    return x[idx], y[idx], n - len(idx)


def main():
    cve_names = json.load(open(os.path.join(ANALYSIS_REPO, "data", "cve_code_names.json")))
    cve_list = list(cve_names.keys())
    assert len(cve_list) == 69, f"expected 69 cities, got {len(cve_list)}"

    radial_f = load_radial_f(cve_list, Path(ANALYSIS_REPO) / "outputs" / "radial_f", core=True)
    N_c = gen_pop_ar(cve_list, Path(ANALYSIS_REPO) / "outputs" / "radial_f")

    # consecutive-period expansion factors Φ (column L), keyed by (CVE_MET, period)
    sf = pd.read_csv(os.path.join(ANALYSIS_REPO, "outputs", "scaling_factors.csv"))
    cve_col = sf.columns[0]  # "CVE_MET"
    consec = {"2000": "1990-2000", "2010": "2000-2010", "2020": "2010-2020"}
    phi = {}
    for _, row in sf.iterrows():
        if row["period"] in consec.values():
            phi[(row[cve_col], row["period"])] = float(row["L"])

    out = {}
    dropped = 0
    g2020 = []
    for i, cve in enumerate(cve_list):
        rf = radial_f[cve]
        rem_s = float(N_c[i, 3]) ** BETA  # sqrt(P_2020)
        r_ring = np.asarray(rf["r_ring"])

        # cumulative expansion factor from 1990
        p01 = phi[(cve, "1990-2000")]
        p12 = phi[(cve, "2000-2010")]
        p23 = phi[(cve, "2010-2020")]
        # Φ may be <1 (paper: cities that contract toward the centre), so G is not
        # necessarily monotonic — only require positive, finite factors.
        G = {"1990": 1.0, "2000": p01, "2010": p01 * p12, "2020": p01 * p12 * p23}
        assert all(np.isfinite(v) and v > 0 for v in G.values()), f"{cve}: bad G {G}"
        g2020.append(G["2020"])

        years = {}
        for y in YEARS:
            cdf = np.asarray(rf[f"cdf_{y}"])
            rho = np.asarray(rf[f"rho_{y}"])
            idx = int(np.searchsorted(cdf, 1.0))
            x = r_ring[: idx + 1] / rem_s        # remoteness
            yv = rho[: idx + 1] * rem_s          # pdf in remoteness units
            xd, yd, drop = downsample(x, yv)
            dropped += drop
            years[str(y)] = {
                "x": [round(float(v), 4) for v in xd],
                "y": [round(float(v), 6) for v in yd],
            }
        out[cve] = {"G": {k: round(v, 5) for k, v in G.items()}, "years": years}

    # ---- validate ----
    for cve, rec in out.items():
        assert set(rec["years"]) == {"1990", "2000", "2010", "2020"}, cve
        for y, yr in rec["years"].items():
            xs, ys = np.array(yr["x"]), np.array(yr["y"])
            assert len(xs) == len(ys) >= 2 and np.all(np.isfinite(xs)) and np.all(np.isfinite(ys)), f"{cve} {y}"
            integ = float(np.trapz(ys, xs))
            assert 0.9 < integ < 1.1, f"{cve} {y}: ∫ρ dr = {integ:.3f} (expected ≈1)"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    kb = round(len(open(OUT).read()) / 1024)
    g2020 = np.array(g2020)
    npts = np.mean([len(rec["years"]["2020"]["x"]) for rec in out.values()])
    print(f"Wrote {len(out)} cities -> {OUT}  ({kb} KB, ~{npts:.0f} pts/curve, downsampled {dropped} pts)")
    print(f"G[2020] (expansion 1990->2020): min {g2020.min():.2f} | median {np.median(g2020):.2f} | max {g2020.max():.2f}")
    print(f"CDMX G: {out['09.1.01']['G']} | Colima G: {out['06.1.01']['G']}")


if __name__ == "__main__":
    main()
