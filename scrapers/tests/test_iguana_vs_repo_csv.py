"""Compare parser output to checked-in CSV for fixture-backed articles."""

from __future__ import annotations

import csv

from running_calendar_scrapers.csv_io import repo_root
from running_calendar_scrapers.iguana import scrape_race

FIXTURE_BY_SLUG = {
	"seven-run-2026": "iguana_seven_run_2026.html",
	"athenas-kids-run-stronger-2026": "iguana_kids_stronger_2026.html",
}


def _read_iguana_rows():
	path = repo_root() / "src" / "data" / "races.csv"
	with path.open(newline="", encoding="utf-8") as f:
		for row in csv.DictReader(f):
			if row.get("providerSlug") == "iguana-sports":
				yield row


def test_fixtures_match_races_csv():
	km = __import__(
		"running_calendar_scrapers.csv_io",
		fromlist=["load_distance_slugs_by_km"],
	).load_distance_slugs_by_km()
	by_slug = {r["calendarSlug"]: r for r in _read_iguana_rows()}
	for slug, fixture_name in FIXTURE_BY_SLUG.items():
		csv_row = by_slug[slug]
		html = (repo_root() / "scrapers" / "tests" / "fixtures" / fixture_name).read_text(encoding="utf-8")
		parsed = scrape_race(slug, html, km_to_slug=km)
		assert parsed.sort_key == csv_row["sortKey"]
		assert parsed.date_time_display == csv_row["dateTimeDisplay"]
		assert parsed.name == csv_row["name"]
		assert parsed.city == csv_row["city"]
		assert parsed.state == csv_row["state"]
		assert parsed.country == csv_row["country"]
		assert parsed.type_slug == csv_row["typeSlug"]
		assert parsed.distance_slugs == csv_row["distanceSlugs"]
		assert parsed.distances_note == csv_row["distancesNote"]
		assert parsed.detail_url == csv_row["detailUrl"]
