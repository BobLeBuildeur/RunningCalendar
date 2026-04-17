"""Unit tests for slug helpers used by the AI scraper."""

from __future__ import annotations

from running_calendar_scrapers.ai_scraper.slug import provider_slug_from_url, slugify


def test_slugify_basic():
	assert slugify("Corre Brasil") == "corre-brasil"
	assert slugify("São Paulo  Running!") == "sao-paulo-running"
	assert slugify("") == ""
	assert slugify("ALREADY-OK") == "already-ok"


def test_provider_slug_from_url_br_domain():
	assert provider_slug_from_url(
		"https://www.yescom.com.br/corridatomejerry/2026/index.asp",
	) == "yescom"
	assert provider_slug_from_url("https://xkrsports.com.br/ktrcampos/") == "xkrsports"


def test_provider_slug_from_url_regular_domain():
	assert provider_slug_from_url("https://iguanasports.com/events/12") == "iguanasports"
	assert provider_slug_from_url("") == ""
