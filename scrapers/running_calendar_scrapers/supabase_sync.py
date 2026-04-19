"""Upsert scraped races into Supabase (PostgreSQL) ``public.races`` and ``race_distances``.

The module is split into three layers that change for independent reasons:

1. **Pure planning** (:func:`plan_supabase_sync`). Given scraped rows and the
   set of existing ``detail_url`` keys, decide which rows to insert, which
   to skip, and return log lines. No DB, no network — fully unit-testable.
2. **DB adapter helpers** (:func:`fetch_existing_detail_url_keys`,
   :func:`insert_races_and_distances`). Wrap the SQL the planner can't do
   alone.
3. **Composition root** (:func:`sync_scraped_rows_to_supabase`). Opens the
   connection, applies the plan, commits. Accepts an injectable ``conn``
   so callers (and tests) can share a transaction or supply a fake.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §1.4.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from running_calendar_scrapers.db_config import database_url_from_env
from running_calendar_scrapers.merge_csv import normalize_detail_url_for_key, partition_scraped_races
from running_calendar_scrapers.race_row import RACE_DB_INSERT_COLUMNS, RACE_ROW_FIELDS

# Mapping from CSV key -> race-row dict lookup, used by :func:`insert_races_and_distances`
# to build the INSERT value tuple in the order declared in ``RACE_ROW_FIELDS``.
_INSERT_CSV_KEYS: tuple[str, ...] = tuple(
	f.csv_key for f in RACE_ROW_FIELDS if f.db_column is not None
)
_INSERT_SQL = (
	"INSERT INTO public.races ("
	+ ", ".join(RACE_DB_INSERT_COLUMNS)
	+ ") VALUES ("
	+ ", ".join(["%s"] * len(RACE_DB_INSERT_COLUMNS))
	+ ") RETURNING id"
)


@dataclass(frozen=True)
class SupabaseSyncPlan:
	"""Result of :func:`plan_supabase_sync`.

	``rows_to_insert`` is the normalised, deduplicated set of scraped rows
	ready for :func:`insert_races_and_distances`. ``log_lines`` contains
	human-readable skip/duplicate messages that the composition root writes
	to stdout, plus the final "Inserted N" or "No new rows" summary.
	"""

	rows_to_insert: list[dict[str, str]]
	log_lines: list[str]


def plan_supabase_sync(
	rows: list[dict[str, str]],
	existing_detail_url_keys: set[str],
	*,
	data_dir: Path | None = None,
) -> SupabaseSyncPlan:
	"""Pure planner: normalise scraped rows and decide which to insert.

	FK validation uses ``public.distances``, ``public.types``, and
	``public.providers`` (or pass ``data_dir`` with the same three ``*.csv``
	files for offline tests).

	Returns a :class:`SupabaseSyncPlan` with duplicate/skip messages already
	in ``log_lines``. A final "Inserted N" message is appended by the
	composition root once the rows have actually been written.
	"""
	to_add, dups, skips = partition_scraped_races(
		rows,
		existing_detail_url_keys,
		data_dir=data_dir,
	)
	log_lines: list[str] = []
	log_lines.extend(dups)
	log_lines.extend(skips)
	if not to_add:
		log_lines.append("No new rows; Supabase unchanged.")
	return SupabaseSyncPlan(rows_to_insert=to_add, log_lines=log_lines)


def fetch_existing_detail_url_keys(conn: Any) -> set[str]:
	"""Normalized keys for every ``public.races.detail_url`` (for deduplication)."""
	keys: set[str] = set()
	with conn.cursor() as cur:
		cur.execute("SELECT detail_url FROM public.races")
		for row in cur.fetchall():
			url = row[0]
			if url:
				keys.add(normalize_detail_url_for_key(str(url)))
	return keys


def insert_races_and_distances(
	conn: Any,
	rows: list[dict[str, str]],
) -> int:
	"""Insert each race row and its ``race_distances`` links in one transaction.

	Returns the number of races inserted.
	"""
	if not rows:
		return 0

	inserted = 0
	with conn.cursor() as cur:
		for row in rows:
			cur.execute(_INSERT_SQL, tuple(row[k] for k in _INSERT_CSV_KEYS))
			race_id = cur.fetchone()[0]
			slugs = [s.strip() for s in (row.get("distanceSlugs") or "").split(";") if s.strip()]
			for ds in slugs:
				cur.execute(
					"""
					INSERT INTO public.race_distances (race_id, distance_slug)
					VALUES (%s, %s)
					ON CONFLICT DO NOTHING
					""",
					(race_id, ds),
				)
			inserted += 1
	return inserted


def sync_scraped_rows_to_supabase(
	rows: list[dict[str, str]],
	*,
	data_dir: Path | None = None,
	conn: Any | None = None,
) -> tuple[int, list[str]]:
	"""Compose the pure plan + DB adapters into a single upsert.

	When ``conn`` is ``None``, a connection is opened from the env-var URI
	and closed when done. Passing ``conn`` lets callers share an existing
	transaction (or inject a fake in tests).

	Returns ``(number_of_races_inserted, log_lines)``.
	"""
	own_conn = conn is None
	connection = conn or _open_connection()
	try:
		existing = fetch_existing_detail_url_keys(connection)
		plan = plan_supabase_sync(rows, existing, data_dir=data_dir)
		if not plan.rows_to_insert:
			return 0, list(plan.log_lines)
		try:
			n = insert_races_and_distances(connection, plan.rows_to_insert)
			connection.commit()
		except Exception:
			connection.rollback()
			raise
		log = list(plan.log_lines)
		log.append(f"Inserted {n} race(s) into Supabase (public.races + race_distances).")
		return n, log
	finally:
		if own_conn:
			connection.close()


def _open_connection() -> Any:
	import psycopg2

	return psycopg2.connect(database_url_from_env())


__all__ = [
	"SupabaseSyncPlan",
	"fetch_existing_detail_url_keys",
	"insert_races_and_distances",
	"plan_supabase_sync",
	"sync_scraped_rows_to_supabase",
]
