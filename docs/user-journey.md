# User journey

This page describes the main path someone takes on the **calendar home page**: narrow the list, mark races to revisit, and open the organizer’s page for full details. The UI copy on the site is largely **Portuguese**; this doc uses English for maintainability.

## Primary journey

```mermaid
journey
    title RunningCalendar — find, save, and open a race
    section Land on the calendar
      Open the home page (static list from build-time data): 5: Visitor
      Scan upcoming races in chronological order: 4: Visitor
    section Filter to find a race
      Choose location (region / “all”): 5: Visitor
      Adjust distance range (when bounds exist): 4: Visitor
      Pick a date range: 4: Visitor
      Optionally show only saved races: 3: Visitor
      Refine until the shortlist feels right: 5: Visitor
    section Favorite a race
      Spot a race worth tracking: 4: Visitor
      Toggle save on the card (stored in the browser): 5: Visitor
      See saved state reflected on the card: 5: Visitor
    section Open race details
      Follow “Ver detalhes” on a card: 5: Visitor
      View full information on the provider’s site (external URL from `detail_url`): 5: Visitor
```

## What each step maps to

- **Filters** — Location select, distance slider, date range, and “Somente corridas salvas” work together; all run client-side on the rendered list (`src/pages/index.astro` and related Svelte components).
- **Save / favorite** — The heart control on each card persists **saved race ids** (the race’s `detailUrl`) in **local storage**; see `src/lib/savedRaces.ts` and `SaveRaceButton`.
- **Details** — There is no in-app detail route; **Ver detalhes** links to the canonical **`detailUrl`** from the database (`raceUrl()` in `src/data/races.ts`).

For schema and build-time data flow, see [data-model.md](./data-model.md).
