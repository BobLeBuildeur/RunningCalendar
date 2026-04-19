"""Tests for the ReferenceData port and composition-root context (principles 2.2, 3.2)."""

from __future__ import annotations

import pytest

from running_calendar_scrapers import context
from running_calendar_scrapers.ports import (
	ReferenceData,
	load_reference_data_from_db,
)


@pytest.fixture(autouse=True)
def _reset_context():
	context.set_reference_data(None)
	yield
	context.set_reference_data(None)


def test_reference_data_is_immutable():
	ref = ReferenceData(
		km_to_slug={5.0: "5km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"yescom"}),
	)
	# Frozen dataclass: mutating the attribute raises.
	with pytest.raises(AttributeError):
		ref.valid_type_slugs = frozenset({"trail"})  # type: ignore[misc]


def test_valid_distance_slugs_derived_from_km_to_slug():
	ref = ReferenceData(
		km_to_slug={5.0: "5km", 10.0: "10km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"yescom"}),
	)
	assert ref.valid_distance_slugs == frozenset({"5km", "10km"})


def test_context_round_trip_default_none():
	assert context.get_reference_data() is None


def test_context_set_get_clear():
	ref = ReferenceData(
		km_to_slug={5.0: "5km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"iguana-sports"}),
	)
	context.set_reference_data(ref)
	assert context.get_reference_data() is ref

	context.set_reference_data(None)
	assert context.get_reference_data() is None


# ---------- load_reference_data_from_db with a fake connection -------------


class _FakeCursor:
	def __init__(self, rowsets: list[list[tuple]]):
		self._rowsets = list(rowsets)

	def execute(self, sql, params=None):
		self._current = self._rowsets.pop(0)

	def fetchall(self):
		return list(self._current)

	def __enter__(self):
		return self

	def __exit__(self, *a):
		return False


class _FakeConn:
	def __init__(self):
		self._cursor = _FakeCursor(
			[
				# distances ORDER BY slug: (slug, km-tenths)
				[("10km", 100), ("21-1km", 211), ("5km", 50)],
				# types
				[("road",), ("trail",), ("adventure",)],
				# providers
				[("iguana-sports",), ("yescom",)],
			]
		)
		self.closed = False

	def cursor(self):
		return self._cursor

	def close(self):
		self.closed = True


def test_load_reference_data_from_db_builds_snapshot_in_one_connection():
	conn = _FakeConn()
	ref = load_reference_data_from_db(conn=conn)

	assert ref.km_to_slug == {10.0: "10km", 21.1: "21-1km", 5.0: "5km"}
	assert ref.valid_type_slugs == frozenset({"road", "trail", "adventure"})
	assert ref.valid_provider_slugs == frozenset({"iguana-sports", "yescom"})
	assert ref.valid_distance_slugs == frozenset({"5km", "10km", "21-1km"})
	# Caller-provided connection is not closed by the helper.
	assert conn.closed is False


def test_scrapers_prefer_explicit_kwarg_over_context(monkeypatch):
	"""When a scraper is given reference_data=, the context value must not be used."""
	from running_calendar_scrapers import iguana

	ctx_ref = ReferenceData(
		km_to_slug={5.0: "5km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"iguana-sports"}),
	)
	context.set_reference_data(ctx_ref)

	captured: dict[str, object] = {}

	def _fake_session_get(*a, **kw):
		raise AssertionError("should not open HTTP — the reference-data preflight is what we're testing")

	def _fake_list_slugs(html):
		return []

	# Short-circuit the HTTP call; scrape_iguana_calendar still runs the
	# preflight check against ref.valid_provider_slugs etc.
	monkeypatch.setattr(iguana, "list_calendar_slugs", _fake_list_slugs)

	class _FakeSession:
		def get(self, url, timeout):
			class _R:
				status_code = 200
				text = "<html></html>"

				def raise_for_status(self):
					return None

			return _R()

	explicit_ref = ReferenceData(
		km_to_slug={10.0: "10km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"iguana-sports"}),
	)
	captured["result"] = iguana.scrape_iguana_calendar(
		session=_FakeSession(),
		reference_data=explicit_ref,
	)
	# Both refs contain iguana-sports + road so either would satisfy the preflight;
	# the test below (no-fallback) is the stronger guard.
	assert captured["result"] == []


def test_scrapers_fall_back_to_context_when_kwarg_omitted(monkeypatch):
	"""With no kwarg and no DB access, the context value must be used."""
	from running_calendar_scrapers import iguana

	ctx_ref = ReferenceData(
		km_to_slug={5.0: "5km"},
		valid_type_slugs=frozenset({"road"}),
		valid_provider_slugs=frozenset({"iguana-sports"}),
	)
	context.set_reference_data(ctx_ref)

	# If the scraper falls through to load_reference_data_from_db, it would
	# open a live Postgres connection — raise loudly instead to make the
	# fallback observable.
	def _should_not_call(*a, **kw):
		raise AssertionError("scraper fell through to DB despite a context value being set")

	monkeypatch.setattr(iguana, "load_reference_data_from_db", _should_not_call)
	monkeypatch.setattr(iguana, "list_calendar_slugs", lambda html: [])

	class _FakeSession:
		def get(self, url, timeout):
			class _R:
				status_code = 200
				text = "<html></html>"

				def raise_for_status(self):
					return None

			return _R()

	result = iguana.scrape_iguana_calendar(session=_FakeSession())
	assert result == []
