"""Tests for the shared kms_to_distance_slugs helper (principle 4.5)."""

from __future__ import annotations

import pytest

from running_calendar_scrapers.distance_slugs import kms_to_distance_slugs


_KM_TO_SLUG = {
	5.0: "5km",
	10.0: "10km",
	21.1: "21-1km",
	42.2: "42-2km",
}


def test_joins_and_sorts_by_km():
	assert kms_to_distance_slugs([10.0, 5.0, 21.1], _KM_TO_SLUG) == "5km;10km;21-1km"


def test_deduplicates_repeated_km():
	assert kms_to_distance_slugs([5.0, 5.0, 10.0, 5.0], _KM_TO_SLUG) == "5km;10km"


def test_empty_input_returns_empty_string():
	assert kms_to_distance_slugs([], _KM_TO_SLUG) == ""


def test_strict_true_raises_on_unknown_km():
	with pytest.raises(ValueError, match="km=3.7"):
		kms_to_distance_slugs([5.0, 3.7], _KM_TO_SLUG, strict=True)


def test_strict_false_drops_unknown_km():
	assert kms_to_distance_slugs([5.0, 3.7, 10.0], _KM_TO_SLUG, strict=False) == "5km;10km"


def test_default_is_non_strict():
	assert kms_to_distance_slugs([3.7], _KM_TO_SLUG) == ""
