# Deploying the summary to GitHub Pages

The site is a self-contained Quarto project — `quarto render` needs only Quarto and the committed
files under `assets/`. Two ways to publish; **A (GitHub Actions)** is the default and is already
wired up in `.github/workflows/publish.yml`.

The repo is configured as a **website-only** repo: the paper's LaTeX sources, build PDFs, `FIGURES/`,
and the `ToTest/` prototype are gitignored (see `.gitignore`). Only `index.qmd`, `_quarto.yml`,
`_includes/`, `assets/`, `scripts/`, `.github/`, and the docs are tracked (~20 MB, mostly
`assets/images/`). To include the paper too, remove those lines from `.gitignore`.

## One-time setup

```bash
cd /Users/gperaza/Drive/Research/scaling_depopulation_summary

# 1. Initialise the repo and make the first commit
git init -b main
git add -A
git commit -m "Lay summary website: interactive Quarto document"

# 2. Create the GitHub repo and push (gh is authenticated as `gperaza`)
gh repo create scaling-depopulation-summary --public --source=. --remote=origin --push
#   (pick any name; use --private for a private repo)
```

### A) GitHub Actions (recommended — auto-deploys on every push)

The workflow renders and pushes `_site/` to a `gh-pages` branch on each push to `main`.

```bash
# The push above already triggered the first run. Watch it:
gh run watch

# Point Pages at the gh-pages branch (once the branch exists):
gh api -X POST repos/gperaza/scaling-depopulation-summary/pages \
  -f "source[branch]=gh-pages" -f "source[path]=/"
# (or: repo Settings -> Pages -> Source: "Deploy from a branch" -> gh-pages / root)
```

Live at `https://gperaza.github.io/scaling-depopulation-summary/`. Every later `git push` re-deploys.

If the Action can't push, enable write for the token: repo **Settings -> Actions -> General ->
Workflow permissions -> "Read and write permissions"** (the workflow's `permissions: contents: write`
usually suffices).

### B) Manual one-liner (no CI)

From your machine (has Quarto), instead of the Action:

```bash
quarto publish gh-pages
```

This renders, creates/updates the `gh-pages` branch, pushes it, and configures Pages. Re-run it
whenever you want to publish updates.

## Updating the site later

- **With Actions (A):** edit, `git commit`, `git push` → auto-redeploys.
- **Manual (B):** edit, then `quarto publish gh-pages`.

If chart data changed, regenerate it first (needs the analysis repo — see `CLAUDE.md`), commit the
updated `assets/data/*`, then deploy.
