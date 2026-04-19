# Analytics events

Suggested event names and funnel mapping for **RunningCalendar**, aligned with the [user journey](./user-journey.md). Use these as a contract when wiring a client-side analytics SDK or server-side logging.

## Naming conventions (summary)

- **Event names:** `<object>_<action>` — describe *what* happened, not the UI control (e.g. prefer `race_favorite_selected` with `is_saved` over `heart_clicked`).
- **Verbs (controlled vocabulary):** `viewed`, `clicked`, `started`, `completed`, `failed`, `submitted`, `selected`.
- **Properties:** `snake_case`, descriptive full words (e.g. `race_id`, `source_page`).

## Funnel mapping

Stages follow the primary journey in [user-journey.md](./user-journey.md).

| Stage | Event |
| --- | --- |
| Land on the calendar | `calendar_viewed` |
| Filter to find a race | `filter_label_clicked`, `location_selected`, `distance_range_selected`, `date_range_selected`, `saved_filter_selected`, `calendar_filtered` |
| Favorite a race | `race_favorite_selected` |
| Open race details | `race_detail_clicked` |

## Event catalog

| Event name | Status | Owner | Description | Key properties |
| --- | --- | --- | --- | --- |
| `calendar_viewed` | Active | Product Analytics | User opened or returned to the calendar home page and the race list was available (static page; first meaningful paint or equivalent). | `source_page` (optional; e.g. referrer path), `base_path` (optional) |
| `filter_label_clicked` | Active | Product Analytics | User clicked the visible label/heading for a filter row (icon + title above the control). | `filter` (`location` \| `distance` \| `date` \| `saved`), `source_page` |
| `calendar_filtered` | Active | Product Analytics | Emitted immediately after any of the four filter-selection events below, with the same user action. Use for aggregate “user filtered” funnels; pair with the specific event for dimensions. | `filter_trigger` (`location_selected` \| `distance_range_selected` \| `date_range_selected` \| `saved_filter_selected`), `source_page` |
| `location_selected` | Active | Product Analytics | User chose a location option in the region filter (including “all” or equivalent). | `location_value`, `source_page` |
| `distance_range_selected` | Active | Product Analytics | User changed the distance range filter (min/max km). Omit or no-op when the UI hides distance bounds. | `distance_min_km`, `distance_max_km`, `source_page` |
| `date_range_selected` | Active | Product Analytics | User finished adjusting the date range filter (emitted after a short idle period so rapid clicks do not duplicate the event). | `start`, `end`, `date_range_start`, `date_range_end`, `source_page` |
| `saved_filter_selected` | Active | Product Analytics | User turned “saved races only” on or off. | `saved_only` (boolean), `source_page` |
| `race_favorite_selected` | Active | Product Analytics | User changed whether a race is saved for later (browser persistence). Fire once per toggle with the new state. | `race_id`, `race_name`, `is_saved` (boolean), `source_page` |
| `race_detail_clicked` | Active | Product Analytics | User followed the primary detail action from a race card (opens the organizer URL; external). | `race_id`, `destination_url`, `source_page` |

### Property notes

- **`race_id`** — Stable identifier for the race in analytics; in the app this matches the saved-race key (canonical `detail_url` / detail URL string).
- **`source_page`** — Path or logical name of the page where the event occurred (e.g. `/RunningCalendar/` for the home calendar).
- **`destination_url`** — Full URL opened for external race details (from `detail_url` in the data model).
- **`start` / `end`** — Inclusive calendar-day bounds for the selected range (ISO `YYYY-MM-DD`, local). Duplicated as `date_range_start` / `date_range_end` for dashboards that already use those names.
- **`filter_trigger`** — On `calendar_filtered`, the specific filter event fired in the same action (`location_selected`, `distance_range_selected`, `date_range_selected`, or `saved_filter_selected`).
