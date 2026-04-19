"""Single source of truth for the flat race-row shape used across the scrapers.

The wire shape is documented in ``docs/data-model.md``. Historically it was
declared four times — in ``iguana.py`` (``ScrapedRace`` + ``RACES_HEADER``),
in ``supabase_sync.py`` (the ``INSERT`` column list), in ``merge_csv.py``
(per-column normalisation), and in ``ai_scraper/schema.py`` (``RACE_ROW_KEYS``
+ JSON schema). Adding one field therefore required edits in five files
that did not import each other.

This module defines the shape once, as a tuple of :class:`RaceRowField`
descriptors, and derives everything else from it:

- :data:`RACES_HEADER` — CSV column order used by every scraper.
- :data:`RACE_DB_INSERT_COLUMNS` — the column list for ``INSERT INTO public.races``.
- :class:`ScrapedRace` — the dataclass returned by the provider scrapers.
- :func:`scraped_to_csv_rows`, :func:`format_races_csv`, :func:`parse_races_csv` —
  CSV serialiser / reader.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §5.4.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, fields


@dataclass(frozen=True)
class RaceRowField:
	"""One field in the flat race-row contract.

	Attributes:
	    csv_key: Column name in scraper stdout / merged CSV (camelCase).
	    db_column: Corresponding ``public.races`` column (snake_case), or ``None``
	        when the field is not stored as a direct column (``distanceSlugs``
	        becomes rows in ``public.race_distances``).
	    attr: Attribute name on :class:`ScrapedRace` (snake_case).
	"""

	csv_key: str
	db_column: str | None
	attr: str


RACE_ROW_FIELDS: tuple[RaceRowField, ...] = (
	RaceRowField("sortKey", "sort_key", "sort_key"),
	RaceRowField("city", "city", "city"),
	RaceRowField("state", "state", "state"),
	RaceRowField("country", "country", "country"),
	RaceRowField("name", "name", "name"),
	RaceRowField("typeSlug", "type_slug", "type_slug"),
	# distanceSlugs has no single DB column: it becomes rows in race_distances.
	RaceRowField("distanceSlugs", None, "distance_slugs"),
	RaceRowField("providerSlug", "provider_slug", "provider_slug"),
	RaceRowField("detailUrl", "detail_url", "detail_url"),
)

RACES_HEADER: list[str] = [f.csv_key for f in RACE_ROW_FIELDS]
"""CSV header in the documented column order."""

RACE_ROW_KEYS: tuple[str, ...] = tuple(RACES_HEADER)
"""Alias for :data:`RACES_HEADER` used by the AI scraper schema."""

RACE_DB_INSERT_COLUMNS: tuple[str, ...] = tuple(
	f.db_column for f in RACE_ROW_FIELDS if f.db_column is not None
)
"""Column list for ``INSERT INTO public.races`` (excludes ``distanceSlugs``)."""

_CSV_TO_ATTR: dict[str, str] = {f.csv_key: f.attr for f in RACE_ROW_FIELDS}


@dataclass(frozen=True)
class ScrapedRace:
	"""One scraped race row. Field order matches :data:`RACE_ROW_FIELDS`."""

	sort_key: str
	city: str
	state: str
	country: str
	name: str
	type_slug: str
	distance_slugs: str
	provider_slug: str
	detail_url: str


# Guardrail: keep ScrapedRace in lockstep with RACE_ROW_FIELDS. If someone
# renames a dataclass field without updating the descriptor, imports fail
# at module load with a clear message rather than producing a mis-keyed row.
_SCRAPED_RACE_ATTRS = tuple(f.name for f in fields(ScrapedRace))
_EXPECTED_ATTRS = tuple(f.attr for f in RACE_ROW_FIELDS)
if _SCRAPED_RACE_ATTRS != _EXPECTED_ATTRS:  # pragma: no cover - structural invariant
	raise RuntimeError(
		"ScrapedRace fields drifted from RACE_ROW_FIELDS: "
		f"dataclass={_SCRAPED_RACE_ATTRS} descriptors={_EXPECTED_ATTRS}",
	)


def scraped_to_csv_rows(races: list[ScrapedRace]) -> list[dict[str, str]]:
	"""Convert :class:`ScrapedRace` instances to CSV-shaped dicts."""
	out: list[dict[str, str]] = []
	for race in races:
		row: dict[str, str] = {}
		for field in RACE_ROW_FIELDS:
			row[field.csv_key] = getattr(race, field.attr)
		out.append(row)
	return out


def format_races_csv(races: list[ScrapedRace]) -> str:
	"""Render ``races`` as a CSV string in the documented header order."""
	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=RACES_HEADER, lineterminator="\n")
	writer.writeheader()
	for row in scraped_to_csv_rows(races):
		writer.writerow(row)
	return buf.getvalue()


def parse_races_csv(text: str) -> list[dict[str, str]]:
	"""Parse CSV text into row dicts (inverse of :func:`format_races_csv`)."""
	reader = csv.DictReader(io.StringIO(text))
	return [dict(row) for row in reader]


__all__ = [
	"RACE_DB_INSERT_COLUMNS",
	"RACE_ROW_FIELDS",
	"RACE_ROW_KEYS",
	"RACES_HEADER",
	"RaceRowField",
	"ScrapedRace",
	"format_races_csv",
	"parse_races_csv",
	"scraped_to_csv_rows",
]
