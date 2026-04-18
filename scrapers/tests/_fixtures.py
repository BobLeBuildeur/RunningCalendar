"""Offline fixture data (km→slug maps) for scraper parser tests.

Previously these helpers lived in ``running_calendar_scrapers/db_ref.py``
next to the live Postgres loaders. Tests change for **test** reasons
(fixture HTML evolves); DB loaders change for **schema** reasons. Keeping
them in the same module was a single-responsibility smell — see
``docs/reports/2026-04-17-scraper-architecture-audit.md`` §1.3.
"""

from __future__ import annotations


def km_to_slug_iguana_html_tests() -> dict[float, str]:
	"""Minimal km→slug map for offline ``iguana`` HTML fixtures (no database)."""
	return {
		7.0: "7km",
		14.0: "14km",
		21.1: "21-1km",
		28.0: "28km",
		0.0: "kids-run",
	}


def km_to_slug_corre_brasil_repeater() -> dict[float, str]:
	"""Km→slug map matching ``corre_brasil_repeater.html`` snapshot expectations (no database)."""
	return {
		3.0: "3km",
		5.0: "5km",
		6.0: "6km",
		10.0: "10km",
		12.0: "12km",
		15.0: "15km",
		21.0: "21km",
		25.0: "25km",
		37.0: "37km",
		42.0: "42km",
		55.0: "55km",
		67.0: "67km",
		104.0: "104km",
		0.0: "kids-run",
	}
