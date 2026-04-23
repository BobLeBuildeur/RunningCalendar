# RunningCalendar

Nx monorepo with the Astro frontend in `apps/site` and shared agnostic UI utilities in `libs/liba`.

## Local development

```bash
npm install
npm run dev
```

Equivalent direct Nx command:

```bash
npx nx run site:dev
```

## Build

```bash
npm run build
```

Equivalent direct Nx command:

```bash
npx nx run site:build
```

Preview the static output:

```bash
npm run preview
```

## GitHub Pages setup

1. In the repository **Settings → Pages**, set **Source** to **GitHub Actions**.
2. In `apps/site/astro.config.mjs`, `site` is set to this org/user’s GitHub Pages host and `base` is `/RunningCalendar/` for a project site at `https://boblebuildeur.github.io/RunningCalendar/`. If you fork or rename the repo, update `site` and `base` to match [Astro’s GitHub deploy guide](https://docs.astro.build/en/guides/deploy/github/).
3. Push to `main`; the **Deploy Astro to GitHub Pages** workflow builds and publishes the `apps/site/dist` folder.

## Stack

- [Astro](https://astro.build/) (minimal template)
- Plain HTML in pages for now (no separate CSS)

## Data

The home page is built from **Supabase (PostgreSQL)** at **`npm run build`** time (`loadCalendar()` in `apps/site/src/data/races.ts`). Set **`RUNNINGCALENDAR_DATABASE_URL`**, **`DATABASE_URL`**, or **`SUPABASE_DB_URL`** to your **session mode** Postgres URI (Project Settings → Database). For **GitHub Pages**, store that URI in a repo secret and inject it in the deploy workflow.

There are **no checked-in CSV data files**; **[data model](docs/data-model.md)** describes the schema and how scraper output maps to tables.

Python scrapers under **`scrapers/`** validate foreign keys against the database and can insert new races with **`--save-to`** (see `docs/data-model.md`).

For JS-heavy or inconsistent race pages, the **AI-assisted scraper** under `scrapers/running_calendar_scrapers/ai_scraper/` renders the page in Cypress and extracts a single race row via the OpenAI API (`docs/ai-scraper.md`).

**Schema check:** with the same database env vars set, run **`npm run validate-db`** to verify slug formats, URLs, FK integrity, and unique `detail_url` values in `public.*`.
