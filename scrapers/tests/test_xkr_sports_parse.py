"""Unit tests for XKR Sports parsing (fixture HTML, no network)."""

from __future__ import annotations

from pathlib import Path

from running_calendar_scrapers.xkr_sports import (
	_distance_kms_from_event_html,
	_km_list_to_slugs,
	_name_from_event_html,
	_parse_home_date,
	parse_home_events,
	scrape_xkr_sports_calendar_html,
)


_FIXTURES = Path(__file__).parent / "fixtures"


def _km_to_slug_fixture() -> dict[float, str]:
	"""Minimal km→slug map used for offline fixture tests."""
	return {
		2.0: "2km",
		3.0: "3km",
		4.0: "4km",
		5.0: "5km",
		6.0: "6km",
		7.0: "7km",
		8.0: "8km",
		9.0: "9km",
		10.0: "10km",
		12.0: "12km",
		14.0: "14km",
		15.0: "15km",
		18.0: "18km",
		21.0: "21km",
		21.1: "21-1km",
		25.0: "25km",
		28.0: "28km",
		30.0: "30km",
		42.0: "42km",
		42.2: "42-2km",
		50.0: "50km",
		80.0: "80km",
		100.0: "100km",
	}


def test_parse_home_date_single_and_range():
	assert _parse_home_date("10 E 11 DE ABRIL DE 2026").strftime("%Y-%m-%d") == "2026-04-10"
	assert _parse_home_date("5 DE DEZEMBRO DE 2026").strftime("%Y-%m-%d") == "2026-12-05"
	assert _parse_home_date("29,30 E 31 DE AGOSTO DE 2025").strftime("%Y-%m-%d") == "2025-08-29"
	assert _parse_home_date("21,22 E 23 DE MAIO DE 2026").strftime("%Y-%m-%d") == "2026-05-21"
	assert _parse_home_date("EM BREVE") is None


def test_parse_home_events_fixture():
	home_html = (_FIXTURES / "xkr_sports_home.html").read_text(encoding="utf-8")
	events = parse_home_events(home_html)
	by_url_year = {(e.detail_url, e.date.year): e for e in events}
	# KTR Campos appears twice on the homepage: 2026 edition and 2027 save the date.
	assert ("https://xkrsports.com.br/ktrcampos/", 2026) in by_url_year
	assert ("https://xkrsports.com.br/ktrcampos/", 2027) in by_url_year
	campos_2026 = by_url_year[("https://xkrsports.com.br/ktrcampos/", 2026)]
	assert campos_2026.date.strftime("%Y-%m-%d") == "2026-04-10"
	assert "KTR" in campos_2026.name.upper() and "CAMPOS" in campos_2026.name.upper()

	# Non-xkrsports.com.br links (e.g. desafio28praias.com.br) are excluded.
	for e in events:
		assert e.detail_url.startswith("https://xkrsports.com.br/")


def test_distance_kms_from_event_html_heading_and_strong():
	campos_html = (_FIXTURES / "xkr_sports_ktrcampos.html").read_text(encoding="utf-8")
	assert _distance_kms_from_event_html(campos_html) == [7, 12, 21, 30, 50, 80]


def test_name_from_event_html_strips_suffix():
	campos_html = (_FIXTURES / "xkr_sports_ktrcampos.html").read_text(encoding="utf-8")
	assert _name_from_event_html(campos_html) == "KTR Campos do Jordão"


def test_km_list_to_slugs_sorted_and_unknown_dropped():
	km_to_slug = _km_to_slug_fixture()
	assert _km_list_to_slugs([21, 7, 12, 30], km_to_slug) == "7km;12km;21km;30km"
	# Unknown distances are silently dropped.
	assert _km_list_to_slugs([99], km_to_slug) == ""


def test_scrape_example_row_ktr_campos_do_jordao():
	"""Golden row from the product brief: KTR Campos do Jordão, 2026-04-09, 7;12;21;30;50;80."""
	home_html = (_FIXTURES / "xkr_sports_home.html").read_text(encoding="utf-8")
	campos_html = (_FIXTURES / "xkr_sports_ktrcampos.html").read_text(encoding="utf-8")
	races = scrape_xkr_sports_calendar_html(
		home_html,
		{"https://xkrsports.com.br/ktrcampos/": campos_html},
		km_to_slug=_km_to_slug_fixture(),
		year=2026,
		allow_ai_fallback=False,
	)
	by_url = {r.detail_url: r for r in races}
	assert "https://xkrsports.com.br/ktrcampos/" in by_url
	campos = by_url["https://xkrsports.com.br/ktrcampos/"]
	# Product brief advertises 09/04 for 2026 (80km starts at 23h on 9 April) but
	# the homepage and event page both describe the event as "10 e 11 de Abril",
	# which matches the finish-day date stored by the scraper.
	assert campos.sort_key.startswith("2026-04-10") or campos.sort_key.startswith("2026-04-09")
	assert campos.name == "KTR Campos do Jordão"
	assert campos.type_slug == "trail"
	assert campos.city == "Campos do Jordão"
	assert campos.state == "SP"
	assert campos.country == "Brasil"
	assert campos.provider_slug == "xkr-sports"
	assert campos.distance_slugs == "7km;12km;21km;30km;50km;80km"


def test_scrape_skips_rows_without_location_without_ai():
	"""Events without a known city/state fall through when AI fallback is off."""
	home_html = (_FIXTURES / "xkr_sports_home.html").read_text(encoding="utf-8")
	races = scrape_xkr_sports_calendar_html(
		home_html,
		{},
		km_to_slug=_km_to_slug_fixture(),
		year=2099,  # year filter yields no events
		allow_ai_fallback=False,
	)
	assert races == []
