# CLAUDE.md

Guidance for working in this repo. Keep it current when structure or workflows change.

## What this is

A **general-audience (lay) web summary** of the academic paper *"Scaling and Population Loss in
Mexican Urban Centres"* (Peraza-Mues, Resendiz, Figueroa-Soriano, Prieto-Curiel, Ponce-Lopez).
It is a single **Quarto** HTML document (`index.qmd`) rendered to a static site (`_site/`) and
deployed to **GitHub Pages**. The paper's LaTeX sources also live in this directory but are not part
of the website.

## Build & preview

```bash
quarto preview          # live-reload while editing (opens a browser)
quarto render           # build the static site into _site/
```

Requirements: **Quarto** (tested 1.9.38). The render is **self-contained** — it needs only the
committed files under `assets/` plus Quarto. It does NOT need Python, R, the analysis repo, or any
network at render time (OJS charts run client-side; figures are pre-rendered PNGs; chart data is
committed CSV/JSON).

## Structure

```
index.qmd              # the whole document (prose + 3 interactive OJS/D3 components)
_quarto.yml            # project config: type default, output-dir _site, resources:[assets, "!ToTest/**"]
assets/
  data/                # committed chart data — figure6_points.csv, city_maps.json, city_images.json, density_change.json, map_vmax.json, radial_density.json
  figures/             # paper figures converted PDF->PNG (figure1..8.png, summary_methods.png)
  images/metros/       # per-city population-change maps: thumb <code>.png (127px), detail <code>2.png (828px)
scripts/               # stdlib data generators (see "Regenerating data")
main.tex, sup_main.tex, Figure*.pdf, FIGURES/   # the PAPER sources (not part of the website; gitignored)
```

## The interactive components (all Observable JS + D3 in `index.qmd`)

1. **Pop-by-zone bar chart** (Finding 1) — `popData` + Observable Plot; toggle total vs share.
2. **Interactive map grid** (Finding 1) — `figure2grid`: responsive grid of all 69 city maps
   (`repeat(auto-fill, minmax(76px,1fr))`, **capped at 10 columns** via `max-width:860px`); click a
   thumbnail → enlarged map on the right; **hovering a remoteness zone** (central/intermediate/
   distant/peri-urban) tints it and shows population change. Zone is computed from the cursor's
   **fractional distance from centre** (ring radii `0.150 / 0.250 / 0.465` of image width — constant
   across all maps) — NOT via SVG shape hit-testing (Chromium mis-routes stacked transparent shapes).
   The right panel also holds a **density-change line plot** (Δ vs. remoteness): 69 faint grey city
   lines + a bold black national trend, the selected city highlighted (orange), and a **Local/Average
   toggle** switching between paper Fig 3a (local point density σ) and Fig 3b (average density σ̄
   within r). Data: `assets/data/density_change.json` (keyed `{point,avg}`, each `{r, national, cities}`). Under the map is a **per-city
   colour-scale bar** showing the map's shading extent ±`vmax` (max |Δpop| per grid cell — each
   map is drawn on its own continuous scale, `adjust_vmax=False`); data `assets/data/map_vmax.json`.
3. **Figure 6 phase space** (Finding 3) — `figure6`: growth × urban-expansion-factor Φ scatter with
   all six labeled regions + the **fitted log-linear trend line** (Φ = growth^β·e^(αΔt), β=0.60,
   α=0.0057, Δt=10 yr; paper eq. L_factors), city dropdown, hover tooltips, zoom/pan (`d3.zoom`
   rescale pattern; "Reset view"). The right panel shows the selected city's **animated radial probability density**
   (paper Fig 5): four census-year ρ(r) curves that start collapsed onto 1990 and expand to their
   true shapes as a 1990→2020 slider/Play sweeps (each freezes at its year; transform `x→x·s`,
   `ρ→ρ/s` with `s=G(min(τ,y))/G(y)`, G = cumulative expansion factor). Data
   `assets/data/radial_density.json`. (This replaced the earlier click-to-select linked *map*.)

## Regenerating chart data (only when the underlying analysis changes)

Data files in `assets/data/` are committed, so normal edits/renders need nothing extra. To rebuild
them you need the paper's **analysis repo** cloned locally at
`/Users/gperaza/Drive/Research/scaling_depopulation` (git remote `CentroFuturoCiudades/scaling_depopulation_mex`,
with its `outputs/` precomputed). Then:

```bash
python3 scripts/build_figure6_data.py    # -> assets/data/figure6_points.csv (growth, Φ per city/period)
python3 scripts/build_city_maps_data.py  # -> assets/data/city_maps.json (per-zone pop per city)

# these two MUST use the analysis repo's interpreter (numpy/pandas/geopandas + the `depopulation`
# package to reuse load_radial_f / plot_delta_density / pop_change_map's vmax logic):
/Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python \
    scripts/build_density_change_data.py   # -> assets/data/density_change.json (Δσ vs remoteness)
/Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python \
    scripts/build_map_vmax.py              # -> assets/data/map_vmax.json (per-city map colour scale)
/Users/gperaza/Drive/Research/scaling_depopulation/.venv/bin/python \
    scripts/build_radial_density.py        # -> assets/data/radial_density.json (Fig 5 ρ(r) + expansion factors G)
```

The first two are pure stdlib. They read `outputs/scaling_factors.csv`, `outputs/pop_remoteness_brackets_long.csv`,
`data/cve_code_names.json` from the analysis repo, and join to images via `assets/data/city_images.json`.
`build_density_change_data.py`, `build_map_vmax.py`, and `build_radial_density.py` instead read
`outputs/radial_f/*.csv` (plus `outputs/mesh.geoparquet` for map_vmax and `outputs/scaling_factors.csv`
for radial_density) via the repo's own functions (`load_radial_f`, `gen_pop_ar`), so they run with
that repo's `.venv` (not system python3).
The paper's raw data is also on Zenodo (DOI `10.5281/zenodo.20630381`).

## Gotchas

- **Join by CVE for data, by image path for images.** A few cities' analysis CVE code ≠ image
  filename code (e.g. Chilpancingo cve `12.1.01` but image `12.2.012.png`). Generators handle this;
  don't derive image paths from `cve_code`.
- **Figures are PDFs → convert to PNG** with `pdftocairo -png -scale-to 2000` (poppler). The web uses
  the PNGs in `assets/figures/`, never the source PDFs.
- **OJS `FileAttachment` paths** are relative to `index.qmd`; `resources: [assets]` in `_quarto.yml`
  is what copies JS-referenced files into `_site/` (Quarto's scanner can't see paths built in JS).
- **`ToTest/`** is a superseded standalone prototype (has its own `.git`); excluded from the build
  (`!ToTest/**`) and gitignored.
- **Verify OJS interactivity in a real browser**, not by grepping the rendered DOM. Serve `_site/`
  over HTTP (`file://` blocks OJS ES-modules) and drive it with headless Chromium
  (`/opt/homebrew/bin/chromium`) — CDP over the DevTools WebSocket works for programmatic hover/click.
- **zsh `noclobber`**: redirects like `> file` fail if the file exists; use `>|` (the Bash tool).

## Deploying to GitHub Pages

Automated via **`.github/workflows/publish.yml`** (GitHub Actions runs `quarto render` on every push
to `main` and deploys `_site/` via the GitHub Pages *artifact* flow — used because this is a
`type: default`, not a `website`, project). Setup details in `DEPLOY.md`.
Live: **https://gperaza.github.io/scaling-depopulation-summary/**.

## More context

Per-session memory (who the user is, project decisions/history) lives under
`~/.claude/projects/-Users-gperaza-Drive-Research-scaling-depopulation-summary/memory/`.
