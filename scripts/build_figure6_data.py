#!/usr/bin/env python3
"""
Build assets/data/figure6_points.csv — the point data behind the interactive
"Figure 6" (population growth factor vs. urban expansion factor Φ).

Source (read-only, precomputed by the analysis repo's Snakemake pipeline):
  <ANALYSIS_REPO>/outputs/scaling_factors.csv   (columns: CVE_MET,_,_,q1,L,q3,min,max,
                                                 idx_max,slopes,N2_N1,t1,t2,R2,period)
    -> L      = Φ  (urban expansion factor, Theil-Sen slope)
    -> N2_N1  = population growth factor P(t2)/P(t1)
  <ANALYSIS_REPO>/data/cve_code_names.json      (CVE code -> city name)

Map images (city population-change maps) already live in this project as
  assets/images/metros/<code>2.png
and are joined by CITY NAME (the analysis CVE codes do not always match the image
codes, e.g. Chilpancingo is 12.1.01 in the analysis but 12.2.01 in the images).
The name -> image map is committed alongside the data as assets/data/city_images.json.

Pure Python standard library only — no pandas/geopandas/network needed.
"""

import csv
import json
import os
import sys

# --- paths -------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ANALYSIS_REPO = "/Users/gperaza/Drive/Research/scaling_depopulation"

SCALING_FACTORS = os.path.join(ANALYSIS_REPO, "outputs", "scaling_factors.csv")
CVE_NAMES = os.path.join(ANALYSIS_REPO, "data", "cve_code_names.json")
CITY_IMAGES = os.path.join(PROJECT, "assets", "data", "city_images.json")
OUT_CSV = os.path.join(PROJECT, "assets", "data", "figure6_points.csv")

DT10_PERIODS = {"1990-2000", "2000-2010", "2010-2020"}
# column indices in scaling_factors.csv
C_CVE, C_PHI, C_GROWTH, C_PERIOD = 0, 4, 10, 14


def load_cve_to_name(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)  # {cve: name}


def main():
    cve_to_name = load_cve_to_name(CVE_NAMES)
    name_to_image = json.load(open(CITY_IMAGES, encoding="utf-8"))  # {name: image path}

    rows_out = []
    missing_name, missing_image = set(), set()
    with open(SCALING_FACTORS, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            period = row[C_PERIOD]
            if period not in DT10_PERIODS:
                continue
            cve = row[C_CVE]
            name = cve_to_name.get(cve)
            if name is None:
                missing_name.add(cve)
                continue
            image = name_to_image.get(name)
            if image is None:
                missing_image.add(name)
                continue
            rows_out.append(
                {
                    "city_name": name,
                    "cve_code": cve,
                    "period": period.replace("-", "–"),  # en-dash
                    "growth_factor": f"{float(row[C_GROWTH]):.6f}",
                    "phi": f"{float(row[C_PHI]):.6f}",
                    "image": image,
                }
            )

    # --- validate -----------------------------------------------------------
    if missing_name:
        sys.exit(f"CVE codes with no name: {sorted(missing_name)}")
    if missing_image:
        sys.exit(f"City names with no image: {sorted(missing_image)}")
    assert len(rows_out) == 207, f"expected 207 rows, got {len(rows_out)}"
    n_cities = len({r["cve_code"] for r in rows_out})
    assert n_cities == 69, f"expected 69 cities, got {n_cities}"
    for r in rows_out:
        img_abs = os.path.join(PROJECT, r["image"])
        if not os.path.exists(img_abs):
            sys.exit(f"Missing image file: {r['image']} ({r['city_name']})")

    # --- write --------------------------------------------------------------
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fields = ["city_name", "cve_code", "period", "growth_factor", "phi", "image"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows ({n_cities} cities) -> {OUT_CSV}")


if __name__ == "__main__":
    main()
