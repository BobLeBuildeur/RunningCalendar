"""Scrape XKR Sports WordPress homepage (event tiles + event pages) into race rows.

XKR Sports (``https://xkrsports.com.br``) organizes trail running events (KTR
Series, Desafio 28 Praias, Ultra KTR Canastra, Festival KMF, Revezamento KTR).
All events are of type ``trail`` per the provider's catalog.

Approach
--------

1. Fetch the XKR homepage and extract one tile per event button
   (``a.elementor-button-link`` that points to a ``xkrsports.com.br/<slug>/``
   detail page). Each tile contributes the event date and name.
2. Deduplicate by detail URL + first-day date — the homepage renders the same
   tile in multiple carousels.
3. For each unique event, fetch the event page and extract the list of
   distances from the distance headings (``<h2>7K</h2>``, ``<h2>80K</h2>`` etc.)
   using ``BeautifulSoup``.
4. If the event page yields **no usable distances** (e.g. future events whose
   page is still ``Em breve``), fall back to the AI-assisted scraper which
   renders the page and asks OpenAI for a structured row — this guards against
   the frequent JS/layout churn of WordPress/Elementor pages.
5. City/state are inferred from a small static lookup keyed on the event URL
   slug (KTR Campos → Campos do Jordão/SP, etc.). The AI fallback populates
   them directly when the static lookup is missing.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from running_calendar_scrapers.db_ref import (
	load_distance_slugs_by_km,
	load_valid_provider_slugs,
	load_valid_type_slugs,
)
from running_calendar_scrapers.iguana import ScrapedRace, format_races_csv

HOME_URL = "https://xkrsports.com.br/"
SITE_HOST = "xkrsports.com.br"
PROVIDER_SLUG = "xkr-sports"
USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"

_PT_MONTHS_FULL = {
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

# URL slug (path segment) -> (city, state). Populated from the event pages'
# ``Local:`` lines; entries outside this map default to "" and are filled by
# the AI fallback when it runs.
_EVENT_LOCATION: dict[str, tuple[str, str]] = {
	"ktrcampos": ("Campos do Jordão", "SP"),
	"ktr-ilhabela": ("Ilhabela", "SP"),
	"ktrcanastra": ("São Roque de Minas", "MG"),
	"28pcostanorte": ("Ubatuba", "SP"),
	"desafio28praias": ("Ubatuba", "SP"),
	"festivalkmf": ("Ilhabela", "SP"),
	"ktr-revezamento-ilhabela": ("Ilhabela", "SP"),
}


@dataclass(frozen=True)
class HomeEvent:
	"""Homepage tile summary: detail URL, event name, and first-day date."""

	detail_url: str
	name: str
	date: datetime


def _session() -> requests.Session:
	s = requests.Session()
	s.headers.update(
		{
			"User-Agent": USER_AGENT,
			"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
		}
	)
	return s


def _norm_month_token(raw: str) -> str | None:
	s = unicodedata.normalize("NFKD", raw.strip().lower())
	s = "".join(ch for ch in s if not unicodedata.combining(ch))
	if s in _PT_MONTHS_FULL:
		return s
	return None


def _month_num(token: str) -> int | None:
	k = _norm_month_token(token)
	return _PT_MONTHS_FULL[k] if k else None


def _parse_home_date(raw: str) -> datetime | None:
	"""Parse tile date lines like ``10 E 11 DE ABRIL DE 2026`` or ``5 DE DEZEMBRO DE 2026``.

	Returns the **first day** of multi-day ranges at 12:00 local time. Single-day
	events also get a 12:00 start (the homepage does not advertise start times).
	"""
	line = re.sub(r"\s+", " ", raw.strip())
	# Range: "10 E 11 DE ABRIL DE 2026", "29,30 E 31 DE AGOSTO DE 2025",
	# "21,22 E 23 DE MAIO DE 2026", "29 E 30 DE AGOSTO DE 2025"
	m = re.match(
		r"^(\d{1,2})(?:\s*,\s*\d{1,2})*(?:\s*(?:E|e)\s*\d{1,2})?\s+DE\s+([A-Za-zÀ-ÿ]+)\s+DE\s+(\d{4})$",
		line,
		re.IGNORECASE,
	)
	if m:
		day = int(m.group(1))
		mon = _month_num(m.group(2))
		year = int(m.group(3))
		if mon is not None:
			try:
				return datetime(year, mon, day, 12, 0)
			except ValueError:
				return None
	# "5 DE DEZEMBRO DE 2026"
	m = re.match(
		r"^(\d{1,2})\s+DE\s+([A-Za-zÀ-ÿ]+)\s+DE\s+(\d{4})$",
		line,
		re.IGNORECASE,
	)
	if m:
		day = int(m.group(1))
		mon = _month_num(m.group(2))
		year = int(m.group(3))
		if mon is not None:
			try:
				return datetime(year, mon, day, 12, 0)
			except ValueError:
				return None
	return None


def _url_slug(detail_url: str) -> str:
	try:
		p = urlparse(detail_url)
	except ValueError:
		return ""
	host = (p.hostname or "").lower().removeprefix("www.")
	if host != SITE_HOST:
		return ""
	return (p.path or "").strip("/").split("/", 1)[0]


def _extract_tile_name(text: str) -> str | None:
	"""Pull a human-readable event name from a tile's collapsed text."""
	t = re.sub(r"\s+", " ", text).strip()
	# Try known prefixes in priority order (longest-match first to avoid e.g.
	# "KTR" being selected inside "ULTRA KTR CANASTRA").
	patterns = [
		r"\bULTRA\s+KTR\s+CANASTRA\b",
		r"\bDESAFIO\s+28\s+PRAIAS(?:\s+COSTA\s+NORTE|\s+COSTA\s+CENTRAL|\s+LUA)?\b",
		r"\bFESTIVAL\s+KMF(?:\s*ILHABELA)?\b",
		r"\bREVEZAMENTO\s+KTR(?:\s+ILHABELA)?\b",
		r"\bKTR\s+CAMPOS(?:\s+DO\s+JORD[AÃ]O)?\b",
		r"\bKTR\s+ILHABELA\b",
	]
	for pat in patterns:
		m = re.search(pat, t, re.IGNORECASE)
		if m:
			return _titlecase_event_name(m.group(0))
	return None


_SMALL_PT_WORDS = {"do", "de", "da", "dos", "das", "e"}


def _titlecase_event_name(raw: str) -> str:
	"""Title-case an event name while keeping Portuguese connectives lowercase and acronyms upper."""
	parts: list[str] = []
	tokens = re.split(r"\s+", raw.strip())
	for i, tok in enumerate(tokens):
		lo = tok.lower()
		# Known acronyms stay uppercase.
		if lo in {"ktr", "kmf"}:
			parts.append(lo.upper())
		elif lo in {"ultra", "festival", "revezamento", "desafio", "praias", "costa", "norte", "central", "lua", "campos", "jordao", "jord\u00e3o", "ilhabela", "canastra"}:
			parts.append(lo.capitalize())
			if lo in {"jordao", "jord\u00e3o"}:
				# Preserve diacritic when user typed it.
				parts[-1] = tok.capitalize()
		elif lo in _SMALL_PT_WORDS and i != 0:
			parts.append(lo)
		else:
			parts.append(tok.capitalize())
	# "28" stays "28"
	return " ".join(parts)


def parse_home_events(html: str) -> list[HomeEvent]:
	"""Extract unique (url, name, first-day date) tuples from the XKR homepage."""
	soup = BeautifulSoup(html, "html.parser")
	out: list[HomeEvent] = []
	seen: set[tuple[str, str]] = set()

	for a in soup.select("a.elementor-button-link"):
		href = (a.get("href") or "").strip()
		if not href or href == "#":
			continue
		try:
			parsed = urlparse(href)
		except ValueError:
			continue
		host = (parsed.hostname or "").lower().removeprefix("www.")
		if host != SITE_HOST:
			continue
		path = (parsed.path or "").strip("/")
		if not path or "/" in path:
			continue

		# Walk up until we find a container that holds the date + name.
		node: Any = a
		date_str = None
		tile_text = ""
		for _ in range(20):
			node = node.parent
			if node is None:
				break
			text = node.get_text(" ", strip=True)
			m = re.search(
				r"\d{1,2}(?:\s*[,E]\s*\d{1,2})*\s+DE\s+[A-Za-zÀ-ÿ]+\s+DE\s+\d{4}",
				text,
				re.IGNORECASE,
			)
			if m:
				date_str = m.group(0)
				tile_text = text
				break
		if not date_str:
			continue
		dt = _parse_home_date(date_str)
		if dt is None:
			continue
		name = _extract_tile_name(tile_text)
		if not name:
			continue
		detail_url = f"https://{SITE_HOST}/{path}/"
		key = (detail_url, dt.strftime("%Y-%m-%d"))
		if key in seen:
			continue
		seen.add(key)
		out.append(HomeEvent(detail_url=detail_url, name=name, date=dt))
	return sorted(out, key=lambda e: (e.date, e.detail_url))


# Matches headings like "7K", "80K", "100K Solo", "50K Solo ou Dupla",
# "42K Solo". Requires the heading to start with an integer + 'K' and
# contain no other digits afterwards to avoid matching prose like "42k
# confirme seus dados".
_KM_HEAD_RE = re.compile(
	r"^(\d{1,3})\s*K(?:\s+[A-ZÀ-Ÿ ]{1,40})?$",
	re.IGNORECASE,
)


def _distance_kms_from_event_html(html: str) -> list[int]:
	"""Extract distance KM integers from an event page's distance headings.

	XKR event pages usually use ``<h2>7K</h2>`` / ``<h2>80K</h2>`` blocks inside
	the ``INFORMAÇÕES DOS PERCURSOS`` section. Some pages (Ultra KTR Canastra,
	Desafio 28 Praias Costa Norte) place the distances inside ``<strong>`` tags
	or pair them with "SOLO" / "DUPLA" labels — those are still handled here.
	"""
	soup = BeautifulSoup(html, "html.parser")
	kms: list[int] = []
	for tag in soup.select("h1, h2, h3, h4, h5, h6, strong"):
		t = tag.get_text(" ", strip=True).upper()
		m = _KM_HEAD_RE.match(t)
		if m:
			km = int(m.group(1))
			if 0 < km < 300 and km not in kms:
				kms.append(km)
	return sorted(kms)


def _name_from_event_html(html: str) -> str:
	"""Pull the event name from the page's ``<title>``, stripping the brand suffix."""
	soup = BeautifulSoup(html, "html.parser")
	t = (soup.title.string or "") if soup.title else ""
	t = re.sub(r"\s+", " ", t or "").strip()
	if not t:
		return ""
	# Strip the " – XKR Sports" / " - XKR Sports" tail.
	t = re.sub(r"\s*[\u2013\u2014\-]\s*XKR\s+Sports\s*$", "", t, flags=re.IGNORECASE)
	# Normalise inner em-dashes/en-dashes to a single dash for readability.
	t = re.sub(r"\s*[\u2013\u2014]\s*", " - ", t)
	return t.strip()


def _km_list_to_slugs(kms: list[int], km_to_slug: dict[float, str]) -> str:
	pairs: list[tuple[int, str]] = []
	seen: set[str] = set()
	for km in kms:
		slug = km_to_slug.get(float(km))
		if slug and slug not in seen:
			pairs.append((km, slug))
			seen.add(slug)
	pairs.sort(key=lambda p: p[0])
	return ";".join(s for _, s in pairs)


def _ai_fallback_distances(detail_url: str) -> str:
	"""Call the AI-assisted scraper and return its ``distanceSlugs`` string.

	Returns ``""`` on any failure so the caller can still emit the row without
	distances (which is still valid per the data model).
	"""
	try:
		from running_calendar_scrapers.ai_scraper import scrape_race_with_ai
	except Exception:
		return ""
	try:
		result = scrape_race_with_ai(detail_url, prefer_loader="requests")
	except Exception:
		return ""
	return (result.race.get("distanceSlugs") or "").strip()


def _ai_fallback_city_state(detail_url: str) -> tuple[str, str]:
	try:
		from running_calendar_scrapers.ai_scraper import scrape_race_with_ai
	except Exception:
		return ("", "")
	try:
		result = scrape_race_with_ai(detail_url, prefer_loader="requests")
	except Exception:
		return ("", "")
	return (
		(result.race.get("city") or "").strip(),
		(result.race.get("state") or "").strip(),
	)


def fetch(url: str, *, session: requests.Session) -> str:
	r = session.get(url, timeout=60)
	r.raise_for_status()
	return r.text


def scrape_xkr_sports_calendar_html(
	home_html: str,
	event_html_by_url: dict[str, str],
	*,
	km_to_slug: dict[float, str],
	year: int | None = None,
	allow_ai_fallback: bool = True,
) -> list[ScrapedRace]:
	"""Build ``ScrapedRace`` rows from a homepage HTML plus per-event HTML.

	``event_html_by_url`` is keyed by the exact ``detail_url`` returned from
	:func:`parse_home_events`. When ``allow_ai_fallback`` is true and the event
	HTML yields no distances, the AI-assisted scraper is invoked for that URL.
	"""
	events = parse_home_events(home_html)
	out: list[ScrapedRace] = []
	for ev in events:
		if year is not None and ev.date.year != year:
			continue
		event_html = event_html_by_url.get(ev.detail_url, "")
		kms = _distance_kms_from_event_html(event_html) if event_html else []
		distance_slugs = _km_list_to_slugs(kms, km_to_slug) if kms else ""
		if not distance_slugs and allow_ai_fallback and os.environ.get("OPENAI_API_KEY"):
			distance_slugs = _ai_fallback_distances(ev.detail_url)

		name = _name_from_event_html(event_html) if event_html else ""
		if not name:
			name = ev.name

		slug = _url_slug(ev.detail_url)
		city, state = _EVENT_LOCATION.get(slug, ("", ""))
		if (not city or not state) and allow_ai_fallback and os.environ.get("OPENAI_API_KEY"):
			ai_city, ai_state = _ai_fallback_city_state(ev.detail_url)
			city = city or ai_city
			state = state or ai_state
		if not city or not state:
			# Skip rows that cannot satisfy validate-db's city/state requirement.
			continue

		out.append(
			ScrapedRace(
				sort_key=ev.date.strftime("%Y-%m-%dT%H:%M"),
				city=city,
				state=state,
				country="Brasil",
				name=name,
				type_slug="trail",
				distance_slugs=distance_slugs,
				provider_slug=PROVIDER_SLUG,
				detail_url=ev.detail_url,
			)
		)
	return sorted(out, key=lambda x: x.sort_key)


def scrape_xkr_sports_calendar(
	*,
	year: int | None = None,
	session: requests.Session | None = None,
	allow_ai_fallback: bool = True,
) -> list[ScrapedRace]:
	session = session or _session()
	km_to_slug = load_distance_slugs_by_km()
	valid_providers = load_valid_provider_slugs()
	valid_types = load_valid_type_slugs()
	if PROVIDER_SLUG not in valid_providers:
		raise RuntimeError(f"public.providers must include {PROVIDER_SLUG}")
	if "trail" not in valid_types:
		raise RuntimeError("public.types must include trail")

	home_html = fetch(HOME_URL, session=session)
	events = parse_home_events(home_html)
	event_html_by_url: dict[str, str] = {}
	for ev in events:
		if year is not None and ev.date.year != year:
			continue
		if ev.detail_url in event_html_by_url:
			continue
		try:
			event_html_by_url[ev.detail_url] = fetch(ev.detail_url, session=session)
		except requests.RequestException:
			event_html_by_url[ev.detail_url] = ""
	return scrape_xkr_sports_calendar_html(
		home_html,
		event_html_by_url,
		km_to_slug=km_to_slug,
		year=year,
		allow_ai_fallback=allow_ai_fallback,
	)


def run(argv: list[str] | None = None) -> str:
	"""CLI entry: print races CSV. Supports ``--year`` (default 2026)."""
	import argparse

	p = argparse.ArgumentParser(prog="xkr_sports", add_help=False)
	p.add_argument("--year", type=int, default=2026)
	p.add_argument(
		"--no-ai-fallback",
		action="store_true",
		help="Disable AI-assisted distance lookup when event pages lack data.",
	)
	args, _ = p.parse_known_args(argv or [])
	races = scrape_xkr_sports_calendar(
		year=args.year,
		allow_ai_fallback=not args.no_ai_fallback,
	)
	return format_races_csv(races)
