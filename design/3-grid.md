# Grid and breakpoints

RunningCalendar uses a **12-column** responsive grid for layout. Align major blocks to the grid; use spacing tokens (`space.*` from the tokens doc) for gutters and internal padding unless a component spec says otherwise.

## Container

| Property | Value |
| --- | --- |
| Columns | 12 |
| Max width | 1200px |

Content is typically centered horizontally within the viewport; the grid container does not grow beyond **1200px** wide.

## Breakpoints

Breakpoints define where layout and typography **may** change (e.g. column spans, stacking order). Exact pixel values belong in implementation as named constants aligned with this table.

| Name | Range | Typical use |
| --- | --- | --- |
| **Mobile** | `< 640px` | Single column or few columns; stacked patterns |
| **Tablet** | `640px` – `1024px` | Intermediate columns; combined side-by-side regions |
| **Desktop** | `≥ 1024px` | Full 12-column layouts; wider tables and filters |

**Convention:** `640px` and `1024px` are the **minimum** widths for tablet and desktop, respectively (tablet includes 640px; desktop starts at 1024px).

## Usage notes

- Prefer **progressive enhancement**: mobile-first layout, then add columns and density at tablet and desktop.
- Keep **clarity over density** (see `1-principles.md`): do not cram 12 columns of content on small screens.
