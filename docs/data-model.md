# Data model

RunningCalendar uses the **same conceptual model** in two places:

1. **CSV files** under `src/data/` — loaded at **build time** by `src/data/races.ts` for the static site.
2. **PostgreSQL on Supabase** — normalized tables for **query/API** use, with races and distances related by a **many-to-many** junction table instead of a semicolon-separated field.

Schema validation for CSVs: run `npm run validate-csv` locally before committing. Slug rules are summarized in [slug-conventions.md](./slug-conventions.md).

## Static site: CSV files

The Astro app does not talk to the database at runtime. It reads CSVs only during the build.

### Entity relationship (CSV)

In the repo, each race stores **multiple distances** as a single optional column: `distanceSlugs` is a `;`-separated list of `distances.slug` values.

```mermaid
erDiagram
	PROVIDER ||--o{ RACE : organizes
	TYPE ||--o{ RACE : categorizes
	DISTANCE ||--o{ RACE : "listed as"

	PROVIDER {
		string slug PK
		string name
		string website
	}

	TYPE {
		string slug PK
		string type
	}

	DISTANCE {
		string slug PK
		int km "tenths of km"
		string description "optional"
	}

	RACE {
		string sortKey "ISO local date-time"
		string city
		string state
		string country
		string name
		string typeSlug FK
		string distanceSlugs "semicolon list optional"
		string providerSlug FK
		string detailUrl
	}
```

- **Provider**: Race organizer; linked from the UI by name (website URL).
- **Type**: Kind of event (e.g. road, trail); `races.typeSlug` references `types.slug` (default in data: `road` when omitted in scraper output; the CSV column should still be set for clarity).
- **Distance**: Canonical distance options; `races.distanceSlugs` is a `;`-separated list of `distances.slug`. The `km` column stores **integer tenths of a kilometre** (for example `50` → 5 km, `211` → 21.1 km) so values stay integers while preserving half-marathon precision. Optional `description` holds non-numeric context (for example kids categories) instead of putting prose in the race row.
- **Race**: One scheduled event. `sortKey` is the single source for ordering and display time (ISO `YYYY-MM-DDTHH:MM`). `detailUrl` is the public page for “View details”. Client-side distance filtering on the home page uses each race’s listed distances (see [components.md](./components.md)).

### Column reference (CSV)

| File | Columns |
|------|---------|
| `races.csv` | `sortKey`, `city`, `state`, `country`, `name`, `typeSlug`, `distanceSlugs` (optional), `providerSlug`, `detailUrl` |
| `providers.csv` | `slug`, `name`, `website` |
| `types.csv` | `slug`, `type` |
| `distances.csv` | `slug`, `km`, `description` (optional) |

## Supabase / PostgreSQL

The database mirrors providers, types, distances, and races, but **splits race–distance associations** into a junction table so the relationship is properly **many-to-many** (`races` ↔ `distances`).

### Entity relationship (database)

```mermaid
erDiagram
	providers ||--o{ races : "provider_slug"
	types ||--o{ races : "type_slug"
	races ||--o{ race_distances : has
	distances ||--o{ race_distances : "distance_slug"

	providers {
		text slug PK
		text name
		text website
	}

	types {
		text slug PK
		text type
	}

	distances {
		text slug PK
		int km "tenths of km"
		text description "nullable"
	}

	races {
		uuid id PK
		text sort_key
		text city
		text state
		text country
		text name
		text type_slug FK
		text provider_slug FK
		text detail_url UK
	}

	race_distances {
		uuid race_id FK
		text distance_slug FK
	}
```

- **`races`**: One row per event. `id` is a UUID primary key. **`detail_url` is unique** and matches the CSV `detailUrl`; it is the stable natural key used when seeding and when resolving junction rows.
- **`race_distances`**: One row per (race, distance) pair. Replaces `races.csv`’s `distanceSlugs` list. Races with no distances in the CSV have no rows here.
- **`distances.km`**: Same meaning as in CSV — integer **tenths of a kilometre** (documented in SQL comments on the column).

### Security

Row Level Security (RLS) is enabled on these tables. Policies allow **`anon` and `authenticated` read (`SELECT`) only** — typical for public calendar data consumed from the browser with the anon key.

### CSV ↔ database mapping

| CSV | Database |
|-----|----------|
| `providers.csv` | `public.providers` |
| `types.csv` | `public.types` |
| `distances.csv` | `public.distances` |
| `races.csv` (scalar columns) | `public.races` (`sort_key`, `detail_url`, …) |
| `races.csv` → `distanceSlugs` | `public.race_distances` (one insert per slug after splitting on `;`) |

### Populating the database from CSVs

The repository does **not** ship generated SQL or migration artifacts for bulk loading. To sync Supabase with `src/data/*.csv`, apply the schema (for example migration `running_calendar_schema` on the project) and load data yourself: insert reference rows (`providers`, `types`, `distances`), insert `races` with `detail_url` matching `detailUrl`, then insert `race_distances` rows by splitting each race’s `distanceSlugs` on `;` and joining to `distances.slug`. Split large scripts if your SQL client enforces a payload limit.

The static site continues to use **only the CSVs** unless you add a separate data layer that queries Supabase.
