"""Shared distance-slug validation + serialisation for scrapers.

Every provider scraper had its own function that took parsed km values,
looked them up in ``public.distances`` (via ``km_to_slug``), deduplicated,
sorted by km, and joined with ``;``. The looks-up-dedupe-sort step was
identical across all three scrapers — what differed was only the
**tokenisation** (HTML labels vs prose blob vs modality IDs) and the
**policy for unknown km** (Iguana raises, Corre Brasil / Running Land
drop silently).

This module centralises the common core so every scraper calls the same
helper after tokenisation, and the unknown-km policy is a single boolean
(``strict``) rather than four slightly different implementations.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §4.5.
"""

from __future__ import annotations

from typing import Iterable, Mapping


def kms_to_distance_slugs(
	kms: Iterable[float],
	km_to_slug: Mapping[float, str],
	*,
	strict: bool = False,
) -> str:
	"""Return a ``;``-joined, deduplicated, km-sorted distance-slug list.

	Parameters
	----------
	kms:
		Km values already parsed from the provider-specific input.
	km_to_slug:
		Whitelist loaded from ``public.distances``. Each km value must be
		present to become a slug.
	strict:
		When ``True`` (Iguana semantics), an unknown km raises
		``ValueError``. When ``False`` (Corre Brasil / Running Land / AI
		scraper semantics), unknown km values are silently dropped.
	"""
	slug_to_km = {slug: km for km, slug in km_to_slug.items()}
	slugs: list[str] = []
	for km in kms:
		slug = km_to_slug.get(km)
		if slug is None:
			if strict:
				raise ValueError(f"No distance slug for km={km!r}")
			continue
		if slug not in slugs:
			slugs.append(slug)
	slugs.sort(key=lambda s: slug_to_km.get(s, 0.0))
	return ";".join(slugs)


__all__ = ["kms_to_distance_slugs"]
