"""Tests for injected AI-scraper whitelists (principle 4.5 + 4.6).

Cover two fixes:

- The AI scraper used to hard-code ``{road, trail, adventure}`` and
  ``country="Brasil"`` in ``_postprocess``. Both are now caller-injected.
- ``normalize_distance_slugs`` used to accept any tenths-of-km value the
  LLM produced, even slugs absent from ``public.distances``. Callers can
  now pass ``valid_distance_slugs=`` to drop those.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from running_calendar_scrapers.ai_scraper import loader as loader_mod
from running_calendar_scrapers.ai_scraper.distance import normalize_distance_slugs
from running_calendar_scrapers.ai_scraper.loader import LoadedPage
from running_calendar_scrapers.ai_scraper.scraper import (
	DEFAULT_COUNTRY,
	DEFAULT_VALID_TYPE_SLUGS,
	scrape_race_with_ai,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "ai_scraper"


# ---------------------------------------------------------------------------
# normalize_distance_slugs whitelist


def test_normalize_distance_slugs_drops_slugs_not_in_whitelist():
	valid = {"5km", "10km", "21-1km"}
	# ``3-7km`` is well-formed but outside the whitelist; must be dropped.
	result = normalize_distance_slugs("5km;3-7km;10km;21.1km", valid_slugs=valid)
	assert result == "5km;10km;21-1km"


def test_normalize_distance_slugs_no_whitelist_keeps_legacy_behaviour():
	# Backwards compatible: without a whitelist, every well-formed slug
	# passes through (the legacy AI scraper behaviour). Output is sorted
	# by km, so '3-7km' (3.7) precedes '5km'.
	assert normalize_distance_slugs("5;3.7;10") == "3-7km;5km;10km"


def test_normalize_distance_slugs_empty_whitelist_drops_everything():
	assert normalize_distance_slugs("5km;10km", valid_slugs=set()) == ""


# ---------------------------------------------------------------------------
# _postprocess via scrape_race_with_ai


class _FakeMessage:
	def __init__(self, content: str):
		self.content = content


class _FakeChoice:
	def __init__(self, content: str):
		self.message = _FakeMessage(content)


class _FakeResponse:
	def __init__(self, content: str):
		self.choices = [_FakeChoice(content)]


class _FakeClient:
	def __init__(self, responses: list[str]):
		self._responses = list(responses)
		self.calls: list[dict] = []
		client = self

		class _Completions:
			def create(self_inner, **kwargs):  # noqa: N805 - mimic OpenAI SDK signature
				client.calls.append(kwargs)
				return _FakeResponse(client._responses.pop(0))

		self.chat = SimpleNamespace(completions=_Completions())


def _fixture_loader(name: str, url: str):
	html = (_FIXTURES / name).read_text(encoding="utf-8")

	def _loader(target_url: str, prefer: str) -> LoadedPage:
		return LoadedPage(
			url=url,
			title="Fixture",
			text=loader_mod._clean_text(html),
			html=html,
			images=tuple(loader_mod._extract_images(html, url)),
		)

	return _loader


def _model_row(url: str, *, type_slug: str, distances: str, country: str = "") -> dict:
	return {
		"sortKey": "2026-05-31T07:00",
		"city": "São Paulo",
		"state": "SP",
		"country": country,
		"name": "Injected Whitelist Race",
		"typeSlug": type_slug,
		"distanceSlugs": distances,
		"providerSlug": "yescom",
		"detailUrl": url,
	}


def test_default_type_whitelist_coerces_unknown_to_road():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(responses=[json.dumps(_model_row(url, type_slug="ski", distances="5km"))])

	result = scrape_race_with_ai(url, prefer_loader="requests", client=client, page_loader=loader)

	assert result.race["typeSlug"] == "road", "unknown type must fall back to 'road'"
	assert "road" in DEFAULT_VALID_TYPE_SLUGS


def test_injected_type_whitelist_preserves_caller_choice():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(responses=[json.dumps(_model_row(url, type_slug="ultra", distances="5km"))])

	# Caller registered 'ultra' upstream (e.g. new row in public.types);
	# 'ultra' must now survive the postprocess coercion.
	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=loader,
		valid_types={"road", "trail", "ultra"},
	)

	assert result.race["typeSlug"] == "ultra"


def test_injected_whitelist_without_road_picks_deterministic_fallback():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(responses=[json.dumps(_model_row(url, type_slug="made-up", distances="5km"))])

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=loader,
		valid_types={"cycling", "skating"},
	)

	# Deterministic alphabetical fallback when 'road' is not registered.
	assert result.race["typeSlug"] == "cycling"


def test_injected_distance_whitelist_drops_slugs_absent_from_public_distances():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	# The model asks for a distance ('3.7') the DB does not have.
	client = _FakeClient(
		responses=[json.dumps(_model_row(url, type_slug="road", distances="5;3.7;10"))]
	)

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=loader,
		valid_distance_slugs={"5km", "10km", "21-1km"},
	)

	assert result.race["distanceSlugs"] == "5km;10km", (
		"'3-7km' is not in the injected whitelist; LLM must not invent it"
	)


def test_default_country_applies_when_model_leaves_it_empty():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(responses=[json.dumps(_model_row(url, type_slug="road", distances="5km"))])

	result = scrape_race_with_ai(url, prefer_loader="requests", client=client, page_loader=loader)

	assert result.race["country"] == DEFAULT_COUNTRY == "Brasil"


def test_injected_default_country_overrides_brasil():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(responses=[json.dumps(_model_row(url, type_slug="road", distances="5km"))])

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=loader,
		default_country="Portugal",
	)

	assert result.race["country"] == "Portugal"


def test_model_supplied_country_wins_over_default():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	client = _FakeClient(
		responses=[json.dumps(_model_row(url, type_slug="road", distances="5km", country="Chile"))]
	)

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=loader,
		default_country="Portugal",
	)

	assert result.race["country"] == "Chile"
