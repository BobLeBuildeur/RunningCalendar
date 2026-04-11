"""Scrape Yescom public calendar (ASP table) into race rows."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from running_calendar_scrapers.csv_io import load_valid_provider_slugs, load_valid_type_slugs
from running_calendar_scrapers.iguana import RACES_HEADER, ScrapedRace, scraped_to_csv_rows

CALENDAR_ASP = "https://www.yescom.com.br/yescom/novosite/codigos/calendario_2016.asp"
USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"

_MONTH_TOKEN = {
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


def _session() -> requests.Session:
	s = requests.Session()
	s.headers.update({"User-Agent": USER_AGENT})
	return s


def _slugify(name: str, year: int, seq: int) -> str:
	base = re.sub(r"[^a-z0-9]+", "-", name.lower())
	base = re.sub(r"-+", "-", base).strip("-")
	return f"yescom-{year}-{seq:04d}-{base}"[:120]


def _parse_onclick_url(onclick: str) -> str | None:
	m = re.search(r"window\.open\(\s*['\"]([^'\"]+)['\"]", onclick)
	return m.group(1).strip() if m else None


def _parse_date_cell(cell: str, year: int) -> tuple[datetime, str]:
	# e.g. "25/Jan" or "08/Mar"
	cell = cell.strip()
	m = re.match(r"(\d{1,2})/([A-Za-zÀ-ÿ]{3})", cell)
	if not m:
		raise ValueError(f"Unexpected date cell: {cell!r}")
	day = int(m.group(1))
	mon_key = m.group(2).lower()[:3]
	if mon_key not in _MONTH_TOKEN:
		raise ValueError(f"Unknown month in date cell: {cell!r}")
	month = _MONTH_TOKEN[mon_key]
	dt = datetime(year, month, day, 12, 0)
	display = f"{day} {_EN_MONTHS[month - 1]} {year}, 12:00"
	return dt, display


def fetch_yescom_calendar_html(year: int, *, session: requests.Session | None = None) -> str:
	session = session or _session()
	url = f"{CALENDAR_ASP}?AnoEvento={year}"
	r = session.get(url, timeout=60)
	r.raise_for_status()
	if r.encoding is None or r.encoding.lower() == "iso-8859-1":
		r.encoding = r.apparent_encoding
	return r.text


def scrape_yescom_calendar(year: int, *, session: requests.Session | None = None) -> list[ScrapedRace]:
	session = session or _session()
	valid_providers = load_valid_provider_slugs()
	valid_types = load_valid_type_slugs()
	if "yescom" not in valid_providers:
		raise RuntimeError("providers.csv must define yescom")
	if "road" not in valid_types:
		raise RuntimeError("types.csv must define road")

	html = fetch_yescom_calendar_html(year, session=session)
	soup = BeautifulSoup(html, "html.parser")
	rows = soup.select("tr.hover-link-calendar")
	out: list[ScrapedRace] = []
	for idx, tr in enumerate(rows, start=1):
		onclick = tr.get("onclick") or ""
		url = _parse_onclick_url(onclick)
		if not url:
			continue
		cells = tr.find_all("td")
		if len(cells) < 3:
			continue
		date_cell = cells[0].get_text(" ", strip=True)
		name = cells[1].get_text(" ", strip=True)
		# location is nice-to-have; keep in city field as full place string
		place = cells[2].get_text(" ", strip=True)
		if not name:
			continue
		try:
			dt, date_display = _parse_date_cell(date_cell, year)
		except ValueError:
			continue
		sort_key = dt.strftime("%Y-%m-%dT%H:%M")
		calendar_slug = _slugify(name, year, idx)
		# Split "São Paulo-SP" style if present
		city = place
		state = ""
		country = "Brasil"
		if "-" in place and len(place.split("-")) == 2:
			left, right = place.rsplit("-", 1)
			if len(right) <= 3 and right.isalpha():
				city = left.strip()
				state = right.strip()
		out.append(
			ScrapedRace(
				sort_key=sort_key,
				date_time_display=date_display,
				city=city,
				state=state,
				country=country,
				name=name,
				type_slug="road",
				distance_slugs="",
				distances_note="Distances not listed on Yescom calendar source",
				calendar_slug=calendar_slug,
				provider_slug="yescom",
				detail_url=url,
			)
		)
	return sorted(out, key=lambda x: x.sort_key)


def format_yescom_csv(races: list[ScrapedRace]) -> str:
	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=RACES_HEADER, lineterminator="\n")
	writer.writeheader()
	for row in scraped_to_csv_rows(races):
		writer.writerow(row)
	return buf.getvalue()
