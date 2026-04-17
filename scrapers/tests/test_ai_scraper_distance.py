"""Unit tests for the AI scraper distance-slug normaliser."""

from __future__ import annotations

from running_calendar_scrapers.ai_scraper.distance import (
	normalize_distance_slugs,
	normalize_distance_token,
)


def test_normalize_single_tokens():
	assert normalize_distance_token("10km") == "10km"
	assert normalize_distance_token("10") == "10km"
	assert normalize_distance_token("5 km") == "5km"
	assert normalize_distance_token("21.1km") == "21-1km"
	assert normalize_distance_token("21,1") == "21-1km"
	assert normalize_distance_token("42.2 km") == "42-2km"
	assert normalize_distance_token("2,5") == "2-5km"


def test_normalize_non_numeric_tokens():
	assert normalize_distance_token("kids") == "kids-run"
	assert normalize_distance_token("KIDS-RUN") == "kids-run"
	assert normalize_distance_token("infantil") is None
	assert normalize_distance_token("") is None


def test_normalize_distance_slugs_tom_jerry():
	# CSV example from the request: "2.5;5;10"
	assert normalize_distance_slugs("2.5;5;10") == "2-5km;5km;10km"


def test_normalize_distance_slugs_ktr():
	assert normalize_distance_slugs("7;12;21;30;50;80") == "7km;12km;21km;30km;50km;80km"


def test_normalize_distance_slugs_dedup_and_sort():
	assert normalize_distance_slugs("10km,5km,10km,21.1km") == "5km;10km;21-1km"


def test_normalize_distance_slugs_drops_unknowns():
	assert normalize_distance_slugs("5km;kids;junk;21,1km") == "kids-run;5km;21-1km"
