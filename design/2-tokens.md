# Design tokens

These tokens are the single source of truth for color, type, spacing, radii, and elevation. **Use these names in implementation** (e.g. CSS custom properties mapped to these values)—do not use arbitrary one-off colors or spacing in UI code.

---

## Colors

| Token | Value | Intent | Usage |
| --- | --- | --- | --- |
| `color.primary` | `#0B6E4F` | Core brand action | Buttons, links, highlights |
| `color.primary.hover` | `#09543D` | Interaction feedback | Button hover |
| `color.secondary` | `#F4A261` | Accent energy | Tags, highlights (e.g. “Popular”) |
| `color.background` | `#FFFFFF` | Base surface | Page background |
| `color.surface` | `#F7F9FA` | Secondary surface | Cards, panels |
| `color.border` | `#E5E7EB` | Separation | Dividers, inputs |
| `color.text.primary` | `#111827` | Readability | Headings, body |
| `color.text.secondary` | `#6B7280` | Supporting info | Metadata |
| `color.success` | `#2A9D8F` | Positive signal | Confirmations |
| `color.warning` | `#E9C46A` | Alerts | Deadlines |
| `color.danger` | `#E76F51` | Critical | Sold out, closed |

---

## Typography

| Token | Size | Weight | Usage |
| --- | --- | --- | --- |
| `text.display` | 32–40px | Bold | Page headers |
| `text.h1` | 28px | Bold | Section titles |
| `text.h2` | 22px | SemiBold | Subsections |
| `text.body` | 16px | Regular | Main content |
| `text.meta` | 14px | Medium | Race details |
| `text.caption` | 12px | Regular | Labels, tags |

**`text.display`:** Use the range responsively (e.g. smaller on narrow viewports, larger on wide)—stay within 32–40px and keep hierarchy clear versus `text.h1`.

---

## Spacing and layout

| Token | Value | Usage |
| --- | --- | --- |
| `space.xs` | 4px | Tight spacing |
| `space.sm` | 8px | Between elements |
| `space.md` | 16px | Standard padding |
| `space.lg` | 24px | Sections |
| `space.xl` | 32px | Large separation |

**Page inset:** Horizontal padding from the viewport to the content block is implemented as **`layout.page.inset`** → CSS `--layout-page-inset` (responsive: `space.md` → `space.lg` → `space.xl` at tablet/desktop breakpoints). See `design/3-grid.md`.

**Grid gutter:** **`grid.gutter`** → `--grid-gutter` (defaults to `space.md`) for gaps between 12-column grid tracks.

---

## Radius

| Token | Value |
| --- | --- |
| `radius.sm` | 6px |
| `radius.md` | 12px |
| `radius.lg` | 20px |

---

## Elevation

Shadow tokens describe **intent**; implement them as `box-shadow` (or equivalent) in code using CSS variables so values stay centralized.

| Token | Value |
| --- | --- |
| `shadow.sm` | Subtle card |
| `shadow.md` | Hover state |
| `shadow.lg` | Modals |
