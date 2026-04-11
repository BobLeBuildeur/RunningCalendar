# Slug conventions (primary and foreign keys)

All slug fields in `src/data/*.csv` use the same lexical rules and act as identifiers across entities.

## Format

- Lowercase ASCII **a–z** and digits **0–9** only, plus **hyphens** `-` between segments (kebab-case).
- No spaces, underscores, diacritics, or punctuation other than `-`.
- Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`.

Examples: `road`, `iguana-sports`, `21-1km`, `yescom-2026-0001-19-meia-maratona-intl-de-s-o-paulo`.

## Primary keys

| Entity    | CSV           | PK column |
|-----------|---------------|-----------|
| Provider  | `providers.csv` | `slug`  |
| Type      | `types.csv`     | `slug`  |
| Distance  | `distances.csv` | `slug`  |

## Foreign keys (from `races.csv`)

| Column           | References        |
|------------------|-------------------|
| `typeSlug`       | `types.slug`      |
| `providerSlug`   | `providers.slug`  |
| `distanceSlugs`  | `distances.slug` (semicolon-separated list; optional column may be empty) |

`sortKey` is an ISO 8601 local date-time string used for ordering; it is not a slug.

## `distances.km` encoding

The validation script requires `km` to be an **integer**. Values are stored as **tenths of a kilometre** (for example `50` → 5 km, `211` → 21.1 km) so half-marathon and marathon distances stay precise without fractional CSV fields.

## Enforcement

- **`npm run validate-csv`** checks slug format and referential integrity.
- Cursor rules under `.cursor/rules/` remind contributors not to duplicate information or bypass these conventions.
