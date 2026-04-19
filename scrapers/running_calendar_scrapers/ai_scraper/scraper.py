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
from running_calendar_scrapers.ai_scraper.extractor import ensure_all_keys
from running_calendar_scrapers.ai_scraper.loader import (
	LoadedPage,
	iter_main_body_images,
	load_page,
)
from running_calendar_scrapers.ai_scraper.schema import RACE_ROW_KEYS
from running_calendar_scrapers.ai_scraper.slug import provider_slug_from_url, slugify
from running_calendar_scrapers.ports import LLMExtractor, OpenAILLMExtractor

PageLoader = Callable[[str, str], LoadedPage]
"""Port for rendering a URL. Accepts ``(url, prefer)`` and returns a ``LoadedPage``.

The default implementation is :func:`running_calendar_scrapers.ai_scraper.loader.load_page`;
tests inject a fake via the ``page_loader`` kwarg on :func:`scrape_race_with_ai` so
they no longer need to monkey-patch the ``scraper.load_page`` attribute path.
"""


# Fallback whitelist used when the caller does not supply ``valid_types``. These
# are the three slugs the AI scraper has historically coerced into; adding a new
# type in Supabase should be a caller-side concern (pass ``valid_types=``), not
# a code edit here.
DEFAULT_VALID_TYPE_SLUGS: frozenset[str] = frozenset({"road", "trail", "adventure"})
DEFAULT_TYPE_SLUG = "road"
DEFAULT_COUNTRY = "Brasil"


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


def _postprocess(
	row: dict[str, Any],
	url: str,
	*,
	valid_types: frozenset[str] | set[str] | None,
	valid_distance_slugs: set[str] | None,
	default_country: str,
) -> dict[str, str]:
	out = ensure_all_keys(row)
	out["detailUrl"] = url
	out["distanceSlugs"] = normalize_distance_slugs(
		out.get("distanceSlugs", ""),
		valid_slugs=valid_distance_slugs,
	)
	type_whitelist = valid_types or DEFAULT_VALID_TYPE_SLUGS
	type_slug = slugify(out.get("typeSlug") or DEFAULT_TYPE_SLUG) or DEFAULT_TYPE_SLUG
	# Fall back to "road" only when it is itself a valid type; otherwise pick
	# any deterministic slug from the whitelist so callers who register a
	# different type set aren't silently forced back to "road".
	if type_slug not in type_whitelist:
		type_slug = DEFAULT_TYPE_SLUG if DEFAULT_TYPE_SLUG in type_whitelist else next(iter(sorted(type_whitelist)))
	out["typeSlug"] = type_slug
	prov_raw = slugify(out.get("providerSlug") or "")
	out["providerSlug"] = prov_raw or provider_slug_from_url(url)
	if not out.get("country"):
		out["country"] = default_country
	return out


def _build_default_extractor(
	*,
	client: Any | None,
	text_model: str | None,
	vision_model: str | None,
) -> LLMExtractor:
	"""Build the default OpenAI-backed :class:`LLMExtractor`.

	Kept separate from :func:`scrape_race_with_ai` so the legacy ``client=`` /
	``text_model=`` / ``vision_model=`` kwargs continue to work as a thin shim
	over the port: pass an ``extractor=`` explicitly when you want to swap in
	a different provider (Anthropic, local model, …).
	"""
	return OpenAILLMExtractor(
		client=client,
		text_model=text_model,
		vision_model=vision_model,
	)


def scrape_race_with_ai(
	url: str,
	*,
	prefer_loader: str = "auto",
	vision_image_limit: int = 4,
	text_model: str | None = None,
	vision_model: str | None = None,
	client: Any | None = None,
	extractor: LLMExtractor | None = None,
	page_loader: PageLoader | None = None,
	valid_types: frozenset[str] | set[str] | None = None,
	valid_distance_slugs: set[str] | None = None,
	default_country: str = DEFAULT_COUNTRY,
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
		defaults in :mod:`.extractor`. Ignored when ``extractor`` is supplied.
	client:
		Pre-built OpenAI client (primarily for tests). When ``None``, a client
		is constructed lazily from the ``OPENAI_API_KEY`` env var. Ignored
		when ``extractor`` is supplied.
	extractor:
		Injected :class:`LLMExtractor` port. When supplied, ``client`` /
		``text_model`` / ``vision_model`` are ignored — use those legacy
		kwargs only when you want the default OpenAI adapter.
	page_loader:
		Injected page-loader port (``(url, prefer) -> LoadedPage``). Defaults
		to :func:`running_calendar_scrapers.ai_scraper.loader.load_page`; tests
		pass a fake so they do not need to monkey-patch imports.
	valid_types:
		Whitelist of ``type_slug`` values (typically loaded from
		``public.types``). Model output outside this set falls back to
		``road`` when present, otherwise to the alphabetically-first slug.
		Defaults to :data:`DEFAULT_VALID_TYPE_SLUGS` when ``None``.
	valid_distance_slugs:
		Whitelist of ``distance_slug`` values (typically loaded from
		``public.distances``). Derived slugs not in the whitelist are
		dropped, so the LLM cannot invent slugs that would later fail FK
		validation during ``--save-to``.
	default_country:
		Country label used when the model does not supply one. Defaults
		to :data:`DEFAULT_COUNTRY` (``"Brasil"``).
	"""
	if not url:
		raise AIScraperError("url is required")

	llm: LLMExtractor = extractor or _build_default_extractor(
		client=client,
		text_model=text_model,
		vision_model=vision_model,
	)
	loader = page_loader or _default_page_loader
	page = loader(url, prefer_loader)

	post_kwargs: dict[str, Any] = {
		"valid_types": valid_types,
		"valid_distance_slugs": valid_distance_slugs,
		"default_country": default_country,
	}

	text_row = llm.extract_from_text(url=url, title=page.title, text=page.text)

	if text_row:
		return AIScraperResult(
			race=_postprocess(text_row, url, **post_kwargs),
			source="text",
			page=page,
		)

	image_urls = list(iter_main_body_images(page, limit=vision_image_limit))
	if not image_urls:
		raise AIScraperError(
			"Text extraction returned no race data and no images were available in the main body.",
		)

	vision_row = llm.extract_from_images(url=url, title=page.title, image_urls=image_urls)

	if not vision_row:
		raise AIScraperError(
			"Both the text and image extractors failed to return a usable race row.",
		)

	return AIScraperResult(
		race=_postprocess(vision_row, url, **post_kwargs),
		source="image",
		images_inspected=len(image_urls),
		page=page,
	)


__all__ = [
	"AIScraperError",
	"AIScraperResult",
	"DEFAULT_COUNTRY",
	"DEFAULT_TYPE_SLUG",
	"DEFAULT_VALID_TYPE_SLUGS",
	"LLMExtractor",
	"PageLoader",
	"RACE_ROW_KEYS",
	"scrape_race_with_ai",
]
