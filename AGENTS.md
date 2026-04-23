# AGENTS.md

## Cursor Cloud specific instructions

This is an **Nx monorepo** hosting a minimal **Astro v6** site (RunningCalendar) at `apps/site`. See `README.md` for standard dev commands (`npm run dev`, `npm run build`, `npm run preview`).

### Non-obvious notes

- **Node >= 22.12.0** is required (`engines` field in `package.json`).
- **`npm run dev`**, **`npm run build`**, and **`npm run validate-db`** need a Postgres connection string (**`RUNNINGCALENDAR_DATABASE_URL`**, **`DATABASE_URL`**, or **`SUPABASE_DB_URL`**) so `loadCalendar()` and validation can read from Supabase. Without it, the build (and `validate-db`) fails.
- The dev server runs on `http://localhost:4321/RunningCalendar/` (note the `/RunningCalendar/` base path configured in `apps/site/astro.config.mjs`). For **visual inspection**, agents should capture screenshots of affected pages after UI changes (see `.cursor/rules/ui-visual-inspection.mdc`); save PNGs under `artifacts/ui/` (gitignored).
- `astro check` requires `@astrojs/check` and `typescript` as dev dependencies. These are not listed in `package.json` by default; install them with `npm install @astrojs/check typescript` before running `npx astro check`.
- There are no lint or test scripts defined; `npx astro check` is the closest equivalent to a lint/type-check step.
- The site build output goes to `apps/site/dist/` (static files). This directory is git-ignored.
