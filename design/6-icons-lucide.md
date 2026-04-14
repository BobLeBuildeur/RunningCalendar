# Icons (Lucide)

RunningCalendar uses **[Lucide](https://lucide.dev)** for UI icons: a single stroke-based family that matches our clean, readable interface (see `design/1-principles.md`, `design/4-typography.md`). Icons are implemented with:

- **`@lucide/astro`** — Astro pages and static markup (`import MapPin from '@lucide/astro/icons/map-pin'`).
- **`lucide`** — icon definitions as data (`import { Calendar } from 'lucide'`). Svelte islands render them through **`LucideIcon`** (`src/components/LucideIcon.svelte`), which mirrors Lucide’s default SVG attributes and works with Astro’s static prerender (unlike importing prebuilt `.svelte` icons from `node_modules`).

The **`lucide`** package is the shared source of icon geometry; keep imports named and tree-shake friendly.

---

## How icons inherit color

Lucide strokes use **`currentColor`** by default. In this project, **do not set `color` on the icon component** unless you need a fixed hex. Instead:

1. Put the icon inside a wrapper with a **semantic token** (e.g. `color: var(--color-primary)` for brand accents, `var(--color-danger)` for errors).
2. Let the SVG inherit via `currentColor`.

That keeps filters, date picker states, and labels aligned with `design/2-tokens.md` without duplicating palette values on each icon.

**Sizes:** Use the `size` prop (number = px). Common patterns here: **16** beside meta labels, **18** inside dense controls (e.g. date range trigger).

---

## Choosing an icon (for agents)

1. **Match the user intent**, not decoration: calendar for dates, map pin for place, sliders/arrows for ranges, check for success, alert circle for validation errors.
2. **Prefer outline / stroke icons** — Lucide’s default; avoid filled variants unless the design explicitly calls for emphasis.
3. **Stay consistent**: if one filter label uses a Lucide icon, sibling labels should too (same visual weight).
4. **Search** [lucide.dev/icons](https://lucide.dev/icons) by keyword (e.g. “distance”, “calendar”, “location”). If several fit, pick the **simplest** silhouette at 16px.
5. **Accessibility:** Decorative icons: omit a title and rely on Lucide’s `aria-hidden` behavior; for meaning conveyed only by icon, add `title` / `aria-label` per Lucide docs and pair with visible text where possible.

---

## Canonical icons in this app

| Context | Lucide name | Intent |
| --- | --- | --- |
| Location filter label | [`MapPin`](https://lucide.dev/icons/map-pin) | Geographic place / venue |
| Date filter label & date range trigger | [`Calendar`](https://lucide.dev/icons/calendar) | Choosing dates |
| Distance filter label | [`MoveHorizontal`](https://lucide.dev/icons/move-horizontal) | Adjustable min/max span (dual range) |
| Valid range / confirmation | [`Check`](https://lucide.dev/icons/check) | Success, complete selection |
| Invalid range | [`CircleAlert`](https://lucide.dev/icons/circle-alert) | Error or incomplete state |

When adding new UI, start from this table; add new rows here if you introduce a repeated pattern.

---

## Implementation notes

- **Imports:** In Astro, use `@lucide/astro/icons/...`. In Svelte, import icon nodes from `lucide` and render with `<LucideIcon icon={…} />` (see existing filters and `DateRangePicker`).
- **Stroke width:** Default is `2`. Match legacy weights only when replacing an existing icon (e.g. slightly heavier check) via the `strokeWidth` prop on `LucideIcon`.
- **Classes:** Pass `class` as needed; `@lucide/astro` adds `lucide` and `lucide-{name}` on Astro icons.
