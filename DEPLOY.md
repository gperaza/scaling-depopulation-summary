# Deploying the summary to GitHub Pages

The site is a self-contained Quarto project — `quarto render` needs only Quarto and the committed
files under `assets/`. It deploys via **GitHub Actions** (`.github/workflows/publish.yml`), using the
GitHub Pages *artifact* flow: on every push to `main` the workflow runs `quarto render` and publishes
`_site/` to Pages. (The artifact flow is used instead of `quarto publish gh-pages` because this is a
`type: default` project, not a `website` project.)

The repo is **website-only**: the paper's LaTeX sources, build PDFs, `FIGURES/`, and the `ToTest/`
prototype are gitignored (see `.gitignore`). Only `index.qmd`, `_quarto.yml`, `assets/`, `scripts/`,
`.github/`, and the docs are tracked (~18 MB, mostly `assets/images/`). To include the paper too,
delete those lines from `.gitignore`.

## One-time setup (already done for this repo)

```bash
git init -b main && git add -A && git commit -m "Lay summary website"
gh repo create scaling-depopulation-summary --public --source=. --remote=origin --push

# Set the Pages source to "GitHub Actions" (enables the artifact deploy):
gh api -X POST repos/gperaza/scaling-depopulation-summary/pages -f build_type=workflow
#   (or: repo Settings -> Pages -> Source: "GitHub Actions")
```

Watch the deploy and get the URL:

```bash
gh run watch
gh api repos/gperaza/scaling-depopulation-summary/pages --jq .html_url
```

Live at **https://gperaza.github.io/scaling-depopulation-summary/**.

## Updating the site later

Edit, then:

```bash
git commit -am "…" && git push      # the Action re-renders and re-deploys automatically
```

If chart data changed, regenerate it first (needs the analysis repo — see `CLAUDE.md`), commit the
updated `assets/data/*`, then push.

## Optional: manual local publishing

`quarto publish gh-pages` (a one-command local deploy) requires a `website`/`book`/`manuscript`
project. To use it, change `_quarto.yml` `project: type: default` -> `type: website` (a default
navbar will appear). The GitHub Actions flow above needs no such change, so it's the recommended path.
