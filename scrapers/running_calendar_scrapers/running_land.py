"""Scrape Running Land Magento GraphQL (Calendário category) into race rows."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests

from running_calendar_scrapers.db_ref import load_distance_slugs_by_km, load_valid_provider_slugs, load_valid_type_slugs
from running_calendar_scrapers.iguana import ScrapedRace, format_races_csv

GRAPHQL_URL = "https://www.runningland.com.br/graphql"
CALENDAR_CATEGORY_ID = "3"
EVENT_LIST_PATH = "/eventos"
# Browser-like UA: the site's edge/WAF rejects several non-browser tokens on GraphQL.
USER_AGENT = (
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/120.0.0.0 Safari/537.36"
)
REFERER = "https://www.runningland.com.br/eventos"

_PRODUCTS_PAGE_QUERY = (
	"query RunningLandCalendarPage($pageSize: Int!, $currentPage: Int!) { "
	f'products(filter: {{ category_id: {{ eq: "{CALENDAR_CATEGORY_ID}" }} }}, '
	"pageSize: $pageSize, currentPage: $currentPage) { total_count items { "
	"name sku url_key event_date event_modality event_city event_region event_product "
	"} } }"
)

_METADATA_QUERIES: dict[str, str] = {
	"event_city": (
		'query { customAttributeMetadata(attributes: '
		'[{ attribute_code: "event_city", entity_type: "catalog_product" }]) '
		"{ items { attribute_options { value label } } } }"
	),
	"event_region": (
		'query { customAttributeMetadata(attributes: '
		'[{ attribute_code: "event_region", entity_type: "catalog_product" }]) '
		"{ items { attribute_options { value label } } } }"
	),
	"event_modality": (
		'query { customAttributeMetadata(attributes: '
		'[{ attribute_code: "event_modality", entity_type: "catalog_product" }]) '
		"{ items { attribute_options { value label } } } }"
	),
}


def _session() -> requests.Session:
	s = requests.Session()
	s.headers.update(
		{
			"User-Agent": USER_AGENT,
			"Accept": "application/json",
			"Referer": REFERER,
			"Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
		}
	)
	return s


def _graphql_get(session: requests.Session, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
	"""Magento GraphQL via GET (site WAF blocks typical JSON POST from scripts)."""
	params: dict[str, str] = {"query": query}
	if variables is not None:
		params["variables"] = json.dumps(variables, separators=(",", ":"))
	url = f"{GRAPHQL_URL}?{urlencode(params)}"
	r = session.get(url, timeout=90)
	r.raise_for_status()
	payload = r.json()
	if payload.get("errors"):
		msgs = "; ".join(str(e.get("message", e)) for e in payload["errors"])
		raise RuntimeError(f"GraphQL errors: {msgs}")
	data = payload.get("data")
	if data is None:
		raise RuntimeError("GraphQL response missing data")
	return data


def _option_id_to_label_map(items: list[dict[str, Any]] | None) -> dict[str, str]:
	out: dict[str, str] = {}
	if not items:
		return out
	first = items[0]
	for opt in first.get("attribute_options") or []:
		val = (opt.get("value") or "").strip()
		if not val:
			continue
		label = (opt.get("label") or "").strip()
		if val:
			out[val] = label
	return out


def load_running_land_option_maps(session: requests.Session) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
	city_data = _graphql_get(session, _METADATA_QUERIES["event_city"])
	region_data = _graphql_get(session, _METADATA_QUERIES["event_region"])
	mod_data = _graphql_get(session, _METADATA_QUERIES["event_modality"])
	city_items = city_data.get("customAttributeMetadata") and city_data["customAttributeMetadata"].get("items")
	region_items = region_data.get("customAttributeMetadata") and region_data["customAttributeMetadata"].get("items")
	mod_items = mod_data.get("customAttributeMetadata") and mod_data["customAttributeMetadata"].get("items")
	return (
		_option_id_to_label_map(list(city_items or [])),
		_option_id_to_label_map(list(region_items or [])),
		_option_id_to_label_map(list(mod_items or [])),
	)


def _parse_event_datetime(raw: str) -> datetime | None:
	t = (raw or "").strip()
	if not t:
		return None
	for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
		try:
			return datetime.strptime(t, fmt)
		except ValueError:
			continue
	return None


def _infer_type_slug(name: str, modality_labels: list[str]) -> str:
	combined = f"{name} {' '.join(modality_labels)}".lower()
	if "cicl" in combined:
		return "adventure"
	if "trail" in combined or "ultra" in combined:
		return "trail"
	return "road"


def _label_to_km(label: str) -> float | None:
	s = label.strip()
	if not s:
		return None
	if re.search(r"anos|idade|kids|infant|caminhada|obst[aá]culo|bike|skate|triathlon|travessia|mandala|teste|escada|metros?\b|mi\b|milhas", s, re.I):
		return None
	m = re.match(r"^(\d+(?:[.,]\d+)?)\s*K$", s, re.I)
	if m:
		return float(m.group(1).replace(",", "."))
	m = re.match(r"^(\d+(?:[.,]\d+)?)\s*KM$", s, re.I)
	if m:
		return float(m.group(1).replace(",", "."))
	m = re.match(r"^(\d+)K$", s, re.I)
	if m:
		return float(m.group(1))
	m = re.match(r"^(\d+(?:[.,]\d+)?)K$", s, re.I)
	if m:
		return float(m.group(1).replace(",", "."))
	return None


def _distance_slugs_from_modality_ids(
	blob: str,
	modality_id_to_label: dict[str, str],
	km_to_slug: dict[float, str],
	*,
	name: str,
) -> str:
	if not (blob or "").strip():
		return ""

	slug_to_km = {slug: km for km, slug in km_to_slug.items()}
	raw_ids = [x.strip() for x in blob.split(",") if x.strip()]
	slugs: list[str] = []
	modality_labels: list[str] = []
	for iid in raw_ids:
		label = modality_id_to_label.get(iid, "")
		if label:
			modality_labels.append(label)
		km = _label_to_km(label) if label else None
		if km is None or km not in km_to_slug:
			continue
		slugs.append(km_to_slug[km])

	unique: list[str] = []
	for s in slugs:
		if s not in unique:
			unique.append(s)
	unique.sort(key=lambda s: slug_to_km.get(s, 0.0))
	if unique:
		return ";".join(unique)
	return ""


def _city_state_country(
	city_id: int | None,
	region_id: int | None,
	city_map: dict[str, str],
	region_map: dict[str, str],
) -> tuple[str, str, str]:
	city = ""
	if city_id is not None:
		city = (city_map.get(str(city_id)) or "").strip()

	state = ""
	if region_id is not None:
		region_label = (region_map.get(str(region_id)) or "").strip()
		if len(region_label) == 2 and region_label.isalpha():
			state = region_label.upper()
		else:
			tok = region_label.split()[-1] if region_label else ""
			if len(tok) == 2 and tok.isalpha():
				state = tok.upper()
			elif len(region_label) <= 3:
				state = region_label.upper()

	return (city, state, "Brasil")


def _detail_url(url_key: str) -> str:
	key = (url_key or "").strip()
	return f"https://www.runningland.com.br{EVENT_LIST_PATH}/{key}"


def fetch_running_land_product_pages(
	session: requests.Session,
	*,
	page_size: int = 100,
	max_pages: int = 50,
) -> list[dict[str, Any]]:
	all_items: list[dict[str, Any]] = []
	page = 1
	while page <= max_pages:
		data = _graphql_get(
			session,
			_PRODUCTS_PAGE_QUERY,
			{"pageSize": page_size, "currentPage": page},
		)
		block = data.get("products") or {}
		items = block.get("items") or []
		if not items:
			break
		all_items.extend(items)
		if len(items) < page_size:
			break
		page += 1
	return all_items


def scrape_running_land_calendar(
	year: int,
	*,
	session: requests.Session | None = None,
	city_map: dict[str, str] | None = None,
	region_map: dict[str, str] | None = None,
	modality_map: dict[str, str] | None = None,
	items: list[dict[str, Any]] | None = None,
) -> list[ScrapedRace]:
	session = session or _session()
	km_to_slug = load_distance_slugs_by_km()
	valid_providers = load_valid_provider_slugs()
	valid_types = load_valid_type_slugs()
	if "running-land" not in valid_providers:
		raise RuntimeError("public.providers must include running-land")
	for need in ("road", "trail", "adventure"):
		if need not in valid_types:
			raise RuntimeError(f"public.types must include {need}")

	if city_map is None or region_map is None or modality_map is None:
		city_map, region_map, modality_map = load_running_land_option_maps(session)

	raw_items = items if items is not None else fetch_running_land_product_pages(session)
	out: list[ScrapedRace] = []
	year_prefix = f"{year}-"

	for p in raw_items:
		if p.get("event_product") != 1:
			continue
		name = (p.get("name") or "").strip()
		url_key = (p.get("url_key") or "").strip()
		if not name or not url_key:
			continue
		ed = p.get("event_date")
		if not ed or not str(ed).strip().startswith(year_prefix):
			continue
		dt = _parse_event_datetime(str(ed))
		if dt is None:
			continue

		ev_city = p.get("event_city")
		ev_region = p.get("event_region")
		city_id = int(ev_city) if ev_city is not None and str(ev_city).strip().isdigit() else None
		region_id = int(ev_region) if ev_region is not None and str(ev_region).strip().isdigit() else None
		city, state, country = _city_state_country(city_id, region_id, city_map, region_map)
		if not city.strip() or not state.strip():
			continue

		mod_blob = str(p.get("event_modality") or "")
		raw_ids = [x.strip() for x in mod_blob.split(",") if x.strip()]
		mod_labels = [modality_map.get(i, "") for i in raw_ids]
		type_slug = _infer_type_slug(name, [m for m in mod_labels if m])
		distance_slugs = _distance_slugs_from_modality_ids(mod_blob, modality_map, km_to_slug, name=name)

		sort_key = dt.strftime("%Y-%m-%dT%H:%M")
		out.append(
			ScrapedRace(
				sort_key=sort_key,
				city=city,
				state=state,
				country=country,
				name=name,
				type_slug=type_slug,
				distance_slugs=distance_slugs,
				provider_slug="running-land",
				detail_url=_detail_url(url_key),
			)
		)

	return sorted(out, key=lambda x: x.sort_key)


def run(argv: list[str] | None = None) -> str:
	"""CLI entry: print races CSV. Supports ``--year`` (default 2026)."""
	import argparse

	p = argparse.ArgumentParser(prog="running_land", add_help=False)
	p.add_argument("--year", type=int, default=2026)
	args = p.parse_args(argv or [])
	return format_races_csv(scrape_running_land_calendar(args.year))
