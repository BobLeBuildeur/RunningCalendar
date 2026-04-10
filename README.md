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
2. In `astro.config.mjs`, replace the `site` value with your Pages origin, for example `https://<your-username>.github.io`, so asset and canonical URLs resolve correctly. The `base` path `/RunningCalendar/` matches a repository named `RunningCalendar` published as a project site at `https://<your-username>.github.io/RunningCalendar/`. If your repository name differs, update `base` to `/<repository-name>/`.
3. Push to `main`; the **Deploy Astro to GitHub Pages** workflow builds and publishes the `dist` folder.

## Stack

- [Astro](https://astro.build/) (minimal template)
- Plain HTML in pages for now (no separate CSS)
