"""Unit tests for ``db_ref.load_races_for_provider`` using an injectable fake connection.

These tests exercise the SQL string and the row-to-dict projection without
requiring a live Postgres — the query class is otherwise only reached from
``RUN_LIVE`` integration tests, which previously let a ``CALESCE`` typo slip
through (see ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §5.3).
"""

from __future__ import annotations

from running_calendar_scrapers.db_ref import (
	_LOAD_RACES_FOR_PROVIDER_SQL,
	load_races_for_provider,
)


class _FakeCursor:
	def __init__(self, rows):
		self._rows = rows
		self.executed: list[tuple[str, tuple]] = []

	def execute(self, sql, params):
		self.executed.append((sql, params))

	def fetchall(self):
		return list(self._rows)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		return False


class _FakeConnection:
	def __init__(self, rows):
		self._cursor = _FakeCursor(rows)

	def cursor(self):
		return self._cursor

	def close(self):
		pass


def test_load_races_for_provider_uses_coalesce_not_calesce():
	"""Guards against SQL typos in the race-rollup query."""
	assert "COALESCE" in _LOAD_RACES_FOR_PROVIDER_SQL
	assert "CALESCE(" not in _LOAD_RACES_FOR_PROVIDER_SQL.upper().replace("COALESCE(", "")


def test_load_races_for_provider_projects_row_shape():
	conn = _FakeConnection(
		rows=[
			(
				"2026-05-31T07:00",
				"São Paulo",
				"SP",
				"Brasil",
				"Fun Run Tom e Jerry 2026",
				"road",
				"yescom",
				"https://www.yescom.com.br/corridatomejerry/2026/index.asp",
				"2-5km;5km;10km",
			),
			(
				"2026-06-07T09:00",
				"Rio de Janeiro",
				"RJ",
				"Brasil",
				"Solo Race",
				"",  # type slug falls back to road
				"yescom",
				"https://www.yescom.com.br/solo/",
				None,  # NULL distance aggregation
			),
		]
	)
	rows = load_races_for_provider("yescom", conn=conn)

	assert len(rows) == 2
	assert rows[0]["sortKey"] == "2026-05-31T07:00"
	assert rows[0]["city"] == "São Paulo"
	assert rows[0]["distanceSlugs"] == "2-5km;5km;10km"
	assert rows[0]["providerSlug"] == "yescom"
	assert rows[1]["typeSlug"] == "road", "empty type_slug should fall back to 'road'"
	assert rows[1]["distanceSlugs"] == "", "NULL aggregation should become empty string"

	executed = conn.cursor().executed
	assert len(executed) == 1
	sql, params = executed[0]
	assert sql == _LOAD_RACES_FOR_PROVIDER_SQL
	assert params == ("yescom",)
