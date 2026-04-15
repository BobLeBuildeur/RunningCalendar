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

**Filtering semantics** (handled in `src/pages/index.astro`): a race is shown if **at least one** of its listed distances (from `public.distances` via slugs loaded at build time) falls **inclusively** within `[start, end]`. When `start` and `end` equal the global min and max, the distance filter is treated as inactive (all races pass the distance check). Races with no listed distances are hidden whenever the distance filter is narrowed.

## Date range picker (`src/components/DateRangePicker.svelte`)

Agnostic calendar UI for choosing an **inclusive** start and end **calendar day** (local date keys `YYYY-MM-DD`). It does not know about races or CSV data.

**Output states** (exposed on the root as `data-state` and in dispatched events):

| State | Meaning |
| --- | --- |
| `inactive` | No dates, or both cleared |
| `invalid` | Exactly one of start/end (partial selection) |
| `valid` | Both start and end set |

**Behavior** (selection rules live in `src/lib/dateRangePickerLogic.ts`):

- First click sets the start date → `invalid`.
- Second click completes the range (before or after the start) → `valid`, or clears if it is the same day as the lone start → `inactive`.
- With a full range, clicking before the start moves the start; clicking after the end moves the end; clicking the start or end removes that endpoint (see spec for edge cases).

**Events**

- Dispatches `runningcalendar:daterange` on `document` with `detail`: `{ state: 'inactive' \| 'invalid' \| 'valid', start: string \| null, end: string \| null }` where `start`/`end` are ISO date keys only when `state === 'valid'`.

**Presentation**

- Collapsed summary; **click the trigger** to open or close the dual-month grid. The trigger uses **mousedown to open** when closed so the same gesture’s `click` does not immediately toggle shut again.
- **Blur outside** closes the popover: `focusout` defers with `setTimeout(0)` and checks `document.activeElement` because `relatedTarget` is often `null` when focus moves into the calendar.
- Styling uses design tokens (`--color-primary`, `--color-danger`, `--color-secondary`, etc.).

**Demo video**

- Run `npm run test:e2e:demo`; Cypress records `artifacts/ui/cypress-videos/date-range-picker-demo.cy.ts.mp4` (gitignored).

## Race date filter (`src/components/RaceDateFilter.svelte`)

Home-page wrapper: label + `DateRangePicker` with `fieldId` defaulting to `race-date-filter`.

**Filtering semantics** (handled in `src/pages/index.astro`): each race card exposes `data-race-date` (YYYY-MM-DD from `sortKey`). When the date range is `valid`, a race is shown only if `data-race-date` is **inclusively** between `start` and `end`. When the range is `inactive` or `invalid`, no date filter is applied (same pattern as location + distance).
