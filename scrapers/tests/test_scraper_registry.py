"""Tests for the explicit scraper registry (principle 5.1)."""

from __future__ import annotations

import pytest

from running_calendar_scrapers.scraper_registry import (
	SCRAPER_ENTRIES,
	Scraper,
	available_scrapers,
	expand_scraper_names,
	get_scraper,
)


def test_available_scrapers_is_sorted_and_non_empty():
	names = available_scrapers()
	assert names == sorted(names), "list must be stable (alphabetical)"
	assert set(names) >= {"iguana", "yescom", "corre_brasil", "running_land"}


def test_every_registered_module_satisfies_scraper_protocol():
	"""Each registered module must expose a callable ``run`` (typed Scraper port)."""
	import importlib

	for entry in SCRAPER_ENTRIES:
		mod = importlib.import_module(entry.module)
		assert isinstance(mod, Scraper), f"{entry.module} does not satisfy Scraper protocol"
		assert callable(mod.run)


def test_expand_all_preserves_registry_order():
	assert expand_scraper_names(["all"]) == available_scrapers()


def test_expand_deduplicates_and_validates():
	assert expand_scraper_names(["iguana", "iguana", "yescom"]) == ["iguana", "yescom"]


def test_expand_unknown_name_raises_with_helpful_message():
	with pytest.raises(KeyError) as excinfo:
		expand_scraper_names(["does_not_exist"])
	msg = str(excinfo.value)
	assert "does_not_exist" in msg
	assert "Available:" in msg
	assert "iguana" in msg


def test_get_scraper_returns_entry_and_loads_run():
	entry = get_scraper("iguana")
	assert entry.name == "iguana"
	assert entry.module == "running_calendar_scrapers.iguana"
	run = entry.load_run()
	assert callable(run)
