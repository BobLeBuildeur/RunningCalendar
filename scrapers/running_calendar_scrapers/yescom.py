"""Scrape Yescom public calendar (ASP table) into race rows."""

from __future__ import annotations

import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from running_calendar_scrapers.context import get_reference_data
from running_calendar_scrapers.http import make_session
from running_calendar_scrapers.locale_pt import EN_MONTH_ABBR, pt_month_number
from running_calendar_scrapers.ports import ReferenceData, load_reference_data_from_db
from running_calendar_scrapers.race_row import ScrapedRace, format_races_csv

CALENDAR_ASP = "https://www.yescom.com.br/yescom/novosite/codigos/calendario_2016.asp"


def _session() -> requests.Session:
	return make_session()


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
	month = pt_month_number(m.group(2))
	if month is None:
		raise ValueError(f"Unknown month in date cell: {cell!r}")
	dt = datetime(year, month, day, 12, 0)
	display = f"{day} {EN_MONTH_ABBR[month - 1]} {year}, 12:00"
	return dt, display


def fetch_yescom_calendar_html(year: int, *, session: requests.Session | None = None) -> str:
	session = session or _session()
	url = f"{CALENDAR_ASP}?AnoEvento={year}"
	r = session.get(url, timeout=60)
	r.raise_for_status()
	if r.encoding is None or r.encoding.lower() == "iso-8859-1":
		r.encoding = r.apparent_encoding
	return r.text


def scrape_yescom_calendar(
	year: int,
	*,
	session: requests.Session | None = None,
	reference_data: ReferenceData | None = None,
) -> list[ScrapedRace]:
	session = session or _session()
	ref = reference_data or get_reference_data() or load_reference_data_from_db()
	if "yescom" not in ref.valid_provider_slugs:
		raise RuntimeError("public.providers must include yescom")
	if "road" not in ref.valid_type_slugs:
		raise RuntimeError("public.types must include road")

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
			dt, _ = _parse_date_cell(date_cell, year)
		except ValueError:
			continue
		sort_key = dt.strftime("%Y-%m-%dT%H:%M")
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
				city=city,
				state=state,
				country=country,
				name=name,
				type_slug="road",
				distance_slugs="",
				provider_slug="yescom",
				detail_url=url,
			)
		)
	return sorted(out, key=lambda x: x.sort_key)


def format_yescom_csv(races: list[ScrapedRace]) -> str:
	return format_races_csv(races)


def run(argv: list[str] | None = None) -> str:
	"""CLI entry: print races CSV. Supports ``--year`` (default 2026)."""
	import argparse

	p = argparse.ArgumentParser(prog="yescom", add_help=False)
	p.add_argument("--year", type=int, default=2026)
	args = p.parse_args(argv or [])
	return format_yescom_csv(scrape_yescom_calendar(args.year))
