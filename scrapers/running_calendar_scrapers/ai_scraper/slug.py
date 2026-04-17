"""Slug helpers (kebab-case normalisation + provider-from-URL inference)."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse


def slugify(raw: str) -> str:
	"""Return a kebab-case slug matching ``^[a-z0-9]+(-[a-z0-9]+)*$`` or ``""``.

	Strips diacritics, lowercases, replaces runs of non-alphanumerics with a
	single hyphen, and trims leading/trailing hyphens (see
	``docs/slug-conventions.md``).
	"""
	if not raw:
		return ""
	stripped = unicodedata.normalize("NFKD", raw)
	ascii_only = "".join(ch for ch in stripped if not unicodedata.combining(ch))
	lower = ascii_only.lower()
	replaced = re.sub(r"[^a-z0-9]+", "-", lower)
	return replaced.strip("-")


def provider_slug_from_url(url: str) -> str:
	"""Infer a provider slug from the event host (e.g. ``www.xkrsports.com.br`` → ``xkrsports``)."""
	try:
		host = (urlparse(url).hostname or "").lower()
	except ValueError:
		return ""
	host = host.removeprefix("www.")
	if not host:
		return ""
	# Use the registrable label: drop the final TLD segments (``.com.br``/``.com``/...).
	parts = host.split(".")
	if len(parts) >= 3 and parts[-2] in {"com", "org", "net", "gov", "edu"} and len(parts[-1]) == 2:
		label = parts[-3]
	elif len(parts) >= 2:
		label = parts[-2]
	else:
		label = parts[0]
	return slugify(label)
