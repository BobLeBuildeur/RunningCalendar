"""Upsert scraped races into Supabase (PostgreSQL) ``public.races`` and ``race_distances``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from running_calendar_scrapers.db_config import database_url_from_env
from running_calendar_scrapers.merge_csv import normalize_detail_url_for_key, partition_scraped_races


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
	"""
	Insert each race row and its ``race_distances`` links in one transaction.

	Returns the number of races inserted.
	"""
	if not rows:
		return 0

	inserted = 0
	with conn.cursor() as cur:
		for row in rows:
			cur.execute(
				"""
				INSERT INTO public.races (
					sort_key, city, state, country, name,
					type_slug, provider_slug, detail_url
				) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
				RETURNING id
				""",
				(
					row["sortKey"],
					row["city"],
					row["state"],
					row["country"],
					row["name"],
					row["typeSlug"],
					row["providerSlug"],
					row["detailUrl"],
				),
			)
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
) -> tuple[int, list[str]]:
	"""
	Load existing ``detail_url`` keys from Supabase, insert only new normalized ``rows``.

	FK validation uses ``public.distances``, ``public.types``, and ``public.providers`` (or
	pass ``data_dir`` with the same three ``*.csv`` files for offline tests).

	Returns (number_of_races_inserted, log_lines).
	"""
	import psycopg2

	log: list[str] = []
	url = database_url_from_env()
	conn = psycopg2.connect(url)
	try:
		existing = fetch_existing_detail_url_keys(conn)
		to_add, dups, skips = partition_scraped_races(rows, existing, data_dir=data_dir)
		for msg in dups:
			log.append(msg)
		for msg in skips:
			log.append(msg)
		if not to_add:
			log.append("No new rows; Supabase unchanged.")
			return 0, log
		try:
			n = insert_races_and_distances(conn, to_add)
			conn.commit()
		except Exception:
			conn.rollback()
			raise
		log.append(f"Inserted {n} race(s) into Supabase (public.races + race_distances).")
		return n, log
	finally:
		conn.close()
