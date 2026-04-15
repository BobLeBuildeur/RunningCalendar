"""Scrape Iguana Sports calendar (Shopify blog) into race rows."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from running_calendar_scrapers.db_ref import load_distance_slugs_by_km, load_valid_provider_slugs, load_valid_type_slugs

CALENDAR_URL = "https://iguanasports.com.br/blogs/calendario-corridas-de-rua"
BLOG_PREFIX = "/blogs/calendario-corridas-de-rua/"
USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"

_PT_MONTHS = {
	"jan": 1,
	"fev": 2,
	"mar": 3,
	"abr": 4,
	"mai": 5,
	"jun": 6,
	"jul": 7,
	"ago": 8,
	"set": 9,
	"out": 10,
	"nov": 11,
	"dez": 12,
}

_EN_MONTHS = (
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
)


@dataclass(frozen=True)
class ScrapedRace:
	sort_key: str
	city: str
	state: str
	country: str
	name: str
	type_slug: str
	distance_slugs: str
	provider_slug: str
	detail_url: str


def _session() -> requests.Session:
	s = requests.Session()
	s.headers.update({"User-Agent": USER_AGENT})
	return s


def list_calendar_slugs(html: str) -> list[str]:
	soup = BeautifulSoup(html, "html.parser")
	seen: set[str] = set()
	ordered: list[str] = []
	for a in soup.select(f'a[href*="{BLOG_PREFIX}"]'):
		href = a.get("href") or ""
		if not href:
			continue
		if href.startswith("http"):
			m = re.search(rf"{re.escape(BLOG_PREFIX)}([^/?#]+)", href)
		else:
			m = re.match(rf"{re.escape(BLOG_PREFIX)}([^/?#]+)", href)
		if not m:
			continue
		slug = m.group(1).strip()
		if not slug or slug in seen:
			continue
		seen.add(slug)
		ordered.append(slug)
	return ordered


def _parse_event_datetime(html: str) -> tuple[datetime, str]:
	"""Return (aware datetime America/Sao_Paulo), display string matching stored sort_key."""
	m = re.search(
		r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})\s+(\d{2}):(\d{2})",
		html,
	)
	if not m:
		raise ValueError("Could not find event datetime in article HTML")
	day_s, mon_s, year_s, hh, mm = m.groups()
	day = int(day_s)
	year = int(year_s)
	mon_key = mon_s.lower()[:3]
	if mon_key not in _PT_MONTHS:
		raise ValueError(f"Unknown Portuguese month token: {mon_s!r}")
	month = _PT_MONTHS[mon_key]
	dt_naive = datetime(year, month, day, int(hh), int(mm))
	tz = ZoneInfo("America/Sao_Paulo")
	dt = dt_naive.replace(tzinfo=tz)
	display = f"{day} {_EN_MONTHS[month - 1]} {year}, {hh}:{mm}"
	return dt, display


def _parse_location(html: str) -> tuple[str, str, str]:
	soup = BeautifulSoup(html, "html.parser")
	for span in soup.select("span.article-label span.feather-icon-map-pin"):
		parent = span.parent
		if not parent:
			continue
		line = parent.get_text(" ", strip=True)
		# strip leading icon noise; expect "City | ST | Country"
		m = re.search(
			r"([^|]+)\s*\|\s*([A-Z]{2})\s*\|\s*(.+)$",
			line,
		)
		if m:
			return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
	raise ValueError("Could not find location line (city | ST | country)")


def _parse_title(html: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	h2 = soup.select_one("h2.page-header")
	if h2 and h2.get_text(strip=True):
		return h2.get_text(strip=True)
	og = soup.select_one('meta[property="og:title"]')
	if og and og.get("content"):
		raw = og["content"].split("–")[0].split("-")[0].strip()
		return raw
	raise ValueError("Could not determine article title")


def _distance_slugs_from_labels(
	labels: list[str],
	km_to_slug: dict[float, str],
) -> tuple[str, str]:
	slug_to_km = {slug: km for km, slug in km_to_slug.items()}
	slugs: list[str] = []
	for raw in labels:
		t = raw.strip()
		if not t:
			continue
		if re.search(r"anos|idade|kids|infant", t, re.I):
			return ("kids-run", "")
		t_clean = t.upper().replace("KM", "").strip()
		try:
			km = float(t_clean.replace(",", "."))
		except ValueError:
			return ("", "")
		if km not in km_to_slug:
			raise ValueError(f"No distance slug for km={km} (label {raw!r})")
		slugs.append(km_to_slug[km])
	unique: list[str] = []
	for s in slugs:
		if s not in unique:
			unique.append(s)
	unique.sort(key=lambda s: slug_to_km.get(s, 0.0))
	return ";".join(unique), ""


def _parse_distance_labels(html: str) -> list[str]:
	soup = BeautifulSoup(html, "html.parser")
	block = soup.select_one("[data-distance-labels]")
	if not block:
		return []
	out: list[str] = []
	for span in block.select("span[data-label]"):
		label = span.get("data-label", "").strip()
		text = span.get_text(strip=True)
		out.append(label or text)
	return out


def fetch_race_article(session: requests.Session, calendar_slug: str) -> str:
	url = f"https://iguanasports.com.br{BLOG_PREFIX}{calendar_slug}"
	r = session.get(url, timeout=60)
	r.raise_for_status()
	return r.text


def scrape_race(
	calendar_slug: str,
	html: str,
	*,
	km_to_slug: dict[float, str],
) -> ScrapedRace:
	dt, _ = _parse_event_datetime(html)
	city, state, country = _parse_location(html)
	name = _parse_title(html)
	labels = _parse_distance_labels(html)
	dist_slugs_str, _ = _distance_slugs_from_labels(labels, km_to_slug)
	sort_key = dt.strftime("%Y-%m-%dT%H:%M")
	detail_url = f"https://iguanasports.com.br{BLOG_PREFIX}{calendar_slug}"
	return ScrapedRace(
		sort_key=sort_key,
		city=city,
		state=state,
		country=country,
		name=name,
		type_slug="road",
		distance_slugs=dist_slugs_str,
		provider_slug="iguana-sports",
		detail_url=detail_url,
	)


def scrape_iguana_calendar(*, session: requests.Session | None = None) -> list[ScrapedRace]:
	session = session or _session()
	km_to_slug = load_distance_slugs_by_km()
	valid_providers = load_valid_provider_slugs()
	valid_types = load_valid_type_slugs()
	if "iguana-sports" not in valid_providers:
		raise RuntimeError("public.providers must include iguana-sports")
	if "road" not in valid_types:
		raise RuntimeError("public.types must include road")

	r = session.get(CALENDAR_URL, timeout=60)
	r.raise_for_status()
	slugs = list_calendar_slugs(r.text)
	out: list[ScrapedRace] = []
	for slug in slugs:
		html = fetch_race_article(session, slug)
		out.append(scrape_race(slug, html, km_to_slug=km_to_slug))
	return sorted(out, key=lambda x: x.sort_key)


RACES_HEADER = [
	"sortKey",
	"city",
	"state",
	"country",
	"name",
	"typeSlug",
	"distanceSlugs",
	"providerSlug",
	"detailUrl",
]


def scraped_to_csv_rows(races: list[ScrapedRace]) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	for x in races:
		rows.append(
			{
				"sortKey": x.sort_key,
				"city": x.city,
				"state": x.state,
				"country": x.country,
				"name": x.name,
				"typeSlug": x.type_slug,
				"distanceSlugs": x.distance_slugs,
				"providerSlug": x.provider_slug,
				"detailUrl": x.detail_url,
			}
		)
	return rows


def format_races_csv(races: list[ScrapedRace]) -> str:
	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=RACES_HEADER, lineterminator="\n")
	writer.writeheader()
	for row in scraped_to_csv_rows(races):
		writer.writerow(row)
	return buf.getvalue()


def parse_races_csv(text: str) -> list[dict[str, str]]:
	reader = csv.DictReader(io.StringIO(text))
	return [dict(row) for row in reader]


def run(argv: list[str] | None = None) -> str:
	"""CLI entry: print races CSV. Ignores unknown flags (e.g. other scrapers' options)."""
	import argparse

	p = argparse.ArgumentParser(prog="iguana", add_help=False)
	p.parse_known_args(argv or [])
	return format_races_csv(scrape_iguana_calendar())
