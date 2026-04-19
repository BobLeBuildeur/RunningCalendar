"""Tests for the LLMExtractor port (principle 2.3).

Before this change, `scrape_race_with_ai` only accepted the raw
OpenAI-SDK-shaped `client=` / `text_model=` / `vision_model=` kwargs,
leaking provider specifics into every call site. It now accepts an
`extractor: LLMExtractor` port with `extract_from_text` / `extract_from_images`
methods; the OpenAI adapter is just one implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from running_calendar_scrapers.ai_scraper import loader as loader_mod
from running_calendar_scrapers.ai_scraper.loader import LoadedPage
from running_calendar_scrapers.ai_scraper.scraper import (
	AIScraperResult,
	scrape_race_with_ai,
)
from running_calendar_scrapers.ports import LLMExtractor

_FIXTURES = Path(__file__).parent / "fixtures" / "ai_scraper"


class _FakeExtractor:
	"""In-process :class:`LLMExtractor` that records calls and returns canned rows."""

	def __init__(self, text_row: dict | None, image_row: dict | None = None) -> None:
		self._text_row = text_row or {}
		self._image_row = image_row or {}
		self.text_calls: list[dict] = []
		self.image_calls: list[dict] = []

	def extract_from_text(self, *, url, title, text):
		self.text_calls.append({"url": url, "title": title, "text": text})
		return dict(self._text_row)

	def extract_from_images(self, *, url, title, image_urls: Iterable[str]):
		self.image_calls.append({"url": url, "title": title, "image_urls": list(image_urls)})
		return dict(self._image_row)


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


def test_fake_extractor_satisfies_llm_extractor_protocol():
	fake = _FakeExtractor(text_row={"sortKey": "2026-05-31T07:00", "name": "X"})
	# runtime_checkable isinstance guard.
	assert isinstance(fake, LLMExtractor)


def test_injected_extractor_is_used_instead_of_openai():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	fake = _FakeExtractor(
		text_row={
			"sortKey": "2026-05-31T07:00",
			"city": "São Paulo",
			"state": "SP",
			"country": "Brasil",
			"name": "Fun Run Tom e Jerry 2026",
			"typeSlug": "road",
			"distanceSlugs": "5",
			"providerSlug": "yescom",
			"detailUrl": url,
		}
	)

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		page_loader=loader,
		extractor=fake,
	)

	assert isinstance(result, AIScraperResult)
	assert result.source == "text"
	assert result.race["name"] == "Fun Run Tom e Jerry 2026"
	assert result.race["distanceSlugs"] == "5km"
	assert len(fake.text_calls) == 1
	assert fake.text_calls[0]["url"] == url
	assert fake.text_calls[0]["title"] == "Fixture"
	# Vision path must NOT have been consulted.
	assert fake.image_calls == []


def test_injected_extractor_triggers_vision_fallback_when_text_is_empty():
	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	fake = _FakeExtractor(
		text_row={},  # "insufficient" / empty
		image_row={
			"sortKey": "2026-06-07T09:00",
			"city": "Rio de Janeiro",
			"state": "RJ",
			"country": "Brasil",
			"name": "Poster Race",
			"typeSlug": "road",
			"distanceSlugs": "10",
			"providerSlug": "example",
			"detailUrl": url,
		},
	)

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		page_loader=loader,
		extractor=fake,
	)

	assert result.source == "image"
	assert result.images_inspected >= 1
	assert fake.text_calls and fake.image_calls
	# Image URLs actually forwarded to the port.
	assert isinstance(fake.image_calls[0]["image_urls"], list)
	assert len(fake.image_calls[0]["image_urls"]) >= 1


def test_legacy_client_kwarg_still_works_as_shim(monkeypatch):
	"""When `extractor=` is omitted, client= / text_model= / vision_model=
	still build the default OpenAI adapter (backwards compatibility).
	"""
	captured: dict[str, object] = {}

	class _StubOpenAIExtractor:
		def __init__(self, *, client=None, text_model=None, vision_model=None):
			captured["client"] = client
			captured["text_model"] = text_model
			captured["vision_model"] = vision_model

		def extract_from_text(self, *, url, title, text):
			return {
				"sortKey": "2026-05-31T07:00",
				"name": "Stub",
				"city": "São Paulo",
				"state": "SP",
				"country": "Brasil",
				"typeSlug": "road",
				"distanceSlugs": "5",
				"providerSlug": "yescom",
				"detailUrl": url,
			}

		def extract_from_images(self, *, url, title, image_urls):
			return {}

	import running_calendar_scrapers.ai_scraper.scraper as scraper_mod

	monkeypatch.setattr(scraper_mod, "OpenAILLMExtractor", _StubOpenAIExtractor)

	url = "https://example.com/race"
	loader = _fixture_loader("tom_jerry.html", url)
	sentinel_client = object()

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		page_loader=loader,
		client=sentinel_client,
		text_model="gpt-4o",
		vision_model="gpt-4o-mini",
	)

	assert result.source == "text"
	assert captured["client"] is sentinel_client
	assert captured["text_model"] == "gpt-4o"
	assert captured["vision_model"] == "gpt-4o-mini"
