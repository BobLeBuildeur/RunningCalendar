"""Compare parser output to expected rows from the database (or skip if no DB URL)."""

from __future__ import annotations

import pytest

from running_calendar_scrapers.db_config import database_url_from_env
from running_calendar_scrapers.db_ref import load_races_for_provider, repo_root
from running_calendar_scrapers.iguana import scrape_race

FIXTURE_BY_SLUG = {
	"seven-run-2026": "iguana_seven_run_2026.html",
	"athenas-kids-run-stronger-2026": "iguana_kids_stronger_2026.html",
}


def _require_db_url():
	try:
		database_url_from_env()
	except RuntimeError as e:
		pytest.skip(str(e))


def _detail_url_by_segment():
	"""Map blog path segment (from detail URL) to public.races row dict."""
	_require_db_url()
	rows = load_races_for_provider("iguana-sports")
	by_segment: dict[str, dict[str, str]] = {}
	for row in rows:
		url = row.get("detailUrl") or ""
		seg = url.rstrip("/").rsplit("/", 1)[-1]
		by_segment[seg] = row
	return by_segment


def test_fixtures_match_database_rows():
	_require_db_url()
	km = __import__(
		"running_calendar_scrapers.db_ref",
		fromlist=["load_distance_slugs_by_km"],
	).load_distance_slugs_by_km()
	by_segment = _detail_url_by_segment()
	for slug, fixture_name in FIXTURE_BY_SLUG.items():
		db_row = by_segment[slug]
		html = (repo_root() / "scrapers" / "tests" / "fixtures" / fixture_name).read_text(encoding="utf-8")
		parsed = scrape_race(slug, html, km_to_slug=km)
		assert parsed.sort_key == db_row["sortKey"]
		assert parsed.name == db_row["name"]
		assert parsed.city == db_row["city"]
		assert parsed.state == db_row["state"]
		assert parsed.country == db_row["country"]
		assert parsed.type_slug == db_row["typeSlug"]
		assert parsed.distance_slugs == db_row["distanceSlugs"]
		assert parsed.detail_url == db_row["detailUrl"]
