"""Merge scraped race rows into repo CSVs with normalization and deduplication."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from running_calendar_scrapers.csv_io import repo_root
from running_calendar_scrapers.iguana import RACES_HEADER, parse_races_csv

__all__ = [
	"normalize_detail_url_for_key",
	"normalize_race_row",
	"merge_new_races",
	"partition_scraped_races",
	"write_races_csv",
]


def normalize_detail_url_for_key(url: str) -> str:
	"""Stable string for duplicate detection (strip, no trailing slash path)."""
	t = (url or "").strip()
	if not t:
		return ""
	parsed = urlparse(t)
	path = parsed.path.rstrip("/")
	netloc = parsed.netloc.lower()
	return urlunparse((parsed.scheme.lower(), netloc, path, "", "", ""))


def _slug_order(distances_path: Path) -> dict[str, float]:
	"""slug -> km for sorting distanceSlugs (CSV km column is integer tenths of a km)."""
	order: dict[str, float] = {}
	with distances_path.open(newline="", encoding="utf-8") as f:
		for row in csv.DictReader(f):
			slug = row["slug"].strip()
			order[slug] = int(row["km"].strip()) / 10.0
	return order


def normalize_race_row(
	row: dict[str, str],
	*,
	slug_to_km: dict[str, float],
	valid_dist: set[str],
	valid_types: set[str],
	valid_providers: set[str],
) -> tuple[dict[str, str], list[str]]:
	"""
	Return a normalized copy and any validation warnings (non-fatal).
	Invalid FKs return empty list and warnings so the caller can skip the row.
	"""
	warnings: list[str] = []
	out = {k: (row.get(k) or "").strip() for k in RACES_HEADER}

	ts = out["typeSlug"]
	if ts not in valid_types:
		return {}, [f"skip: unknown typeSlug {ts!r} for detailUrl={out.get('detailUrl', '')!r}"]

	ps = out["providerSlug"]
	if ps not in valid_providers:
		return {}, [f"skip: unknown providerSlug {ps!r} for detailUrl={out.get('detailUrl', '')!r}"]

	# distanceSlugs: validate and sort by km
	raw_slugs = [s.strip() for s in out["distanceSlugs"].split(";") if s.strip()]
	bad = [s for s in raw_slugs if s not in valid_dist]
	if bad:
		return {}, [f"skip: unknown distance slug(s) {bad} for detailUrl={out['detailUrl']!r}"]

	unique_sorted = sorted(set(raw_slugs), key=lambda s: slug_to_km.get(s, 0.0))
	out["distanceSlugs"] = ";".join(unique_sorted)

	# Name: collapse internal whitespace
	out["name"] = re.sub(r"\s+", " ", out["name"]).strip()

	return out, warnings


def _existing_urls(rows: list[dict[str, str]]) -> set[str]:
	urls: set[str] = set()
	for r in rows:
		du = normalize_detail_url_for_key(r.get("detailUrl") or "")
		if du:
			urls.add(du)
	return urls


def _validation_context(data_dir: Path) -> tuple[dict[str, float], set[str], set[str], set[str]]:
	distances_path = data_dir / "distances.csv"
	slug_to_km = _slug_order(distances_path)
	valid_dist = set(slug_to_km.keys())

	types_path = data_dir / "types.csv"
	with types_path.open(encoding="utf-8", newline="") as f:
		valid_types = {r["slug"].strip() for r in csv.DictReader(f) if r.get("slug")}

	prov_path = data_dir / "providers.csv"
	with prov_path.open(encoding="utf-8", newline="") as f:
		valid_providers = {r["slug"].strip() for r in csv.DictReader(f) if r.get("slug")}

	return slug_to_km, valid_dist, valid_types, valid_providers


def partition_scraped_races(
	new_rows: list[dict[str, str]],
	existing_detail_url_keys: set[str],
	*,
	data_dir: Path,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
	"""
	Normalize scraped rows and return only those whose ``detailUrl`` is not in
	``existing_detail_url_keys`` (normalized keys from :func:`normalize_detail_url_for_key`).

	``existing_detail_url_keys`` should include every URL already present in the target
	(e.g. Supabase ``races.detail_url`` or merged CSV rows).

	Returns (rows_to_insert_sorted, duplicate_messages, skip_messages).
	"""
	slug_to_km, valid_dist, valid_types, valid_providers = _validation_context(data_dir)
	seen = set(existing_detail_url_keys)
	to_add: list[dict[str, str]] = []
	duplicate_msgs: list[str] = []
	skip_msgs: list[str] = []

	for raw in new_rows:
		norm, warns = normalize_race_row(
			raw,
			slug_to_km=slug_to_km,
			valid_dist=valid_dist,
			valid_types=valid_types,
			valid_providers=valid_providers,
		)
		for w in warns:
			skip_msgs.append(w)
		if not norm:
			continue

		du_key = normalize_detail_url_for_key(norm["detailUrl"])

		if du_key and du_key in seen:
			duplicate_msgs.append(
				f"duplicate (detailUrl): {norm['detailUrl']!r} — not merged",
			)
			continue

		to_add.append(norm)
		if du_key:
			seen.add(du_key)

	to_add.sort(key=lambda r: r["sortKey"])
	return to_add, duplicate_msgs, skip_msgs


def merge_new_races(
	new_rows: list[dict[str, str]],
	existing_rows: list[dict[str, str]],
	*,
	data_dir: Path,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
	"""
	Merge normalized new rows into existing; skip duplicates.

	Returns (combined_rows_sorted, duplicate_messages, skip_messages).
	"""
	existing_urls = _existing_urls(existing_rows)
	to_add, duplicate_msgs, skip_msgs = partition_scraped_races(
		new_rows,
		existing_urls,
		data_dir=data_dir,
	)
	combined = [dict(r) for r in existing_rows] + to_add
	combined.sort(key=lambda r: r["sortKey"])
	return combined, duplicate_msgs, skip_msgs


def write_races_csv(path: Path, rows: list[dict[str, str]]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open("w", newline="", encoding="utf-8") as f:
		w = csv.DictWriter(f, fieldnames=RACES_HEADER, lineterminator="\n")
		w.writeheader()
		for row in rows:
			w.writerow({k: row.get(k, "") for k in RACES_HEADER})


def load_races_csv_file(path: Path) -> list[dict[str, str]]:
	if not path.is_file():
		return []
	text = path.read_text(encoding="utf-8")
	return parse_races_csv(text)
