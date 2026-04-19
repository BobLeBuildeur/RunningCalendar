"""Tests for the PageLoader port (principle 2.4, §3.3).

The AI scraper now accepts both the legacy callable
``(url, prefer) -> LoadedPage`` *and* a class-based
:class:`~running_calendar_scrapers.ports.PageLoader` with a ``load(url)``
method. All browser-specific side effects (subprocess, ``os.environ``,
tempfile) live inside the :class:`CypressLoader` adapter.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from running_calendar_scrapers.ai_scraper import loader as loader_mod
from running_calendar_scrapers.ai_scraper.loader import LoadedPage
from running_calendar_scrapers.ai_scraper.scraper import scrape_race_with_ai
from running_calendar_scrapers.ports import (
	CypressLoader,
	PageLoader,
	RequestsLoader,
	default_page_loader,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "ai_scraper"


class _FakePageLoader:
	"""Port-shaped fake (``.load(url) -> LoadedPage``)."""

	def __init__(self, page: LoadedPage) -> None:
		self._page = page
		self.calls: list[str] = []

	def load(self, url: str) -> LoadedPage:
		self.calls.append(url)
		return self._page


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
		client = self

		class _Completions:
			def create(self_inner, **kwargs):  # noqa: N805
				return _FakeResponse(client._responses.pop(0))

		self.chat = SimpleNamespace(completions=_Completions())


# ---------- port types --------------------------------------------------


def test_fake_loader_satisfies_page_loader_port():
	page = LoadedPage(url="u", title="t", text="x", html="<p>x</p>", images=())
	fake = _FakePageLoader(page)
	assert isinstance(fake, PageLoader)


def test_requests_loader_satisfies_page_loader_port():
	assert isinstance(RequestsLoader(), PageLoader)


def test_cypress_loader_satisfies_page_loader_port():
	# We don't actually invoke Cypress — just verify it satisfies the Protocol.
	assert isinstance(CypressLoader(), PageLoader)


def test_default_page_loader_selects_by_prefer():
	assert isinstance(default_page_loader("requests"), RequestsLoader)
	assert isinstance(default_page_loader("cypress"), CypressLoader)
	# Auto returns a composite (not one of the two adapter classes).
	auto = default_page_loader("auto")
	assert isinstance(auto, PageLoader)


# ---------- scrape_race_with_ai accepts both shapes ---------------------


def test_scrape_race_with_ai_accepts_page_loader_port_instance():
	url = "https://example.com/race"
	html = (_FIXTURES / "tom_jerry.html").read_text(encoding="utf-8")
	page = LoadedPage(
		url=url,
		title="Fixture",
		text=loader_mod._clean_text(html),
		html=html,
		images=tuple(loader_mod._extract_images(html, url)),
	)
	fake_loader = _FakePageLoader(page)
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
					"distanceSlugs": "5km",
					"providerSlug": "yescom",
					"detailUrl": url,
				}
			)
		]
	)

	result = scrape_race_with_ai(
		url,
		prefer_loader="requests",
		client=client,
		page_loader=fake_loader,
	)

	assert result.race["name"] == "Fun Run Tom e Jerry 2026"
	assert fake_loader.calls == [url]
