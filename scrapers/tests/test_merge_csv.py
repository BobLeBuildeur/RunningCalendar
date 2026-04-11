"""Tests for incremental CSV merge and normalization."""

from __future__ import annotations

from pathlib import Path

from running_calendar_scrapers.merge_csv import merge_new_races, normalize_detail_url_for_key


def test_normalize_detail_url_for_key():
	assert normalize_detail_url_for_key("HTTPS://Example.COM/foo/bar/") == "https://example.com/foo/bar"


def test_merge_skips_duplicate_detail_url(tmp_path: Path):
	data_dir = tmp_path / "data"
	data_dir.mkdir()
	(data_dir / "distances.csv").write_text(
		"slug,km,description\n5km,50,\n",
		encoding="utf-8",
	)
	(data_dir / "types.csv").write_text("slug,type\nroad,Road\n", encoding="utf-8")
	(data_dir / "providers.csv").write_text(
		"slug,name,website\np1,P1,https://p1\n",
		encoding="utf-8",
	)
	existing = [
		{
			"sortKey": "2026-01-01T10:00",
			"city": "X",
			"state": "SP",
			"country": "Brasil",
			"name": "Old",
			"typeSlug": "road",
			"distanceSlugs": "5km",
			"providerSlug": "p1",
			"detailUrl": "https://a.com/x",
		}
	]
	new_row = {
		**existing[0],
		"name": "New Name",
	}
	combined, dups, skips = merge_new_races([new_row], existing, data_dir=data_dir)
	assert len(combined) == 1
	assert combined[0]["name"] == "Old"
	assert len(dups) == 1
	assert "detailUrl" in dups[0]


def test_merge_adds_new_row(tmp_path: Path):
	data_dir = tmp_path / "data"
	data_dir.mkdir()
	(data_dir / "distances.csv").write_text(
		"slug,km,description\n5km,50,\n",
		encoding="utf-8",
	)
	(data_dir / "types.csv").write_text("slug,type\nroad,Road\n", encoding="utf-8")
	(data_dir / "providers.csv").write_text(
		"slug,name,website\np1,P1,https://p1\n",
		encoding="utf-8",
	)
	existing: list[dict[str, str]] = []
	new_row = {
		"sortKey": "2026-02-01T10:00",
		"city": "Y",
		"state": "RJ",
		"country": "Brasil",
		"name": "New  Race",
		"typeSlug": "road",
		"distanceSlugs": "5km",
		"providerSlug": "p1",
		"detailUrl": "https://b.com/y",
	}
	combined, dups, skips = merge_new_races([new_row], existing, data_dir=data_dir)
	assert len(combined) == 1
	assert combined[0]["name"] == "New Race"
	assert not dups
