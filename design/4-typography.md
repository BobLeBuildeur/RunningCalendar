# Typography

Typography uses **Manrope** as the primary typeface: a geometric sans with open forms, readable at small sizes and confident at display sizes. **CSS custom properties** in `apps/site/src/styles/tokens.css` implement the tokens below—use those names in components instead of raw `font-size`, `font-weight`, or color values.

---

## Font stack

| Token | Value | Notes |
| --- | --- | --- |
| `font.family.sans` | `"Manrope", system-ui, sans-serif` | Loaded via Google Fonts (variable `wght` 200–800). Fallbacks keep layout stable before the webfont loads. |

---

## Type scale and weights

Sizes align with `design/2-tokens.md` (`text.display` through `text.caption`). Weights map to Manrope’s axis: Regular 400, Medium 500, SemiBold 600, Bold 700.

| Token | CSS variable | Size | Weight | Default color token | Typical use |
| --- | --- | --- | --- | --- | --- |
| `text.display` | `--text-display` | clamp 32–40px | `--font-weight-bold` (700) | `color.text.primary` | Page title (site hero, main `<h1>` for a view) |
| `text.h1` | `--text-h1` | 28px | `--font-weight-bold` (700) | `color.text.primary` | Section titles (`<h1>` in cards, major `<h2>` on page) |
| `text.h2` | `--text-h2` | 22px | `--font-weight-semibold` (600) | `color.text.primary` | Subsections, card titles |
| `text.body` | `--text-body` | 16px | `--font-weight-regular` (400) | `color.text.primary` | Paragraphs, main UI copy |
| `text.body.secondary` | — (same size as `text.body`) | 16px | `--font-weight-regular` (400) | `color.text.secondary` | Supporting sentences, descriptions under headings |
| `text.meta` | `--text-meta` | 14px | `--font-weight-medium` (500) | `color.text.secondary` | Dates, times, secondary facts |
| `text.caption` | `--text-caption` | 12px | `--font-weight-regular` (400) | `color.text.secondary` | Labels, tags, fine print |
| `text.link` | — (inherits surrounding size) | — | `--font-weight-semibold` (600) | `color.primary` (hover: `color.primary.hover`) | Inline text links and text-style buttons |

**Line height:** Use `--line-height-tight` for headings and `--line-height-body` for paragraphs and UI blocks unless a component spec says otherwise.

---

## Heading hierarchy (semantic + visual)

| Role | HTML | Visual tokens | Color |
| --- | --- | --- | --- |
| Page title | One `<h1 class="...">` per page | `text.display` + bold | `color.text.primary` |
| Section heading | `<h2>` | `text.h1` + bold | `color.text.primary` |
| Subsection / card title | `<h3>` or `<h2 class="...">` in a card | `text.h2` + semibold | `color.text.primary` |
| Body | `<p>`, lists | `text.body` + regular | `color.text.primary` |
| Subtitle / intro | `<p class="...">` under the page title | `text.body` + regular | `color.text.secondary` |

Keep hierarchy consistent: one page-level `text.display` (or equivalent class) per view; nested headings use `text.h1` / `text.h2` so levels don’t skip visually.

---

## Common text patterns and components

| Pattern | Tokens | Notes |
| --- | --- | --- |
| **Page header block** | Title: `text.display`; optional subtitle: `text.body` + `color.text.secondary` | Vertical spacing: `space.sm` between title and subtitle, `space-xl` below the block |
| **Race card datetime** | `text.meta` + `color.text.secondary` | Already used in race cards |
| **Race card title** | `text.h2` + semibold + `color.text.primary` | |
| **Race card location** | `text.body` + `color.text.secondary` | |
| **Badge / tag** | `text.caption` + `color.text.secondary` (or inverse on tinted surfaces) | |
| **Primary action link** | `text.meta` + semibold + `color.primary` | Hover uses `color.primary.hover` |

---

## Cross-reference

- **Color tokens:** `design/2-tokens.md` — `color.text.primary`, `color.text.secondary`, `color.primary`, etc.
- **Spacing:** `design/2-tokens.md` — `space.*` for gaps and padding around type blocks.
