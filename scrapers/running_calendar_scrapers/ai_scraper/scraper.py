"""High-level entry point: ``scrape_race_with_ai(url) -> AIScraperResult``.

Pipeline:

1. Load the page (Cypress preferred, ``requests`` fallback).
2. Ask OpenAI (text) to extract a structured race row.
3. If the text pass is empty, run the vision fallback on up to 4 main-body images.
4. Post-process the result: normalise distance slugs, coerce the provider slug,
   default the type slug / country, and always echo the requested URL back into
   ``detailUrl``.

The return value is an :class:`AIScraperResult` containing the flat race row
and a small amount of metadata about which path was used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from running_calendar_scrapers.ai_scraper.distance import normalize_distance_slugs
from running_calendar_scrapers.ai_scraper.extractor import (
	ensure_all_keys,
	extract_from_images,
	extract_from_text,
)
from running_calendar_scrapers.ai_scraper.loader import (
	LoadedPage,
	iter_main_body_images,
	load_page,
)
from running_calendar_scrapers.ai_scraper.schema import RACE_ROW_KEYS
from running_calendar_scrapers.ai_scraper.slug import provider_slug_from_url, slugify

PageLoader = Callable[[str, str], LoadedPage]
"""Port for rendering a URL. Accepts ``(url, prefer)`` and returns a ``LoadedPage``.

The default implementation is :func:`running_calendar_scrapers.ai_scraper.loader.load_page`;
tests inject a fake via the ``page_loader`` kwarg on :func:`scrape_race_with_ai` so
they no longer need to monkey-patch the ``scraper.load_page`` attribute path.
"""


def _default_page_loader(url: str, prefer: str) -> LoadedPage:
	return load_page(url, prefer=prefer)


class AIScraperError(RuntimeError):
	"""Raised when the pipeline cannot produce a race row for the caller."""


@dataclass(frozen=True)
class AIScraperResult:
	"""Structured output of :func:`scrape_race_with_ai`.

	``race`` is a flat dict with the exact keys listed in
	:data:`running_calendar_scrapers.ai_scraper.schema.RACE_ROW_KEYS`.
	``source`` is ``"text"`` or ``"image"`` depending on which extractor produced
	a usable row. ``images_inspected`` is the number of images passed to the
	vision fallback (``0`` when the text pass succeeded).
	"""

	race: dict[str, str]
	source: str
	images_inspected: int = 0
	page: LoadedPage | None = field(default=None, repr=False)


def _postprocess(row: dict[str, Any], url: str) -> dict[str, str]:
	out = ensure_all_keys(row)
	out["detailUrl"] = url
	out["distanceSlugs"] = normalize_distance_slugs(out.get("distanceSlugs", ""))
	type_slug = slugify(out.get("typeSlug") or "road") or "road"
	if type_slug not in {"road", "trail", "adventure"}:
		type_slug = "road"
	out["typeSlug"] = type_slug
	prov_raw = slugify(out.get("providerSlug") or "")
	out["providerSlug"] = prov_raw or provider_slug_from_url(url)
	if not out.get("country"):
		out["country"] = "Brasil"
	return out


def scrape_race_with_ai(
	url: str,
	*,
	prefer_loader: str = "auto",
	vision_image_limit: int = 4,
	text_model: str | None = None,
	vision_model: str | None = None,
	client: Any | None = None,
	page_loader: PageLoader | None = None,
) -> AIScraperResult:
	"""Scrape a single race row from an arbitrary running-race page.

	Parameters
	----------
	url:
		Event URL to scrape. Echoed into ``race["detailUrl"]``.
	prefer_loader:
		Loader preference: ``"auto"`` (default), ``"cypress"`` (hard require),
		or ``"requests"`` (skip the browser).
	vision_image_limit:
		Maximum number of main-body images forwarded to the vision fallback.
	text_model / vision_model:
		Override the default OpenAI models (``gpt-4o-mini``). ``None`` uses the
		defaults in :mod:`.extractor`.
	client:
		Pre-built OpenAI client (primarily for tests). When ``None``, a client
		is constructed lazily from the ``OPENAI_API_KEY`` env var.
	page_loader:
		Injected page-loader port (``(url, prefer) -> LoadedPage``). Defaults
		to :func:`running_calendar_scrapers.ai_scraper.loader.load_page`; tests
		pass a fake so they do not need to monkey-patch imports.
	"""
	if not url:
		raise AIScraperError("url is required")

	loader = page_loader or _default_page_loader
	page = loader(url, prefer_loader)

	text_kwargs: dict[str, Any] = {
		"url": url,
		"title": page.title,
		"text": page.text,
		"client": client,
	}
	if text_model:
		text_kwargs["model"] = text_model
	text_row = extract_from_text(**text_kwargs)

	if text_row:
		return AIScraperResult(
			race=_postprocess(text_row, url),
			source="text",
			page=page,
		)

	image_urls = list(iter_main_body_images(page, limit=vision_image_limit))
	if not image_urls:
		raise AIScraperError(
			"Text extraction returned no race data and no images were available in the main body.",
		)

	vision_kwargs: dict[str, Any] = {
		"url": url,
		"title": page.title,
		"image_urls": image_urls,
		"client": client,
	}
	if vision_model:
		vision_kwargs["model"] = vision_model
	vision_row = extract_from_images(**vision_kwargs)

	if not vision_row:
		raise AIScraperError(
			"Both the text and image extractors failed to return a usable race row.",
		)

	return AIScraperResult(
		race=_postprocess(vision_row, url),
		source="image",
		images_inspected=len(image_urls),
		page=page,
	)


__all__ = [
	"AIScraperError",
	"AIScraperResult",
	"PageLoader",
	"RACE_ROW_KEYS",
	"scrape_race_with_ai",
]
