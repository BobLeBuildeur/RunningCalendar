"""Optional live fetch: set RUN_LIVE=1 to verify scraper vs races.csv (network)."""

from __future__ import annotations

import csv
import os

import pytest
import requests

from running_calendar_scrapers.csv_io import repo_root
from running_calendar_scrapers.iguana import fetch_race_article, scrape_race


@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="Set RUN_LIVE=1 to run live network test")
def test_live_articles_match_csv():
	km = __import__(
		"running_calendar_scrapers.csv_io",
		fromlist=["load_distance_slugs_by_km"],
	).load_distance_slugs_by_km()
	path = repo_root() / "src" / "data" / "races.csv"
	with path.open(newline="", encoding="utf-8") as f:
		rows = [r for r in csv.DictReader(f) if r.get("providerSlug") == "iguana-sports"]
	session = requests.Session()
	session.headers.update({"User-Agent": "RunningCalendarBot/1.0"})
	for row in rows:
		url = row["detailUrl"]
		slug = url.rstrip("/").rsplit("/", 1)[-1]
		html = fetch_race_article(session, slug)
		parsed = scrape_race(slug, html, km_to_slug=km)
		assert parsed.sort_key == row["sortKey"], slug
		assert parsed.name == row["name"], slug
