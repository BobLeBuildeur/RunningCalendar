"""Optional live fetch: set RUN_LIVE=1 to verify scraper vs public.races (network + DB)."""

from __future__ import annotations

import os

import pytest
import requests

from running_calendar_scrapers.db_config import database_url_from_env
from running_calendar_scrapers.db_ref import load_races_for_provider
from running_calendar_scrapers.iguana import fetch_race_article, scrape_race


@pytest.mark.skipif(os.environ.get("RUN_LIVE") != "1", reason="Set RUN_LIVE=1 to run live network test")
def test_live_articles_match_database():
	try:
		database_url_from_env()
	except RuntimeError as e:
		pytest.skip(str(e))
	km = __import__(
		"running_calendar_scrapers.db_ref",
		fromlist=["load_distance_slugs_by_km"],
	).load_distance_slugs_by_km()
	rows = [r for r in load_races_for_provider("iguana-sports")]
	session = requests.Session()
	session.headers.update({"User-Agent": "RunningCalendarBot/1.0"})
	for row in rows:
		url = row["detailUrl"]
		slug = url.rstrip("/").rsplit("/", 1)[-1]
		html = fetch_race_article(session, slug)
		parsed = scrape_race(slug, html, km_to_slug=km)
		assert parsed.sort_key == row["sortKey"], slug
		assert parsed.name == row["name"], slug
