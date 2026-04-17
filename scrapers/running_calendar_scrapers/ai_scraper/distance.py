"""Helpers to normalise the distance slug list returned by the LLM.

Follows the slug conventions in ``docs/slug-conventions.md`` (``^[a-z0-9]+(-[a-z0-9]+)*$``)
and the tenths-of-a-kilometre encoding used by ``public.distances.km``.
"""

from __future__ import annotations

import re

_KM_NUMBER = re.compile(r"^(\d+(?:[\.,]\d+)?)$")


def _km_to_slug(km: float) -> str | None:
	"""Convert a kilometre value to its canonical distance slug, or ``None``.

	- Whole kilometres render as ``<n>km`` (e.g. ``10`` → ``10km``).
	- Fractional kilometres render as ``<int>-<tenths>km`` (e.g. ``21.1`` → ``21-1km``).
	- Values that cannot be expressed in tenths of a km cleanly return ``None``.
	"""
	if km <= 0:
		return None
	tenths = round(km * 10)
	if abs(tenths - km * 10) > 1e-6:
		return None
	if tenths % 10 == 0:
		return f"{tenths // 10}km"
	whole = tenths // 10
	frac = tenths % 10
	return f"{whole}-{frac}km"


def normalize_distance_token(raw: str) -> str | None:
	"""Normalise a single distance token returned by the model.

	Accepts plain numeric strings (``"5"``, ``"21.1"``, ``"21,1"``), numbers with a
	``km`` suffix (``"5km"``, ``"21.1 km"``), and already-normalised slugs
	(``"21-1km"``, ``"10km"``). Returns ``None`` for unrecognised input such as
	``"kids"`` or free-text labels.
	"""
	t = (raw or "").strip().lower().replace(" ", "")
	if not t:
		return None

	if re.fullmatch(r"\d+(?:-\d+)?km", t):
		return t
	if t in {"kids-run", "kids", "kidsrun"}:
		return "kids-run"

	t_no_km = t.removesuffix("km").removesuffix("k")
	m = _KM_NUMBER.match(t_no_km)
	if not m:
		return None
	try:
		km = float(m.group(1).replace(",", "."))
	except ValueError:
		return None
	return _km_to_slug(km)


def normalize_distance_slugs(raw_list: str) -> str:
	"""Normalise a ``;``/``,``-separated distance blob to canonical slugs.

	Returns a ``;``-separated string sorted by kilometre order. Unknown tokens
	are dropped silently; duplicate slugs are collapsed.
	"""
	if not raw_list:
		return ""
	# Convert Portuguese decimal commas (e.g. '21,1km') to dots so ','-splitting
	# does not turn '21,1' into '21' and '1'. Standalone commas between tokens
	# (``5km, 10km``) are preserved as list separators.
	normalised = re.sub(r"(?<=\d),(?=\d)", ".", raw_list)
	parts = re.split(r"[;,]", normalised)
	slugs: list[str] = []
	for part in parts:
		slug = normalize_distance_token(part)
		if slug and slug not in slugs:
			slugs.append(slug)

	def _sort_key(slug: str) -> tuple[int, int]:
		if slug == "kids-run":
			return (0, 0)
		m = re.fullmatch(r"(\d+)(?:-(\d+))?km", slug)
		if not m:
			return (10**9, 0)
		whole = int(m.group(1))
		frac = int(m.group(2) or 0)
		return (whole, frac)

	slugs.sort(key=_sort_key)
	return ";".join(slugs)
