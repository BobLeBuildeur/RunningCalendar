"""Call the OpenAI Chat Completions API to extract a single race row.

Two entry points are exposed:

- :func:`extract_from_text` — primary path; uses the cleaned HTML text.
- :func:`extract_from_images` — vision fallback that runs only if
  :func:`extract_from_text` returns an empty/invalid row.

Both return a ``dict`` whose keys match :mod:`.schema` (flat race row), or an
empty ``dict`` when the model is not confident. All OpenAI requests are issued
with Structured Outputs so the response parses deterministically.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Iterable

from running_calendar_scrapers.ai_scraper.schema import RACE_ROW_KEYS, race_row_json_schema

DEFAULT_TEXT_MODEL = "gpt-4o-mini"
DEFAULT_VISION_MODEL = "gpt-4o-mini"
MAX_TEXT_CHARS = 18_000


def _require_api_key() -> str:
	key = (os.environ.get("OPENAI_API_KEY") or "").strip()
	if not key:
		raise RuntimeError(
			"OPENAI_API_KEY is not set; export a valid OpenAI API key before running the AI scraper.",
		)
	return key


def _truncate(text: str, *, limit: int = MAX_TEXT_CHARS) -> str:
	if len(text) <= limit:
		return text
	# Keep the top of the page (where titles/dates usually sit) plus the tail.
	head = text[: int(limit * 0.7)]
	tail = text[-int(limit * 0.3) :]
	return f"{head}\n...\n{tail}"


def _system_prompt() -> str:
	return (
		"You extract structured data about a single running race from the text of a web page. "
		"Return JSON only. When the page lists multiple races, describe ONLY the first one. "
		"For multi-day events, use the STARTING day. "
		"sortKey must be ISO local date-time YYYY-MM-DDTHH:MM (use T00:00 if only a date is known). "
		"typeSlug is one of road/trail/adventure (default road). "
		"distanceSlugs is a semicolon-separated list of kebab-case slugs: whole km as '<n>km' (e.g. '10km'), "
		"half-marathon as '21-1km', full marathon as '42-2km'; leave empty if no distances are advertised. "
		"providerSlug is a short kebab-case identifier derived from the event host. "
		"If the page does not have enough information to confidently extract ANY of name, city or date, "
		"return the JSON object {\"insufficient\": true} instead."
	)


def _user_prompt(url: str, title: str, text: str) -> str:
	return (
		f"Event URL: {url}\n"
		f"Page title: {title}\n"
		f"--- Page text start ---\n{_truncate(text)}\n--- Page text end ---"
	)


def _build_client() -> Any:
	"""Lazy-import the OpenAI SDK so importing the package never hits the network."""
	try:
		from openai import OpenAI
	except ImportError as exc:
		raise RuntimeError(
			"The 'openai' Python package is required. Install with `pip install openai`.",
		) from exc
	return OpenAI(api_key=_require_api_key())


def _parse_response_payload(payload: str) -> dict[str, Any]:
	data = json.loads(payload)
	if isinstance(data, dict) and data.get("insufficient") is True:
		return {}
	if not isinstance(data, dict):
		return {}
	return data


def _looks_complete(row: dict[str, Any]) -> bool:
	required = ("sortKey", "name")
	if not all(str(row.get(k) or "").strip() for k in required):
		return False
	# Very loose sanity check on the date format.
	return bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", str(row.get("sortKey"))))


def extract_from_text(
	*,
	url: str,
	title: str,
	text: str,
	model: str = DEFAULT_TEXT_MODEL,
	client: Any | None = None,
) -> dict[str, Any]:
	"""Ask the model to return a race row from cleaned page text.

	Returns an empty dict when the page is too thin or the model signals
	``{"insufficient": true}``.
	"""
	client = client or _build_client()
	resp = client.chat.completions.create(
		model=model,
		response_format={
			"type": "json_schema",
			"json_schema": {
				"name": "race_row",
				"strict": False,
				"schema": race_row_json_schema(),
			},
		},
		messages=[
			{"role": "system", "content": _system_prompt()},
			{"role": "user", "content": _user_prompt(url, title, text)},
		],
		temperature=0,
	)
	payload = resp.choices[0].message.content or ""
	row = _parse_response_payload(payload)
	if not row:
		return {}
	if not _looks_complete(row):
		return {}
	return row


def extract_from_images(
	*,
	url: str,
	title: str,
	image_urls: Iterable[str],
	model: str = DEFAULT_VISION_MODEL,
	client: Any | None = None,
) -> dict[str, Any]:
	"""Vision fallback: extract the race row from up to N main-body images.

	Triggered only when :func:`extract_from_text` produces nothing usable.
	"""
	urls = [u for u in image_urls if u]
	if not urls:
		return {}
	client = client or _build_client()

	content: list[dict[str, Any]] = [
		{
			"type": "text",
			"text": (
				f"Event URL: {url}\nPage title: {title}\n"
				"The images below are the main banners or flyers for the race. "
				"Extract the first race using the same JSON contract as before."
			),
		},
	]
	for src in urls:
		content.append({"type": "image_url", "image_url": {"url": src}})

	resp = client.chat.completions.create(
		model=model,
		response_format={
			"type": "json_schema",
			"json_schema": {
				"name": "race_row",
				"strict": False,
				"schema": race_row_json_schema(),
			},
		},
		messages=[
			{"role": "system", "content": _system_prompt()},
			{"role": "user", "content": content},
		],
		temperature=0,
	)
	payload = resp.choices[0].message.content or ""
	row = _parse_response_payload(payload)
	if not row or not _looks_complete(row):
		return {}
	return row


def ensure_all_keys(row: dict[str, Any]) -> dict[str, str]:
	"""Coerce model output to string values and ensure every contract key is present."""
	return {k: str(row.get(k, "") or "") for k in RACE_ROW_KEYS}
