# Slug conventions (primary and foreign keys)

Slug fields in **`public.providers`**, **`public.types`**, **`public.distances`**, and foreign-key columns on **`public.races`** use the same lexical rules and act as identifiers across entities.

## Format

- Lowercase ASCII **a–z** and digits **0–9** only, plus **hyphens** `-` between segments (kebab-case).
- No spaces, underscores, diacritics, or punctuation other than `-`.
- Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`.

Examples: `road`, `iguana-sports`, `running-land`, `xkr-sports`, `21-1km`, `yescom-2026-0001-19-meia-maratona-intl-de-s-o-paulo`.

## Primary keys

| Entity    | Table              | PK column |
|-----------|--------------------|-----------|
| Provider  | `public.providers` | `slug`    |
| Type      | `public.types`     | `slug`    |
| Distance  | `public.distances` | `slug`    |

## Foreign keys (`public.races`)

| Column           | References        |
|------------------|-------------------|
| `type_slug`      | `types.slug`      |
| `provider_slug`  | `providers.slug`  |
| `race_distances.distance_slug` | `distances.slug` |

`sort_key` is an ISO 8601 local date-time string used for ordering; it is not a slug.

## `distances.km` encoding

Values are stored as **integer tenths of a kilometre** (for example `50` → 5 km, `211` → 21.1 km) so half-marathon and marathon distances stay precise without fractional fields.

## Enforcement

- **`npm run validate-db`** checks slug format and referential integrity against the live database.
- Cursor rules under `.cursor/rules/` remind contributors not to duplicate information or bypass these conventions.
