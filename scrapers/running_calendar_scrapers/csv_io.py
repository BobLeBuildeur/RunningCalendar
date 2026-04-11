"""Read distances and types from repo CSVs (for validation)."""

from __future__ import annotations

import csv
from pathlib import Path


def repo_root() -> Path:
	return Path(__file__).resolve().parents[2]


def load_distance_slugs_by_km() -> dict[float, str]:
	path = repo_root() / "src" / "data" / "distances.csv"
	by_km: dict[float, str] = {}
	with path.open(newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			km = float(row["km"].strip())
			by_km[km] = row["slug"].strip()
	return by_km


def load_valid_type_slugs() -> set[str]:
	path = repo_root() / "src" / "data" / "types.csv"
	with path.open(newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		return {row["slug"].strip() for row in reader if row.get("slug")}


def load_valid_provider_slugs() -> set[str]:
	path = repo_root() / "src" / "data" / "providers.csv"
	with path.open(newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		return {row["slug"].strip() for row in reader if row.get("slug")}
