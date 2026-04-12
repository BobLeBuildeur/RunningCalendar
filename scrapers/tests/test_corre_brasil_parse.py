"""Unit tests for Corre Brasil calendar parsing (fixture HTML, no network)."""

from __future__ import annotations

from pathlib import Path

from running_calendar_scrapers.corre_brasil import (
	_parse_event_day_month,
	_parse_place_line,
	scrape_corre_brasil_calendar_html,
)


def test_parse_day_month_variants():
	assert _parse_event_day_month("12 de Abril", 2026) == (12, 4)
	assert _parse_event_day_month("29 à 31 de Maio", 2026) == (29, 5)
	assert _parse_event_day_month("31 de Julho à 02 de Agosto", 2026) == (31, 7)
	assert _parse_event_day_month("17 e 18 de Outubro", 2026) == (17, 10)
	assert _parse_event_day_month("25 e 26 de Abril", 2026) == (25, 4)
	assert _parse_event_day_month("11 a 15 de Novembro", 2026) == (11, 11)
	assert _parse_event_day_month("01 a 06 de Setembro", 2026) == (1, 9)


def test_parse_place():
	assert _parse_place_line("Camboriú/SC") == ("Camboriú", "SC", "Brasil")
	assert _parse_place_line("Santa Catarina") == ("Santa Catarina", "SC", "Brasil")


def test_fixture_repeater_snapshot():
	fixture = Path(__file__).parent / "fixtures" / "corre_brasil_repeater.html"
	html = fixture.read_text(encoding="utf-8")
	races = scrape_corre_brasil_calendar_html(html, year=2026, calendar_url="https://www.correbrasil.com.br/calendario-corridas")
	by_name = {r.name: r for r in races}
	assert len(races) == 12
	gv = by_name["GV LIFE RUN GREEN VALLEY"]
	assert gv.sort_key == "2026-04-12T12:00"
	assert gv.city == "Camboriú" and gv.state == "SC"
	assert gv.type_slug == "road"
	assert gv.detail_url.startswith("https://www.guicheweb.com.br/")
	meia_bc = by_name["MEIA MARATONA INTERNACIONAL DE BALNEÁRIO CAMBORIÚ"]
	assert "meiadebc2026" in meia_bc.detail_url
	mons = by_name["MONS ULTRA TRAIL"]
	assert mons.type_slug == "trail"
	assert mons.detail_url == "https://monsultratrail.com.br/"
	volta = by_name["VOLTA CICLÍSTICA"]
	assert volta.type_slug == "adventure"
	assert volta.detail_url.endswith("/calendario-corridas")
