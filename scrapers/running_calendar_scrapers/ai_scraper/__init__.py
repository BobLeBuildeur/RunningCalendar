"""AI-assisted race scraper.

Programmatic and CLI entry points for extracting a single race row from an
arbitrary running-race web page using a Cypress-rendered DOM snapshot plus the
OpenAI Chat Completions API.

Output follows the flat race-row contract documented in ``docs/data-model.md``:
``sortKey``, ``city``, ``state``, ``country``, ``name``, ``typeSlug``,
``distanceSlugs``, ``providerSlug``, ``detailUrl``.

See :func:`scrape_race_with_ai` for the Python entry point and
``python -m running_calendar_scrapers.ai_scraper <url>`` for the CLI.
"""

from __future__ import annotations

from running_calendar_scrapers.ai_scraper.scraper import (
	AIScraperError,
	AIScraperResult,
	scrape_race_with_ai,
)

__all__ = [
	"AIScraperError",
	"AIScraperResult",
	"scrape_race_with_ai",
]
