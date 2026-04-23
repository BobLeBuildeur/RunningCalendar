# Grid and breakpoints

RunningCalendar uses a **12-column** responsive grid for layout. Align major blocks to the grid; use spacing tokens (`space.*` from the tokens doc) for gutters and internal padding unless a component spec says otherwise.

## Container

| Property | Value |
| --- | --- |
| Columns | 12 |
| Max width | 1200px |

Content is typically centered horizontally within the viewport; the grid container does not grow beyond **1200px** wide.

### Page inset (edge padding)

Horizontal space between the viewport edge and the content block keeps text readable on wide and narrow screens. Implementation uses **`--layout-page-inset`**: `space.md` (16px) by default, **`space.lg`** (24px) from the tablet breakpoint upward, **`space.xl`** (32px) from desktop upward. See `apps/site/src/styles/tokens.css`.

### CSS layout utilities

| Class | Role |
| --- | --- |
| `.layout` | Full-width wrapper (optional vertical sections). |
| `.layout__container` | Centers content, applies `max-width: 1200px`, responsive horizontal `--layout-page-inset`, and vertical `space.lg` padding. |

### 12-column grid

| Class | Role |
| --- | --- |
| `.grid` | CSS Grid with 12 equal columns and `--grid-gutter` between tracks. |
| `.grid__col` | Column cell (use on direct children of `.grid`; includes `min-width: 0` for overflow). |
| `.grid__col--span-1` … `.grid__col--span-12` | How many columns the cell spans (mobile-first; add media queries in page/component CSS for responsive spans if needed). |

**Pattern:** wrap the page in `.layout` → `.layout__container` → inner `.grid` → rows of `.grid__col.grid__col--span-*`.

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
