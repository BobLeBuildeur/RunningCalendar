"""End-to-end tests for the AI scraper pipeline using a mocked OpenAI client.

No network access is performed: the loader is monkey-patched to return the
local fixture HTML and the OpenAI client is replaced with a stub that returns
pre-canned structured JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from running_calendar_scrapers.ai_scraper import loader as loader_mod
from running_calendar_scrapers.ai_scraper.loader import LoadedPage
from running_calendar_scrapers.ai_scraper.scraper import AIScraperError, scrape_race_with_ai

_FIXTURES = Path(__file__).parent / "fixtures" / "ai_scraper"


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
	"""Mimics ``openai.OpenAI`` for tests.

	Responses are a list of JSON strings returned in order for successive
	``chat.completions.create`` calls.
	"""

	def __init__(self, responses: list[str]):
		self._responses = list(responses)
		self.calls: list[dict] = []
		client = self

		class _Completions:
			def create(self_inner, **kwargs):  # noqa: N805 - mimic OpenAI SDK signature
				client.calls.append(kwargs)
				if not client._responses:
					raise AssertionError("No more canned responses available")
				return _FakeResponse(client._responses.pop(0))

		self.chat = SimpleNamespace(completions=_Completions())


def _fixture_loader(name: str, url: str):
	html = (_FIXTURES / name).read_text(encoding="utf-8")

	def _loader(target_url: str, *, prefer: str = "auto") -> LoadedPage:
		assert target_url == url
		return LoadedPage(
			url=url,
			title="Fixture",
			text=loader_mod._clean_text(html),
			html=html,
			images=tuple(loader_mod._extract_images(html, url)),
		)

	return _loader


def test_scrape_race_with_ai_text_path_tom_jerry(monkeypatch):
	url = "https://www.yescom.com.br/corridatomejerry/2026/index.asp"
	monkeypatch.setattr(
		"running_calendar_scrapers.ai_scraper.scraper.load_page",
		_fixture_loader("tom_jerry.html", url),
	)
	client = _FakeClient(
		responses=[
			json.dumps(
				{
					"sortKey": "2026-05-31T07:00",
					"city": "São Paulo",
					"state": "SP",
					"country": "Brasil",
					"name": "Fun Run Tom e Jerry 2026",
					"typeSlug": "road",
					"distanceSlugs": "2.5;5;10",
					"providerSlug": "yescom",
					"detailUrl": url,
				}
			)
		]
	)

	result = scrape_race_with_ai(url, prefer_loader="requests", client=client)

	assert result.source == "text"
	assert result.images_inspected == 0
	assert result.race["sortKey"] == "2026-05-31T07:00"
	assert result.race["name"] == "Fun Run Tom e Jerry 2026"
	assert result.race["city"] == "São Paulo"
	assert result.race["state"] == "SP"
	assert result.race["country"] == "Brasil"
	assert result.race["distanceSlugs"] == "2-5km;5km;10km"
	assert result.race["typeSlug"] == "road"
	assert result.race["providerSlug"] == "yescom"
	assert result.race["detailUrl"] == url
	assert len(client.calls) == 1


def test_scrape_race_with_ai_text_path_ktr(monkeypatch):
	url = "https://xkrsports.com.br/ktrcampos/"
	monkeypatch.setattr(
		"running_calendar_scrapers.ai_scraper.scraper.load_page",
		_fixture_loader("ktr.html", url),
	)
	client = _FakeClient(
		responses=[
			json.dumps(
				{
					"sortKey": "2026-04-09T00:00",
					"city": "Campos do Jordão",
					"state": "SP",
					"country": "Brasil",
					"name": "KTR Campos do Jordão",
					"typeSlug": "trail",
					"distanceSlugs": "7;12;21;30;50;80",
					"providerSlug": "xkrsports",
					"detailUrl": url,
				}
			)
		]
	)

	result = scrape_race_with_ai(url, prefer_loader="requests", client=client)

	assert result.source == "text"
	assert result.race["typeSlug"] == "trail"
	assert result.race["distanceSlugs"] == "7km;12km;21km;30km;50km;80km"
	assert result.race["providerSlug"] == "xkrsports"


def test_scrape_race_with_ai_falls_back_to_vision(monkeypatch):
	url = "https://example.com/race"
	monkeypatch.setattr(
		"running_calendar_scrapers.ai_scraper.scraper.load_page",
		_fixture_loader("empty.html", url),
	)
	client = _FakeClient(
		responses=[
			json.dumps({"insufficient": True}),
			json.dumps(
				{
					"sortKey": "2026-05-31T07:00",
					"city": "Rio de Janeiro",
					"state": "RJ",
					"country": "Brasil",
					"name": "Poster Race",
					"typeSlug": "road",
					"distanceSlugs": "5;10",
					"providerSlug": "example",
					"detailUrl": url,
				}
			),
		]
	)

	result = scrape_race_with_ai(url, prefer_loader="requests", client=client)

	assert result.source == "image"
	assert result.images_inspected == 1
	assert result.race["name"] == "Poster Race"
	assert result.race["distanceSlugs"] == "5km;10km"
	assert len(client.calls) == 2
	second_call = client.calls[1]
	user_content = second_call["messages"][-1]["content"]
	assert any(part.get("type") == "image_url" for part in user_content)


def test_scrape_race_with_ai_errors_when_both_paths_empty(monkeypatch):
	url = "https://example.com/race"
	monkeypatch.setattr(
		"running_calendar_scrapers.ai_scraper.scraper.load_page",
		_fixture_loader("empty.html", url),
	)
	client = _FakeClient(
		responses=[
			json.dumps({"insufficient": True}),
			json.dumps({"insufficient": True}),
		]
	)

	with pytest.raises(AIScraperError):
		scrape_race_with_ai(url, prefer_loader="requests", client=client)


def test_scrape_race_with_ai_errors_when_no_images_and_text_empty(monkeypatch):
	# No <img> tags present -> the image fallback has nothing to inspect.
	url = "https://example.com/bare"

	def _loader(target_url: str, *, prefer: str = "auto") -> LoadedPage:
		return LoadedPage(
			url=url,
			title="Bare",
			text="Not a race page",
			html="<html><body><p>Not a race page</p></body></html>",
			images=(),
		)

	monkeypatch.setattr(
		"running_calendar_scrapers.ai_scraper.scraper.load_page",
		_loader,
	)
	client = _FakeClient(responses=[json.dumps({"insufficient": True})])

	with pytest.raises(AIScraperError):
		scrape_race_with_ai(url, prefer_loader="requests", client=client)
