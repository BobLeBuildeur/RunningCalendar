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

Home-page wrapper around `DualRangeSlider` for race discovery. The slider axis is fixed (**0 km → 41.195 km**, see `src/lib/distanceFilter.ts`) so the control stays predictable; it does not stretch to the longest ultra in the dataset. The native range step is **0.001 km** so the maximum thumb position can represent **41.195 km** exactly. It dispatches a bubbling `runningcalendar:distance` `CustomEvent` with `{ minKm, maxKm, start, end }` whenever the range changes (including the initial mount).

**Filtering semantics** (handled in `src/pages/index.astro`): a race is shown if **at least one** of its listed distances (from `public.distances` via slugs loaded at build time) falls within the selected range. When the **end** thumb is at the slider maximum (41.195 km), any distance **greater than or equal to** that value matches (full marathon and longer ultras). Otherwise the end bound is **inclusive** (`k <= end`). When `start` and `end` equal the slider min and max, the distance filter is treated as inactive (all races pass the distance check). Races with no listed distances are hidden whenever the distance filter is narrowed.

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

- Dispatches `runningcalendar:daterange` on `document` with `detail`: `{ state: 'inactive' \| 'invalid' \| 'valid', start: string \| null, end: string \| null }` where `start`/`end` are ISO date keys only when `state === 'valid'`. The home page listens to this event for filtering; it fires on every state change.
- **Analytics:** when PostHog is enabled, `date_range_selected` is captured after the range settles (debounced), not on every intermediate click, and includes `start`, `end`, `date_range_start`, and `date_range_end`.

**Presentation**

- Collapsed summary; **click the trigger** to open or close the dual-month grid. The trigger uses **mousedown to open** when closed so the same gesture’s `click` does not immediately toggle shut again.
- **Blur outside** closes the popover: `focusout` defers with `setTimeout(0)` and checks `document.activeElement` because `relatedTarget` is often `null` when focus moves into the calendar.
- Styling uses design tokens (`--color-primary`, `--color-danger`, `--color-secondary`, etc.).

**Demo video**

- Run `npm run test:e2e:demo`; Cypress records `artifacts/ui/cypress-videos/date-range-picker-demo.cy.ts.mp4` (gitignored).

**E2E builds:** `npm run preview:e2e` sets `RUNNINGCALENDAR_E2E_FIXTURE=1` so `npm run build` uses a small in-repo calendar instead of PostgreSQL (for Cypress in CI and local runs without a DB URL).

## Race date filter (`src/components/RaceDateFilter.svelte`)

Home-page wrapper: label + `DateRangePicker` with `fieldId` defaulting to `race-date-filter`.

**Filtering semantics** (handled in `src/pages/index.astro`): each race card exposes `data-race-date` (YYYY-MM-DD from `sortKey`). When the date range is `valid`, a race is shown only if `data-race-date` is **inclusively** between `start` and `end`. When the range is `inactive` or `invalid`, no date filter is applied (same pattern as location + distance).

## Save race button (`src/components/SaveRaceButton.svelte`)

Heart-shaped toggle rendered inside every race card header (`src/components/RaceItem.svelte`) that marks a race as saved. The component renders SSR-only markup (a `.save-race` button with `data-race-id` + `data-saved="false"` and `data-label-save` / `data-label-unsave` strings for accessibility). All interactivity — reading/writing `localStorage`, updating `data-saved` + filling the SVG heart, and updating `aria-label` / `aria-pressed` — is handled by a single delegated `click` handler in the inline script of `src/pages/index.astro`. This avoids hydrating one Svelte island per race card and keeps the page static.

**Storage contract** (`src/lib/savedRaces.ts`): `localStorage` key `runningcalendar:saved-races` holds a JSON array of race identifiers. The identifier used for each race is its `detailUrl` (stable per the data model, see `docs/data-model.md`). The constant is imported by the Astro page and embedded in a `<script type="application/json" id="running-calendar-config">` block so that the inline filter script reads the same key without duplicating the string.

**Visual state**: muted (`--color-text-secondary`) when not saved, brand primary (`--color-primary`) filled when saved. Styles live in `src/styles/global.css` so state selectors such as `.save-race[data-saved='true']` keep matching after the delegated handler flips the attribute.

## Race saved filter (`src/components/RaceSavedFilter.svelte`)

Home-page wrapper: heart-icon label + a native checkbox ("Somente corridas salvas"). On change it dispatches a bubbling `runningcalendar:savedfilter` `CustomEvent` on `document` with `detail.active: boolean`.

**Filtering semantics** (handled in `src/pages/index.astro`): when active, races are shown only if their `data-race-id` appears in the saved set read from `localStorage` **at the moment the user toggled the checkbox**. Toggling individual heart buttons after that does **not** re-apply the filter — the visible list only changes when the user interacts with the saved-filter checkbox again. This is intentional: it prevents cards from disappearing under the user's cursor as they curate their list. The checkbox state itself is session-only (not persisted).
