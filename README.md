# RunningCalendar

Astro site bootstrapped for deployment to **GitHub Pages** (project site).

## Local development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

Preview the static output:

```bash
npm run preview
```

## GitHub Pages setup

1. In the repository **Settings → Pages**, set **Source** to **GitHub Actions**.
2. In `astro.config.mjs`, `site` is set to this org/user’s GitHub Pages host and `base` is `/RunningCalendar/` for a project site at `https://boblebuildeur.github.io/RunningCalendar/`. If you fork or rename the repo, update `site` and `base` to match [Astro’s GitHub deploy guide](https://docs.astro.build/en/guides/deploy/github/).
3. Push to `main`; the **Deploy Astro to GitHub Pages** workflow builds and publishes the `dist` folder.

## Stack

- [Astro](https://astro.build/) (minimal template)
- Plain HTML in pages for now (no separate CSS)

## Data

The home page is built from **Supabase (PostgreSQL)** at **`npm run build`** time (`loadCalendar()` in `src/data/races.ts`). Set **`RUNNINGCALENDAR_DATABASE_URL`**, **`DATABASE_URL`**, or **`SUPABASE_DB_URL`** to your **session mode** Postgres URI (Project Settings → Database). For **GitHub Pages**, store that URI in a repo secret and inject it in the deploy workflow.

**`src/data/*.csv`** files are kept for **`npm run validate-csv`** and for Python scraper FK validation; they are not used to render the site. See **[data model](docs/data-model.md)** for the schema and CSV ↔ table mapping.

Python scrapers under **`scrapers/`** can insert new races with **`--save-to`** (see `docs/data-model.md`).

**Parity check:** with `DATABASE_URL` (or `RUNNINGCALENDAR_DATABASE_URL`) set, run **`npm run compare-db-to-csv`** to assert `public.*` matches `src/data/*.csv` (same race keys as `detailUrl`, distance slugs ordered by `km`).
