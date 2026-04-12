# UI components

## Dual Range Slider (`src/components/DualRangeSlider.svelte`)

Agnostic two-thumb range control for selecting a **start** and **end** value on a single numeric axis.

**Props**

| Prop | Description |
| --- | --- |
| `min`, `max` | Bounds of the axis (inclusive). |
| `start`, `end` | Bindable selected range (`$bindable()`). |
| `step` | Step for native range inputs (default `0.1`). |
| `formatValue` | Formats a single number for display (default: `String`). |
| `formatMinLabel`, `formatMaxLabel` | Optional overrides for the left and right track labels. |
| `formatRange` | Optional override for the center summary string. |
| `id` | Prefix for element ids (defaults to a random id). |
| `labelledBy` | Optional id of an external label element; combined with the value text for `aria-labelledby`. |

**Rules**

- `start` is clamped to `[min, end]`; `end` is clamped to `[start, max]`.
- Thumbs use stacked native `<input type="range">` elements; the end thumb sits above the start thumb when they overlap so both remain draggable.

Parent pages can listen for value changes via their own wrappers (for example custom events).

## Race distance filter (`src/components/RaceDistanceFilter.svelte`)

Home-page wrapper around `DualRangeSlider` for race discovery. It receives `minKm` and `maxKm` computed at build time from all races’ listed distances (see `distanceBoundsFromRaces` in `src/data/races.ts`), formats labels as kilometres, and dispatches a bubbling `runningcalendar:distance` `CustomEvent` with `{ minKm, maxKm, start, end }` whenever the range changes (including the initial mount).

**Filtering semantics** (handled in `src/pages/index.astro`): a race is shown if **at least one** of its listed distances (from `distances.csv` via slugs) falls **inclusively** within `[start, end]`. When `start` and `end` equal the global min and max, the distance filter is treated as inactive (all races pass the distance check). Races with no listed distances are hidden whenever the distance filter is narrowed.
