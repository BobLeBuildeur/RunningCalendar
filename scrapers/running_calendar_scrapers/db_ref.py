"""Load reference slugs and distance ordering from PostgreSQL (Supabase)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from running_calendar_scrapers.db_config import database_url_from_env


def repo_root() -> Path:
	return Path(__file__).resolve().parents[2]


def _connect():
	import psycopg2

	return psycopg2.connect(database_url_from_env())


def load_slug_to_km(conn: Any | None = None) -> dict[str, float]:
	"""slug -> km for sorting distance lists (DB ``km`` is integer tenths of a km)."""
	own = conn is None
	c = conn or _connect()
	try:
		out: dict[str, float] = {}
		with c.cursor() as cur:
			cur.execute("SELECT slug, km FROM public.distances")
			for slug, km in cur.fetchall():
				out[str(slug).strip()] = int(km) / 10.0
		return out
	finally:
		if own:
			c.close()


def load_distance_slugs_by_km(conn: Any | None = None) -> dict[float, str]:
	"""Map distance in km (float) to slug. DB stores integer tenths of a km (e.g. 50 → 5.0)."""
	own = conn is None
	c = conn or _connect()
	try:
		by_km: dict[float, str] = {}
		with c.cursor() as cur:
			cur.execute("SELECT slug, km FROM public.distances ORDER BY slug")
			for slug, km in cur.fetchall():
				tenths = int(km)
				km_f = tenths / 10.0
				by_km[km_f] = str(slug).strip()
		return by_km
	finally:
		if own:
			c.close()


_LOAD_RACES_FOR_PROVIDER_SQL = """
SELECT
	r.sort_key,
	r.city,
	r.state,
	r.country,
	r.name,
	r.type_slug,
	r.provider_slug,
	r.detail_url,
	COALESCE(
		(
			SELECT string_agg(s.slug, ';' ORDER BY s.km)
			FROM (
				SELECT rd.distance_slug AS slug, d.km
				FROM public.race_distances rd
				INNER JOIN public.distances d ON d.slug = rd.distance_slug
				WHERE rd.race_id = r.id
			) s
		),
		''
	) AS distance_slugs
FROM public.races r
WHERE r.provider_slug = %s
ORDER BY r.sort_key
"""


def _row_to_race_dict(row: tuple[Any, ...]) -> dict[str, str]:
	"""Coerce a ``load_races_for_provider`` row into the flat race-row contract."""
	sort_key, city, state, country, name, type_slug, prov, detail_url, dist_cell = row
	return {
		"sortKey": str(sort_key).strip(),
		"city": str(city).strip(),
		"state": str(state).strip(),
		"country": str(country).strip(),
		"name": str(name).strip(),
		"typeSlug": str(type_slug).strip() or "road",
		"distanceSlugs": str(dist_cell).strip() if dist_cell else "",
		"providerSlug": str(prov).strip(),
		"detailUrl": str(detail_url).strip(),
	}


def load_races_for_provider(
	provider_slug: str,
	*,
	conn: Any | None = None,
) -> list[dict[str, str]]:
	"""Race rows for a provider (same keys as scraper CSV), ordered by ``sort_key``.

	``conn`` is injectable so the query can be exercised against a fake
	DB-API connection in unit tests (see ``tests/test_db_ref_load_races.py``).
	"""
	own = conn is None
	c = conn or _connect()
	try:
		with c.cursor() as cur:
			cur.execute(_LOAD_RACES_FOR_PROVIDER_SQL, (provider_slug,))
			return [_row_to_race_dict(row) for row in cur.fetchall()]
	finally:
		if own:
			c.close()


def load_valid_type_slugs(conn: Any | None = None) -> set[str]:
	own = conn is None
	c = conn or _connect()
	try:
		with c.cursor() as cur:
			cur.execute("SELECT slug FROM public.types")
			return {str(r[0]).strip() for r in cur.fetchall() if r[0]}
	finally:
		if own:
			c.close()


def load_valid_provider_slugs(conn: Any | None = None) -> set[str]:
	own = conn is None
	c = conn or _connect()
	try:
		with c.cursor() as cur:
			cur.execute("SELECT slug FROM public.providers")
			return {str(r[0]).strip() for r in cur.fetchall() if r[0]}
	finally:
		if own:
			c.close()
