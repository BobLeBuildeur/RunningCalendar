# AGENTS.md

## Cursor Cloud specific instructions

This is a minimal **Astro v6** static site (RunningCalendar). See `README.md` for standard dev commands (`npm run dev`, `npm run build`, `npm run preview`).

### Non-obvious notes

- **Node >= 22.12.0** is required (`engines` field in `package.json`).
- **`npm run dev`** and **`npm run build`** need a Postgres connection string (**`RUNNINGCALENDAR_DATABASE_URL`**, **`DATABASE_URL`**, or **`SUPABASE_DB_URL`**) so `loadCalendar()` can read from Supabase during SSR/prerender. Without it, the build fails.
- The dev server runs on `http://localhost:4321/RunningCalendar/` (note the `/RunningCalendar/` base path configured in `astro.config.mjs`). For **visual inspection**, agents should capture screenshots of affected pages after UI changes (see `.cursor/rules/ui-visual-inspection.mdc`); save PNGs under `artifacts/ui/` (gitignored).
- `astro check` requires `@astrojs/check` and `typescript` as dev dependencies. These are not listed in `package.json` by default; install them with `npm install @astrojs/check typescript` before running `npx astro check`.
- There are no lint or test scripts defined; `npx astro check` is the closest equivalent to a lint/type-check step.
- The build output goes to `dist/` (static files). This directory is git-ignored.
