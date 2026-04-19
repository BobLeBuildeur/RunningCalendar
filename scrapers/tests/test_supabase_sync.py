"""Tests for the Supabase sync layer (principle 1.4).

Exercises both the pure planner (:func:`plan_supabase_sync`) and the
composition root (:func:`sync_scraped_rows_to_supabase`) with an injected
fake DB-API connection. No live database required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from running_calendar_scrapers.supabase_sync import (
	SupabaseSyncPlan,
	insert_races_and_distances,
	plan_supabase_sync,
	sync_scraped_rows_to_supabase,
)


def _reference_csvs(tmp_path: Path) -> Path:
	data_dir = tmp_path / "data"
	data_dir.mkdir()
	(data_dir / "distances.csv").write_text(
		"slug,km,description\n5km,50,\n10km,100,\n",
		encoding="utf-8",
	)
	(data_dir / "types.csv").write_text("slug,type\nroad,Road\n", encoding="utf-8")
	(data_dir / "providers.csv").write_text(
		"slug,name,website\np1,P1,https://p1\n",
		encoding="utf-8",
	)
	return data_dir


def _row(**over: str) -> dict[str, str]:
	base = {
		"sortKey": "2026-02-01T10:00",
		"city": "Y",
		"state": "RJ",
		"country": "Brasil",
		"name": "Race",
		"typeSlug": "road",
		"distanceSlugs": "5km;10km",
		"providerSlug": "p1",
		"detailUrl": "https://b.com/y",
	}
	base.update(over)
	return base


# -- plan_supabase_sync --------------------------------------------------


def test_plan_returns_rows_to_insert_when_nothing_exists(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)
	plan = plan_supabase_sync([_row()], set(), data_dir=data_dir)

	assert isinstance(plan, SupabaseSyncPlan)
	assert len(plan.rows_to_insert) == 1
	assert plan.rows_to_insert[0]["detailUrl"] == "https://b.com/y"
	assert "No new rows" not in " ".join(plan.log_lines)


def test_plan_skips_duplicates_and_logs_them(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)
	row = _row()
	existing = {"https://b.com/y"}
	plan = plan_supabase_sync([row], existing, data_dir=data_dir)

	assert plan.rows_to_insert == []
	assert "No new rows; Supabase unchanged." in plan.log_lines
	assert any("duplicate" in m for m in plan.log_lines)


def test_plan_reports_skips_for_invalid_foreign_keys(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)
	bad = _row(typeSlug="made-up")
	plan = plan_supabase_sync([bad], set(), data_dir=data_dir)

	assert plan.rows_to_insert == []
	assert any("skip" in m for m in plan.log_lines)


# -- sync_scraped_rows_to_supabase (injected fake conn) ------------------


class _FakeCursor:
	def __init__(self, existing_urls: list[str]):
		self._existing_urls = existing_urls
		self._last_insert_race = False
		self.executed: list[tuple[str, tuple]] = []
		self._next_race_id = 1

	def execute(self, sql, params=None):
		self.executed.append((sql, params))
		# Mark whether the most recent query was the races INSERT so
		# fetchone() can return a race_id next.
		self._last_insert_race = "INSERT INTO public.races" in sql

	def fetchall(self):
		return [(u,) for u in self._existing_urls]

	def fetchone(self):
		if not self._last_insert_race:
			raise AssertionError("fetchone() called outside an INSERT RETURNING")
		race_id = self._next_race_id
		self._next_race_id += 1
		return (race_id,)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		return False


class _FakeConnection:
	def __init__(self, existing_urls: list[str] | None = None):
		self._cursor = _FakeCursor(existing_urls or [])
		self.committed = False
		self.rolled_back = False
		self.closed = False

	def cursor(self):
		return self._cursor

	def commit(self):
		self.committed = True

	def rollback(self):
		self.rolled_back = True

	def close(self):
		self.closed = True


def test_sync_inserts_new_rows_with_injected_conn(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)
	conn = _FakeConnection(existing_urls=[])

	n, log = sync_scraped_rows_to_supabase([_row()], data_dir=data_dir, conn=conn)

	assert n == 1
	assert conn.committed
	assert not conn.rolled_back
	# Injected connections must not be closed by the sync helper.
	assert not conn.closed
	assert any("Inserted 1" in m for m in log)

	# The race INSERT + the two race_distances INSERTs were issued in order.
	sqls = [sql for sql, _ in conn.cursor().executed]
	assert sum("INSERT INTO public.races" in s for s in sqls) == 1
	assert sum("INSERT INTO public.race_distances" in s for s in sqls) == 2


def test_sync_short_circuits_when_every_row_is_a_duplicate(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)
	conn = _FakeConnection(existing_urls=["https://b.com/y"])

	n, log = sync_scraped_rows_to_supabase([_row()], data_dir=data_dir, conn=conn)

	assert n == 0
	assert not conn.committed, "nothing to commit when no rows were inserted"
	sqls = [sql for sql, _ in conn.cursor().executed]
	assert all("INSERT INTO public.races" not in s for s in sqls)
	assert any("No new rows" in m for m in log)


def test_sync_rolls_back_on_insert_failure(tmp_path: Path):
	data_dir = _reference_csvs(tmp_path)

	class _ExplodingCursor(_FakeCursor):
		def execute(self, sql, params=None):
			super().execute(sql, params)
			if "INSERT INTO public.races" in sql:
				raise RuntimeError("boom")

	class _ExplodingConn(_FakeConnection):
		def __init__(self):
			super().__init__(existing_urls=[])
			self._cursor = _ExplodingCursor(existing_urls=[])

	conn = _ExplodingConn()
	with pytest.raises(RuntimeError, match="boom"):
		sync_scraped_rows_to_supabase([_row()], data_dir=data_dir, conn=conn)

	assert conn.rolled_back
	assert not conn.committed


# -- insert_races_and_distances direct -----------------------------------


def test_insert_noop_on_empty_rows():
	conn = _FakeConnection()
	assert insert_races_and_distances(conn, []) == 0
	assert conn.cursor().executed == []
