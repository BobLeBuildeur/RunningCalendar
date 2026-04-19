"""Ports (typed seams) for scraper infrastructure.

Four capabilities every scraper needs from the outside world are declared here
as runtime-checkable :class:`~typing.Protocol` types so scrapers and tests can
talk to stable, narrow interfaces instead of concrete SDKs / drivers /
subprocesses:

- :class:`HttpClient` — issue an HTTP GET and return the response body.
- :class:`ReferenceData` — snapshot of ``public.distances`` / ``public.types`` /
  ``public.providers`` loaded once at the composition root.
- :class:`LLMExtractor` — extract a structured race row from text or images.
- :class:`PageLoader` — render a URL into a :class:`LoadedPage`.

Default adapters live alongside each Protocol (``default_http_client``,
``load_reference_data_from_db``, ``OpenAILLMExtractor``, ``RequestsLoader``,
``CypressLoader``). See ``docs/reports/2026-04-17-scraper-architecture-audit.md``
§2.1–§2.4 and §3.2–§3.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

import requests

from running_calendar_scrapers.http import make_session


# ---------------------------------------------------------------------------
# HTTP port (§2.1)


@runtime_checkable
class HttpClient(Protocol):
	"""Narrow HTTP GET surface used by every scraper.

	Implementations must return a decoded string body (charset detection is
	the adapter's responsibility) and raise on non-2xx responses.
	"""

	def get_text(self, url: str, *, timeout: int = 60) -> str: ...  # pragma: no cover


class RequestsHttpClient:
	"""Default :class:`HttpClient` adapter backed by a :mod:`requests` session.

	A single session is reused across calls so connection pooling and the
	configured ``User-Agent`` / extra headers apply to every request.
	"""

	def __init__(self, session: requests.Session | None = None) -> None:
		self._session = session or make_session()

	@property
	def session(self) -> requests.Session:
		return self._session

	def get_text(self, url: str, *, timeout: int = 60) -> str:
		resp = self._session.get(url, timeout=timeout)
		resp.raise_for_status()
		if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
			resp.encoding = resp.apparent_encoding
		return resp.text


# ---------------------------------------------------------------------------
# Reference-data port (§2.2)


@dataclass(frozen=True)
class ReferenceData:
	"""Snapshot of the reference tables the scrapers validate against.

	One instance is typically built at the composition root and passed to
	every scraper; offline tests build a :class:`ReferenceData` directly
	with the fixture dicts they need.
	"""

	km_to_slug: Mapping[float, str]
	valid_type_slugs: frozenset[str]
	valid_provider_slugs: frozenset[str]

	@property
	def valid_distance_slugs(self) -> frozenset[str]:
		return frozenset(self.km_to_slug.values())


def load_reference_data_from_db(conn: Any | None = None) -> ReferenceData:
	"""Build a :class:`ReferenceData` from a single live Postgres connection.

	Used by the CLI composition root. When ``conn`` is ``None`` the helper
	opens a connection via :func:`db_ref._connect` (env-var driven).
	Replaces the previous pattern of three independent ``SELECT`` queries
	each opening its own psycopg2 connection.
	"""
	from running_calendar_scrapers import db_ref

	own = conn is None
	c = conn or db_ref._connect()
	try:
		km_to_slug = dict(db_ref.load_distance_slugs_by_km(c))
		valid_types = frozenset(db_ref.load_valid_type_slugs(c))
		valid_providers = frozenset(db_ref.load_valid_provider_slugs(c))
	finally:
		if own:
			c.close()
	return ReferenceData(
		km_to_slug=km_to_slug,
		valid_type_slugs=valid_types,
		valid_provider_slugs=valid_providers,
	)


# ---------------------------------------------------------------------------
# LLM port (§2.3)


@runtime_checkable
class LLMExtractor(Protocol):
	"""Adapter that asks a model for a structured race row.

	The return value is a flat dict whose keys match
	:data:`running_calendar_scrapers.race_row.RACE_ROW_KEYS`; an empty
	dict means "the model was not confident" and triggers the vision
	fallback.
	"""

	def extract_from_text(self, *, url: str, title: str, text: str) -> dict[str, Any]: ...  # pragma: no cover
	def extract_from_images(
		self, *, url: str, title: str, image_urls: Iterable[str]
	) -> dict[str, Any]: ...  # pragma: no cover


class OpenAILLMExtractor:
	"""Default :class:`LLMExtractor` adapter wrapping the OpenAI SDK.

	Thin wrapper around :func:`ai_scraper.extractor.extract_from_text` and
	:func:`ai_scraper.extractor.extract_from_images` so the concrete SDK
	shape (``chat.completions.create``, Structured Outputs payload) never
	surfaces in the scraper pipeline.
	"""

	def __init__(
		self,
		*,
		client: Any | None = None,
		text_model: str | None = None,
		vision_model: str | None = None,
	) -> None:
		self._client = client
		self._text_model = text_model
		self._vision_model = vision_model

	def extract_from_text(self, *, url: str, title: str, text: str) -> dict[str, Any]:
		from running_calendar_scrapers.ai_scraper.extractor import extract_from_text

		kwargs: dict[str, Any] = {
			"url": url,
			"title": title,
			"text": text,
			"client": self._client,
		}
		if self._text_model:
			kwargs["model"] = self._text_model
		return extract_from_text(**kwargs)

	def extract_from_images(
		self, *, url: str, title: str, image_urls: Iterable[str]
	) -> dict[str, Any]:
		from running_calendar_scrapers.ai_scraper.extractor import extract_from_images

		kwargs: dict[str, Any] = {
			"url": url,
			"title": title,
			"image_urls": image_urls,
			"client": self._client,
		}
		if self._vision_model:
			kwargs["model"] = self._vision_model
		return extract_from_images(**kwargs)


# ---------------------------------------------------------------------------
# Page-loader port (§2.4, §3.3)


@runtime_checkable
class PageLoader(Protocol):
	"""Render a URL into a :class:`LoadedPage` snapshot."""

	def load(self, url: str) -> "LoadedPage": ...  # pragma: no cover


class RequestsLoader:
	"""Default :class:`PageLoader` adapter backed by :mod:`requests`.

	Drops the browser dependency entirely — suitable for static pages,
	tests, and CI environments without Chrome.
	"""

	def __init__(self, *, timeout: int = 30) -> None:
		self._timeout = timeout

	def load(self, url: str) -> "LoadedPage":
		from running_calendar_scrapers.ai_scraper.loader import load_via_requests

		return load_via_requests(url, timeout=self._timeout)


class CypressLoader:
	"""Browser-backed :class:`PageLoader` adapter.

	All browser-specific side effects (``os.environ`` mutation, ``tempfile``
	coordination, ``subprocess.run`` into ``npx cypress``) are contained
	inside this adapter — the scraper pipeline only sees the port's
	:meth:`load` method. Raises :class:`RuntimeError` when Cypress is not
	installed so the caller can fall back deterministically.
	"""

	def __init__(self, *, timeout: int = 120) -> None:
		self._timeout = timeout

	def load(self, url: str) -> "LoadedPage":
		from running_calendar_scrapers.ai_scraper.loader import load_via_cypress

		return load_via_cypress(url, timeout=self._timeout)


def default_page_loader(prefer: str = "auto") -> PageLoader:
	"""Select a :class:`PageLoader` adapter based on ``prefer``.

	``"auto"`` uses Cypress when available and falls back to
	:class:`RequestsLoader` on any failure (useful in CI without a browser).
	``"cypress"`` forces the browser adapter and raises if it fails.
	``"requests"`` skips the browser entirely.
	"""
	if prefer == "requests":
		return RequestsLoader()
	if prefer == "cypress":
		return CypressLoader()
	return _AutoPageLoader()


class _AutoPageLoader:
	"""Composite that tries :class:`CypressLoader` first, falls back to requests."""

	def __init__(self) -> None:
		self._cypress = CypressLoader()
		self._fallback = RequestsLoader()

	def load(self, url: str) -> "LoadedPage":
		from running_calendar_scrapers.ai_scraper.loader import _cypress_available

		if _cypress_available():
			try:
				return self._cypress.load(url)
			except Exception:
				# Fall back so the CLI remains usable in headless CI.
				pass
		return self._fallback.load(url)


__all__ = [
	"CypressLoader",
	"HttpClient",
	"LLMExtractor",
	"OpenAILLMExtractor",
	"PageLoader",
	"ReferenceData",
	"RequestsHttpClient",
	"RequestsLoader",
	"default_page_loader",
	"load_reference_data_from_db",
]


# Type checkers need a forward-reference target without a runtime import cycle.
from running_calendar_scrapers.ai_scraper.loader import LoadedPage  # noqa: E402
