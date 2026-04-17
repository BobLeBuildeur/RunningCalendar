"""Explicit registry of provider scrapers.

Replaces the previous filesystem-glob + ``importlib`` + ``getattr`` discovery
in ``run_scrapers.py``. The orchestrator now talks to a typed :class:`Scraper`
protocol via a curated registry, so:

- Adding a new scraper is an explicit edit to ``SCRAPER_ENTRIES`` below —
  the orchestrator refuses to register a module that does not satisfy the
  :class:`Scraper` protocol.
- Tests can enumerate and exercise scrapers without walking the filesystem.
- ``python3 run_scrapers.py list`` is deterministic (no ordering surprises
  from ``Path.glob``) and does not import modules as a side effect of
  listing.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §5.1.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class Scraper(Protocol):
	"""Contract every scraper module must satisfy.

	A scraper is a Python module that exposes a callable named ``run``
	accepting an optional ``argv`` list and returning a CSV string with the
	shared :data:`running_calendar_scrapers.race_row.RACES_HEADER` columns.
	"""

	def run(self, argv: list[str] | None = None) -> str: ...  # pragma: no cover


RunCallable = Callable[[list[str] | None], str]


@dataclass(frozen=True)
class ScraperEntry:
	"""One registered scraper: CLI ``name`` + the dotted module that hosts ``run``."""

	name: str
	module: str

	def load_run(self) -> RunCallable:
		"""Import the module and return its ``run`` callable.

		Raises ``RuntimeError`` if the module does not satisfy :class:`Scraper`.
		"""
		mod = importlib.import_module(self.module)
		run = getattr(mod, "run", None)
		if not callable(run):
			raise RuntimeError(
				f"Scraper {self.name!r} ({self.module}) does not expose a callable 'run'",
			)
		return run


# NOTE: extend this list when adding a new scraper. The orchestrator does not
# walk the filesystem, so a new module with a ``run()`` function is NOT picked
# up automatically — this is intentional (open/closed + auditability).
SCRAPER_ENTRIES: tuple[ScraperEntry, ...] = (
	ScraperEntry(name="corre_brasil", module="running_calendar_scrapers.corre_brasil"),
	ScraperEntry(name="iguana", module="running_calendar_scrapers.iguana"),
	ScraperEntry(name="running_land", module="running_calendar_scrapers.running_land"),
	ScraperEntry(name="yescom", module="running_calendar_scrapers.yescom"),
)

_REGISTRY: dict[str, ScraperEntry] = {e.name: e for e in SCRAPER_ENTRIES}


def available_scrapers() -> list[str]:
	"""Names of every registered scraper, in stable alphabetical order."""
	return sorted(_REGISTRY.keys())


def get_scraper(name: str) -> ScraperEntry:
	"""Return the registry entry for ``name`` or raise ``KeyError``."""
	try:
		return _REGISTRY[name]
	except KeyError as exc:
		available = ", ".join(available_scrapers()) or "(none)"
		raise KeyError(
			f"Unknown scraper {name!r}. Available: {available}. "
			"Add an entry to SCRAPER_ENTRIES in scraper_registry.py.",
		) from exc


def expand_scraper_names(names: list[str]) -> list[str]:
	"""Resolve ``all`` and validate user-supplied scraper names.

	Preserves the legacy CLI semantics: ``all`` expands to every registered
	scraper in :func:`available_scrapers` order, duplicates are removed, and
	unknown names raise :class:`KeyError` with a helpful message.
	"""
	available = available_scrapers()
	available_set = set(available)
	out: list[str] = []
	for n in names:
		if n == "all":
			for a in available:
				if a not in out:
					out.append(a)
			continue
		if n not in available_set:
			get_scraper(n)  # raises with formatted message
		if n not in out:
			out.append(n)
	return out


__all__ = [
	"Scraper",
	"ScraperEntry",
	"SCRAPER_ENTRIES",
	"available_scrapers",
	"expand_scraper_names",
	"get_scraper",
]
