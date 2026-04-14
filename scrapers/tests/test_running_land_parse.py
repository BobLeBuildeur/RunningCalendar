"""Unit tests for Running Land scraper helpers (no network)."""

from __future__ import annotations

from running_calendar_scrapers.running_land import (
	_city_state_country,
	_detail_url,
	_distance_slugs_from_modality_ids,
	_infer_type_slug,
	_label_to_km,
)


def test_label_to_km():
	assert _label_to_km("5K") == 5.0
	assert _label_to_km("10K") == 10.0
	assert _label_to_km("21K") == 21.0
	assert _label_to_km("Caminhada") is None


def test_infer_type_slug():
	assert _infer_type_slug("Meia Maratona X", ["10K"]) == "road"
	assert _infer_type_slug("Ultra Trail Y", []) == "trail"
	assert _infer_type_slug("Volta Ciclística Z", []) == "adventure"


def test_city_state_country():
	city_m = {"179": "Rio de Janeiro"}
	reg_m = {"49": " RJ"}
	city, state, country = _city_state_country(179, 49, city_m, reg_m)
	assert city == "Rio de Janeiro"
	assert state == "RJ"
	assert country == "Brasil"


def test_distance_slugs_from_modality():
	km_to_slug = {5.0: "5k", 10.0: "10k", 21.0: "half-marathon"}
	mod_map = {"38": "5K", "41": "10K"}
	assert (
		_distance_slugs_from_modality_ids("38,41", mod_map, km_to_slug, name="X") == "5k;10k"
	)


def test_detail_url():
	assert _detail_url("longevidade-bradesco-rio-de-janeiro-2026").endswith(
		"/eventos/longevidade-bradesco-rio-de-janeiro-2026"
	)
