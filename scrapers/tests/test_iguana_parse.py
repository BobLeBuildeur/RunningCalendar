"""Unit tests for Iguana HTML parsing (offline snippets)."""

from __future__ import annotations

from running_calendar_scrapers.db_ref import repo_root
from running_calendar_scrapers.iguana import scrape_race
from tests._fixtures import km_to_slug_iguana_html_tests


def test_seven_run_distances():
	km = km_to_slug_iguana_html_tests()
	html = (repo_root() / "scrapers" / "tests" / "fixtures" / "iguana_seven_run_2026.html").read_text(
		encoding="utf-8",
	)
	r = scrape_race("seven-run-2026", html, km_to_slug=km)
	assert r.sort_key == "2026-04-26T06:00"
	assert r.name == "Seven Run 2026"
	assert r.city == "São Paulo"
	assert r.state == "SP"
	assert r.country == "Brasil"
	assert r.distance_slugs == "7km;14km;21-1km;28km"
	assert r.provider_slug == "iguana-sports"


def test_kids_run_note():
	km = km_to_slug_iguana_html_tests()
	html = (repo_root() / "scrapers" / "tests" / "fixtures" / "iguana_kids_stronger_2026.html").read_text(
		encoding="utf-8",
	)
	r = scrape_race("athenas-kids-run-stronger-2026", html, km_to_slug=km)
	assert r.distance_slugs == "kids-run"
