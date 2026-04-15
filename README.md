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

Race data is normalized in **`src/data/*.csv`** files and loaded at build time. The **[data model](docs/data-model.md)** also describes the **Supabase (PostgreSQL)** layout: the same entities, with races and distances linked by a **`race_distances`** junction table instead of a semicolon-separated column. The deployed static site does not query the database at runtime unless you add that separately.
