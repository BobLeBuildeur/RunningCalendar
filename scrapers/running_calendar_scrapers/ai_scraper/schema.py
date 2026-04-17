"""Structured-output schema used to constrain the OpenAI response.

The schema mirrors the flat race-row contract in ``docs/data-model.md``:

- ``sortKey`` — ISO ``YYYY-MM-DDTHH:MM`` local date-time of the **starting day**
  of the race (required).
- ``city``, ``state``, ``country`` — location strings; ``state`` should be a
  2-letter UF for Brazil when identifiable, otherwise empty.
- ``name`` — full race title.
- ``typeSlug`` — kebab-case type slug (``road``, ``trail``, ``adventure``); the
  tool defaults to ``road`` when the page does not specify.
- ``distanceSlugs`` — ``;``-separated kebab-case distance tokens such as
  ``5km;10km;21-1km`` (see :mod:`distance helpers<.distance>`).
- ``providerSlug`` — kebab-case provider slug inferred from the event URL.
- ``detailUrl`` — the public event page URL (echoed from the request).
"""

from __future__ import annotations

from typing import Any

RACE_ROW_KEYS: tuple[str, ...] = (
	"sortKey",
	"city",
	"state",
	"country",
	"name",
	"typeSlug",
	"distanceSlugs",
	"providerSlug",
	"detailUrl",
)


def race_row_json_schema() -> dict[str, Any]:
	"""Return a JSON Schema used with OpenAI Structured Outputs.

	The schema is intentionally permissive about ``state`` (may be empty if the
	page does not clearly indicate a UF) and ``distanceSlugs`` (empty string if
	no distances are advertised).
	"""
	return {
		"type": "object",
		"additionalProperties": False,
		"required": list(RACE_ROW_KEYS),
		"properties": {
			"sortKey": {
				"type": "string",
				"description": (
					"Starting-day ISO local date-time of the race formatted as "
					"YYYY-MM-DDTHH:MM. If only a date is known, use T00:00."
				),
			},
			"city": {"type": "string"},
			"state": {
				"type": "string",
				"description": "2-letter UF for Brazil or equivalent short code; empty if unknown.",
			},
			"country": {"type": "string"},
			"name": {"type": "string"},
			"typeSlug": {
				"type": "string",
				"description": "Kebab-case type slug. Use 'road' unless the page clearly states trail/adventure/etc.",
			},
			"distanceSlugs": {
				"type": "string",
				"description": (
					"Semicolon-separated kebab-case distance slugs such as '5km;10km;21-1km'. "
					"Use '21-1km' for the half marathon and '42-2km' for the full marathon. "
					"Empty string if the page does not list distances."
				),
			},
			"providerSlug": {
				"type": "string",
				"description": "Kebab-case provider slug derived from the event host.",
			},
			"detailUrl": {"type": "string"},
		},
	}
