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


def fixture_km_to_slug_iguana_html_tests() -> dict[float, str]:
	"""Minimal km→slug map for offline ``iguana`` HTML fixtures (no database)."""
	return {
		7.0: "7km",
		14.0: "14km",
		21.1: "21-1km",
		28.0: "28km",
		0.0: "kids-run",
	}


def fixture_km_to_slug_corre_brasil_repeater() -> dict[float, str]:
	"""Km→slug map matching ``corre_brasil_repeater.html`` snapshot expectations (no database)."""
	return {
		3.0: "3km",
		5.0: "5km",
		6.0: "6km",
		10.0: "10km",
		12.0: "12km",
		15.0: "15km",
		21.0: "21km",
		25.0: "25km",
		37.0: "37km",
		42.0: "42km",
		55.0: "55km",
		67.0: "67km",
		104.0: "104km",
		0.0: "kids-run",
	}


def load_races_for_provider(provider_slug: str) -> list[dict[str, str]]:
	"""Race rows for a provider (same keys as scraper CSV), ordered by ``sort_key``."""
	c = _connect()
	try:
		out: list[dict[str, str]] = []
		with c.cursor() as cur:
			cur.execute(
				"""
				SELECT
					r.sort_key,
					r.city,
					r.state,
					r.country,
					r.name,
					r.type_slug,
					r.provider_slug,
					r.detail_url,
					CALESCE(
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
				""",
				(provider_slug,),
			)
			for row in cur.fetchall():
				sort_key, city, state, country, name, type_slug, prov, detail_url, dist_cell = row
				out.append(
					{
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
				)
		return out
	finally:
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
