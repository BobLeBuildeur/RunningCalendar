"""Process-local composition context shared between scrapers.

Lets :mod:`run_scrapers` load :class:`~running_calendar_scrapers.ports.ReferenceData`
**once** (one DB connection, one round-trip) and share it with every scraper
invoked in the same process, instead of each scraper re-querying Postgres.

Scrapers consult the context lazily:

    reference_data = explicit_kwarg or context.get_reference_data() or load_reference_data_from_db()

so individual call sites (including tests) are free to keep passing an explicit
``reference_data`` kwarg. See ``docs/reports/2026-04-17-scraper-architecture-audit.md``
§2.2 and §3.2.
"""

from __future__ import annotations

from running_calendar_scrapers.ports import ReferenceData

_reference_data: ReferenceData | None = None


def set_reference_data(ref: ReferenceData | None) -> None:
	"""Register a process-local :class:`ReferenceData` snapshot, or clear it."""
	global _reference_data
	_reference_data = ref


def get_reference_data() -> ReferenceData | None:
	"""Return the registered snapshot, or ``None`` if no composition root set one."""
	return _reference_data


__all__ = ["get_reference_data", "set_reference_data"]
