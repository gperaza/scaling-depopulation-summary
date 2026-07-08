#!/usr/bin/env python3
"""
Build assets/data/city_maps.json — data for the interactive 69-city map grid that
replaces static Figure 2. Each city carries its thumbnail + detail image paths and,
for the four remoteness zones, the urban population in each census year (so the map
overlay can show the population change per zone on hover).

Sources (read-only):
  assets/data/figure6_points.csv                     -> cve_code, city_name, image (detail path)
  <ANALYSIS_REPO>/outputs/pop_remoteness_brackets_long.csv  -> per cve / bracket / year POB_URB
  <ANALYSIS_REPO>/outputs/remoteness_brackets.csv    -> per-city ring radii r_3/r_5/r_9.3 (km)

Join is by cve_code (== CVE_MET). Image paths come from figure6_points' `image`
column (detail = "...2.png"; thumb = strip the trailing "2"), which stays correct
even where the image code differs from the analysis code (e.g. Chilpancingo
cve 12.1.01 but image 12.2.012.png).

Pure Python standard library only.
"""

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ANALYSIS_REPO = "/Users/gperaza/Drive/Research/scaling_depopulation"

FIG6 = os.path.join(PROJECT, "assets", "data", "figure6_points.csv")
POP = os.path.join(ANALYSIS_REPO, "outputs", "pop_remoteness_brackets_long.csv")
RADII = os.path.join(ANALYSIS_REPO, "outputs", "remoteness_brackets.csv")
OUT = os.path.join(PROJECT, "assets", "data", "city_maps.json")

YEARS = ["1990", "2000", "2010", "2020"]
# analysis bracket label -> our zone key
BRACKET_ZONE = {"inner": "central", "mid": "intermediate", "distant": "distant", "outmost": "periurban"}
ZONE_ORDER = ["central", "intermediate", "distant", "periurban"]


def thumb_from_detail(detail):
    base, ext = os.path.splitext(detail)  # ".../09.1.012", ".png"
    return (base[:-1] + ext) if base.endswith("2") else detail


def main():
    # 1. cities from figure6_points (dedupe by cve)
    cities = {}
    with open(FIG6, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            cve = r["cve_code"]
            if cve not in cities:
                cities[cve] = {"cve": cve, "name": r["city_name"],
                               "detail": r["image"], "thumb": thumb_from_detail(r["image"])}
    assert len(cities) == 69, f"expected 69 cities, got {len(cities)}"

    # 2. per-zone population per year
    pop = {}  # cve -> zone -> {year: POB_URB}
    with open(POP, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            zone = BRACKET_ZONE.get(r["bracket"])
            if zone is None:
                sys.exit(f"unknown bracket: {r['bracket']}")
            pop.setdefault(r["CVE_MET"], {}).setdefault(zone, {})[r["year"]] = int(r["POB_URB"])

    # 3. ring radii (km) per city  (columns: CVE_MET, r_3, r_5, r_9.3, ...)
    radii = {}
    with open(RADII, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames

        def pick(*cands):
            for c in cands:
                if c in cols:
                    return c
            return None
        c3, c5, c93 = pick("r_3", "r3"), pick("r_5", "r5"), pick("r_9.3", "r_93", "r9.3")
        for r in rd:
            radii[r["CVE_MET"]] = {
                "r3": round(float(r[c3]), 1) if c3 and r[c3] else None,
                "r5": round(float(r[c5]), 1) if c5 and r[c5] else None,
                "r9_3": round(float(r[c93]), 1) if c93 and r[c93] else None,
            }

    # 4. assemble + validate
    out = []
    for cve, c in cities.items():
        if cve not in pop:
            sys.exit(f"cve {cve} ({c['name']}) missing from pop_remoteness")
        zones = {}
        for zone in ZONE_ORDER:
            zpop = pop[cve].get(zone)
            if zpop is None or any(y not in zpop for y in YEARS):
                sys.exit(f"cve {cve} zone {zone} missing years: {zpop}")
            zones[zone] = {f"p{y}": zpop[y] for y in YEARS}
        for path in (c["thumb"], c["detail"]):
            if not os.path.exists(os.path.join(PROJECT, path)):
                sys.exit(f"missing image: {path} ({c['name']})")
        out.append({**c, "km": radii.get(cve, {}), "zones": zones})

    out.sort(key=lambda d: d["name"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(out)} cities -> {OUT}")


if __name__ == "__main__":
    main()
