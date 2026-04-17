"""Guard-rail tests: the race-row shape has one source of truth.

If these tests fail, a downstream consumer (scraper CSV, AI schema, Supabase
INSERT, merge normalisation) has re-declared the row shape instead of
importing it from :mod:`running_calendar_scrapers.race_row`.
"""

from __future__ import annotations

from dataclasses import fields

from running_calendar_scrapers.ai_scraper.schema import RACE_ROW_KEYS as AI_KEYS
from running_calendar_scrapers.merge_csv import RACES_HEADER as MERGE_HEADER
from running_calendar_scrapers.race_row import (
	RACE_DB_INSERT_COLUMNS,
	RACE_ROW_FIELDS,
	RACE_ROW_KEYS,
	RACES_HEADER,
	ScrapedRace,
	format_races_csv,
	parse_races_csv,
	scraped_to_csv_rows,
)


def test_single_source_of_truth_for_csv_header():
	assert AI_KEYS is RACE_ROW_KEYS
	assert tuple(MERGE_HEADER) == tuple(RACES_HEADER)
	assert tuple(RACES_HEADER) == RACE_ROW_KEYS


def test_scraped_race_fields_match_descriptors():
	descriptor_attrs = tuple(f.attr for f in RACE_ROW_FIELDS)
	dataclass_attrs = tuple(f.name for f in fields(ScrapedRace))
	assert dataclass_attrs == descriptor_attrs


def test_insert_columns_exclude_distance_slugs():
	# distanceSlugs becomes rows in public.race_distances, not a races column.
	assert "distance_slugs" not in RACE_DB_INSERT_COLUMNS
	# Every other field maps to a races column.
	expected = tuple(
		f.db_column for f in RACE_ROW_FIELDS if f.db_column is not None
	)
	assert RACE_DB_INSERT_COLUMNS == expected


def test_csv_roundtrip_via_shared_helpers():
	race = ScrapedRace(
		sort_key="2026-05-31T07:00",
		city="São Paulo",
		state="SP",
		country="Brasil",
		name="Fun Run Tom e Jerry 2026",
		type_slug="road",
		distance_slugs="2-5km;5km;10km",
		provider_slug="yescom",
		detail_url="https://www.yescom.com.br/corridatomejerry/2026/index.asp",
	)
	csv_text = format_races_csv([race])
	parsed = parse_races_csv(csv_text)
	assert parsed == scraped_to_csv_rows([race])
	assert parsed[0]["distanceSlugs"] == "2-5km;5km;10km"


def test_iguana_re_exports_shared_contract():
	"""Legacy import paths keep working (backwards compatibility)."""
	from running_calendar_scrapers import iguana

	assert iguana.RACES_HEADER is RACES_HEADER
	assert iguana.ScrapedRace is ScrapedRace
	assert iguana.format_races_csv is format_races_csv
	assert iguana.parse_races_csv is parse_races_csv
	assert iguana.scraped_to_csv_rows is scraped_to_csv_rows
