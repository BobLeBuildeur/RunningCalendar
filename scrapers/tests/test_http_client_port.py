"""Tests for the HttpClient port (principle 2.1).

The HttpClient Protocol formalises the narrow surface scrapers need from
HTTP infrastructure: a ``get_text(url, *, timeout)`` method that raises
on non-2xx and returns a decoded body. RequestsHttpClient is the default
adapter.
"""

from __future__ import annotations

import pytest

from running_calendar_scrapers.http import DEFAULT_USER_AGENT, make_session
from running_calendar_scrapers.ports import HttpClient, RequestsHttpClient


class _FakeHttpClient:
	"""Minimal fake that satisfies the HttpClient Protocol without hitting the network."""

	def __init__(self, body: str = "hello") -> None:
		self._body = body
		self.calls: list[tuple[str, int]] = []

	def get_text(self, url: str, *, timeout: int = 60) -> str:
		self.calls.append((url, timeout))
		return self._body


def test_fake_satisfies_http_client_protocol():
	client = _FakeHttpClient()
	assert isinstance(client, HttpClient)


def test_requests_http_client_satisfies_protocol():
	client = RequestsHttpClient()
	assert isinstance(client, HttpClient)


def test_requests_http_client_reuses_session_across_calls():
	session = make_session()
	client = RequestsHttpClient(session=session)
	# Same session object every time (connection pooling + shared headers).
	assert client.session is session
	assert client.session.headers["User-Agent"] == DEFAULT_USER_AGENT


def test_requests_http_client_applies_custom_user_agent():
	custom = make_session(user_agent="custom/1.0")
	client = RequestsHttpClient(session=custom)
	assert client.session.headers["User-Agent"] == "custom/1.0"


def test_requests_http_client_raises_on_http_error(monkeypatch):
	class _Resp:
		encoding = "utf-8"
		apparent_encoding = "utf-8"

		def raise_for_status(self):
			raise RuntimeError("404 Not Found")

	class _Session:
		headers: dict[str, str] = {}

		def get(self, url, timeout):
			return _Resp()

	client = RequestsHttpClient(session=_Session())  # type: ignore[arg-type]
	with pytest.raises(RuntimeError, match="404"):
		client.get_text("https://example.com", timeout=1)


def test_requests_http_client_decodes_iso_8859_1_as_apparent():
	"""Yescom's ASP endpoint returns ISO-8859-1 without declaring UTF-8."""

	class _Resp:
		encoding: str | None = "ISO-8859-1"
		apparent_encoding = "utf-8"
		text = "São Paulo"

		def raise_for_status(self):
			return None

	class _Session:
		headers: dict[str, str] = {}

		def get(self, url, timeout):
			return _Resp()

	client = RequestsHttpClient(session=_Session())  # type: ignore[arg-type]
	body = client.get_text("https://example.com", timeout=1)
	assert body == "São Paulo"
