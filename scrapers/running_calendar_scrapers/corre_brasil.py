"""Scrape Corre Brasil Wix calendar (repeater list) into race rows."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from running_calendar_scrapers.db_ref import load_distance_slugs_by_km, load_valid_provider_slugs, load_valid_type_slugs
from running_calendar_scrapers.iguana import ScrapedRace, format_races_csv

CALENDAR_URL = "https://www.correbrasil.com.br/calendario-corridas"
USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"

_SITE_HOST = "correbrasil.com.br"

# When the site lists only the state name (no City/UF), map to UF for non-empty `state` (validate-db).
_BR_STATE_NAME_TO_UF: dict[str, str] = {
	"acre": "AC",
	"alagoas": "AL",
	"amapa": "AP",
	"amazonas": "AM",
	"bahia": "BA",
	"ceara": "CE",
	"distrito federal": "DF",
	"espirito santo": "ES",
	"goias": "GO",
	"maranhao": "MA",
	"mato grosso": "MT",
	"mato grosso do sul": "MS",
	"minas gerais": "MG",
	"para": "PA",
	"paraiba": "PB",
	"parana": "PR",
	"pernambuco": "PE",
	"piaui": "PI",
	"rio de janeiro": "RJ",
	"rio grande do norte": "RN",
	"rio grande do sul": "RS",
	"rondonia": "RO",
	"roraima": "RR",
	"santa catarina": "SC",
	"sao paulo": "SP",
	"sergipe": "SE",
	"tocantins": "TO",
}


def _norm_state_lookup_key(s: str) -> str:
	t = unicodedata.normalize("NFKD", s.strip().lower())
	return "".join(ch for ch in t if not unicodedata.combining(ch))


_PT_MONTHS = {
	"janeiro": 1,
	"fevereiro": 2,
	"marco": 3,
	"abril": 4,
	"maio": 5,
	"junho": 6,
	"julho": 7,
	"agosto": 8,
	"setembro": 9,
	"outubro": 10,
	"novembro": 11,
	"dezembro": 12,
}


def _session() -> requests.Session:
	s = requests.Session()
	s.headers.update({"User-Agent": USER_AGENT})
	return s


def _norm_month_token(raw: str) -> str | None:
	s = unicodedata.normalize("NFKD", raw.strip().lower())
	s = "".join(ch for ch in s if not unicodedata.combining(ch))
	if s.endswith("co") and s.startswith("mar"):
		return "marco"
	return s if s in _PT_MONTHS else None


def _month_num(token: str | None) -> int | None:
	if not token:
		return None
	n = _norm_month_token(token)
	return _PT_MONTHS[n] if n else None


def _parse_event_day_month(date_line: str, year: int) -> tuple[int, int] | None:
	"""Return (day, month) for sorting (first day of multi-day ranges)."""
	line = date_line.strip()
	line = re.sub(r"\s+", " ", line)

	m = re.match(
		r"^(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)\s+à\s+(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)$",
		line,
	)
	if m:
		d1, mon_a, d2, mon_b = int(m.group(1)), m.group(2), int(m.group(3)), m.group(4)
		ma = _month_num(mon_a)
		mb = _month_num(mon_b)
		if ma is not None and mb is not None:
			return (d1, ma)

	m = re.match(r"^(\d{1,2})\s+à\s+(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)$", line)
	if m:
		d1 = int(m.group(1))
		mon = _month_num(m.group(3))
		if mon is not None:
			return (d1, mon)

	m = re.match(r"^(\d{1,2})\s+e\s+(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)$", line)
	if m:
		d1 = int(m.group(1))
		mon = _month_num(m.group(3))
		if mon is not None:
			return (d1, mon)

	m = re.match(r"^(\d{1,2})\s+a\s+(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)$", line)
	if m:
		d1 = int(m.group(1))
		mon = _month_num(m.group(3))
		if mon is not None:
			return (d1, mon)

	m = re.match(r"^(\d{1,2})\s+de\s+([A-Za-zÀ-ÿ]+)$", line)
	if m:
		d = int(m.group(1))
		mon = _month_num(m.group(2))
		if mon is not None:
			return (d, mon)

	return None


def _parse_place_line(place_line: str) -> tuple[str, str, str]:
	"""City/UF or region; country fixed to Brasil."""
	raw = place_line.strip()
	if not raw:
		return ("", "", "Brasil")
	if "/" in raw:
		left, right = raw.rsplit("/", 1)
		city = left.strip()
		st = right.strip().upper()
		if len(st) == 2 and st.isalpha():
			return (city, st, "Brasil")
	uf = _BR_STATE_NAME_TO_UF.get(_norm_state_lookup_key(raw))
	if uf:
		return (raw, uf, "Brasil")
	return (raw, "", "Brasil")


def _infer_type_slug(name: str, distances_blob: str) -> str:
	combined = f"{name} {distances_blob}".lower()
	if "cicl" in combined:
		return "adventure"
	if "trail" in combined or "ultra" in combined:
		return "trail"
	return "road"


def _distance_slugs_from_blob(
	blob: str,
	km_to_slug: dict[float, str],
	*,
	name: str,
) -> str:
	"""Extract km-ish tokens from prose; unknown numeric distances are skipped."""
	if not blob.strip():
		return ""

	slug_to_km = {slug: km for km, slug in km_to_slug.items()}
	tokens = re.split(r"[•,;]+|\s+e\s+|\s+/\s+", blob)
	slugs: list[str] = []
	for tok in tokens:
		t = tok.strip()
		if not t:
			continue
		if re.search(r"anos|idade|kids|infant|mi\b|milhas|modalidade", t, re.I):
			continue
		t_clean = t.upper().replace("KM", "").strip().replace(",", ".")
		m = re.match(r"^(\d+(?:\.\d+)?)\s*K?$", t_clean)
		if not m:
			continue
		try:
			km = float(m.group(1))
		except ValueError:
			continue
		if km not in km_to_slug:
			continue
		slugs.append(km_to_slug[km])
	unique: list[str] = []
	for s in slugs:
		if s not in unique:
			unique.append(s)
	unique.sort(key=lambda s: slug_to_km.get(s, 0.0))
	if unique:
		return ";".join(unique)
	nl = name.lower()
	if re.search(r"\bkids?\b", blob, re.I) and "trail" not in nl and "ultra" not in nl:
		return "kids-run"
	return ""


def _pick_detail_url(links: list[str], calendar_url: str) -> str:
	parsed_cal = urlparse(calendar_url)
	cal_host = (parsed_cal.hostname or "").lower().removeprefix("www.")
	cal_path = (parsed_cal.path or "").strip("/")

	def _same_calendar(u: str) -> bool:
		try:
			p = urlparse(u)
		except ValueError:
			return True
		h = (p.hostname or "").lower().removeprefix("www.")
		path = (p.path or "").strip("/")
		return h == cal_host and path == cal_path

	for href in links:
		if not href or href.startswith("#"):
			continue
		try:
			parsed = urlparse(href)
			host = (parsed.hostname or "").lower().removeprefix("www.")
			path = (parsed.path or "").strip("/")
		except ValueError:
			continue
		if host and host != _SITE_HOST:
			return href
		if host == _SITE_HOST and path and not _same_calendar(href):
			return href
	return calendar_url


def _collect_links(item) -> list[str]:
	seen: list[str] = []
	for a in item.select("a[href]"):
		href = (a.get("href") or "").strip()
		if href and href not in seen:
			seen.append(href)
	return seen


def scrape_corre_brasil_calendar_html(
	html: str,
	*,
	year: int,
	calendar_url: str = CALENDAR_URL,
	km_to_slug: dict[float, str] | None = None,
) -> list[ScrapedRace]:
	if km_to_slug is None:
		km_to_slug = load_distance_slugs_by_km()
	soup = BeautifulSoup(html, "html.parser")
	items = soup.select("div.wixui-repeater__item")
	out: list[ScrapedRace] = []
	for item in items:
		ps = [p.get_text(" ", strip=True) for p in item.select("p.font_8")]
		ps = [t for t in ps if t and t.strip() not in ("\u200b",)]
		date_line = ps[0] if len(ps) >= 1 else ""
		place_line = ps[1] if len(ps) >= 2 else ""
		h4 = item.select_one("h4")
		name = h4.get_text(" ", strip=True) if h4 else ""
		if not name:
			continue
		dm = _parse_event_day_month(date_line, year)
		if not dm:
			continue
		day, month = dm
		try:
			dt = datetime(year, month, day, 12, 0)
		except ValueError:
			continue
		sort_key = dt.strftime("%Y-%m-%dT%H:%M")
		city, state, country = _parse_place_line(place_line)
		dist_blob = ""
		if len(ps) >= 3:
			dist_blob = ps[2]
		type_slug = _infer_type_slug(name, dist_blob)
		distance_slugs = _distance_slugs_from_blob(dist_blob, km_to_slug, name=name)
		detail_url = _pick_detail_url(_collect_links(item), calendar_url)
		out.append(
			ScrapedRace(
				sort_key=sort_key,
				city=city,
				state=state,
				country=country,
				name=name,
				type_slug=type_slug,
				distance_slugs=distance_slugs,
				provider_slug="corre-brasil",
				detail_url=detail_url,
			)
		)
	return sorted(out, key=lambda x: x.sort_key)


def fetch_corre_brasil_calendar_html(*, session: requests.Session | None = None) -> str:
	session = session or _session()
	r = session.get(CALENDAR_URL, timeout=60)
	r.raise_for_status()
	return r.text


def scrape_corre_brasil_calendar(year: int, *, session: requests.Session | None = None) -> list[ScrapedRace]:
	session = session or _session()
	valid_providers = load_valid_provider_slugs()
	valid_types = load_valid_type_slugs()
	if "corre-brasil" not in valid_providers:
		raise RuntimeError("public.providers must include corre-brasil")
	for need in ("road", "trail", "adventure"):
		if need not in valid_types:
			raise RuntimeError(f"public.types must include {need}")
	html = fetch_corre_brasil_calendar_html(session=session)
	return scrape_corre_brasil_calendar_html(html, year=year)


def run(argv: list[str] | None = None) -> str:
	"""CLI entry: print races CSV. Supports ``--year`` (default 2026)."""
	import argparse

	p = argparse.ArgumentParser(prog="corre_brasil", add_help=False)
	p.add_argument("--year", type=int, default=2026)
	args = p.parse_args(argv or [])
	return format_races_csv(scrape_corre_brasil_calendar(args.year))
