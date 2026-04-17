#!/usr/bin/env python3
"""Run scrapers and print CSV to stdout (for CI or local inspection).

Each scrapper is a module ``running_calendar_scrapers/<name>.py`` defining
``run(argv: list[str] | None = None) -> str`` returning CSV text. Modules are
discovered by filename (see ``list`` command).

Use ``--save-to`` to insert scraped races into **Supabase** (``public.races`` and
``race_distances``): rows are normalized against ``public.distances``, ``public.types``,
and ``public.providers``, duplicates by ``detail_url`` skipped (reported on stdout).
Requires ``RUNNINGCALENDAR_DATABASE_URL``, ``DATABASE_URL``, or ``SUPABASE_DB_URL``
(PostgreSQL URI, e.g. from Supabase).

Examples::

	python3 run_scrapers.py list
	python3 run_scrapers.py run iguana
	python3 run_scrapers.py run iguana yescom
	python3 run_scrapers.py run all
	python3 run_scrapers.py run yescom --year 2026
	python3 run_scrapers.py run iguana --save-to

Legacy (same as ``run``)::

	python3 run_scrapers.py iguana yescom
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

from running_calendar_scrapers.db_ref import repo_root
from running_calendar_scrapers.race_row import parse_races_csv
from running_calendar_scrapers.supabase_sync import sync_scraped_rows_to_supabase


def _package_dir() -> Path:
	return Path(__file__).resolve().parent / "running_calendar_scrapers"


def discover_scraper_names() -> list[str]:
	"""Return module stems under ``running_calendar_scrapers`` that define ``run``."""
	names: list[str] = []
	for path in sorted(_package_dir().glob("*.py")):
		if path.name == "__init__.py" or path.name.startswith("_"):
			continue
		mod = importlib.import_module(f"running_calendar_scrapers.{path.stem}")
		if callable(getattr(mod, "run", None)):
			names.append(path.stem)
	return names


def _expand_scraper_args(names: list[str], available: list[str]) -> list[str]:
	"""Resolve ``all`` and validate names."""
	avail_set = set(available)
	out: list[str] = []
	for n in names:
		if n == "all":
			for a in available:
				if a not in out:
					out.append(a)
			continue
		if n not in avail_set:
			raise SystemExit(
				f"Unknown scraper {n!r}. Available: {', '.join(available) or '(none)'}. "
				"Use `python3 run_scrapers.py list` to see scrapers.",
			)
		out.append(n)
	return out


def main() -> None:
	argv = sys.argv[:]
	if len(argv) >= 2:
		first = argv[1]
		if first not in ("list", "run", "-h", "--help") and not first.startswith("-"):
			argv = [argv[0], "run", *argv[1:]]

	available = discover_scraper_names()

	parser = argparse.ArgumentParser(description="RunningCalendar data scrapers")
	sub = parser.add_subparsers(dest="command", required=True)

	sub.add_parser("list", help="Print available scraper names (module filenames without .py)")

	p_run = sub.add_parser("run", help="Run one or more scrapers and print CSV to stdout")
	p_run.add_argument(
		"scrapers",
		nargs="+",
		metavar="NAME",
		help="Scraper module name(s), or 'all' for every discovered scraper",
	)
	p_run.add_argument(
		"--year",
		type=int,
		default=2026,
		help="Calendar year for scrapers that need it (e.g. yescom); others ignore it",
	)
	p_run.add_argument(
		"--save-to",
		action="store_true",
		help=(
			"Insert new races into Supabase (public.races + race_distances). "
			"FK validation uses public.distances/types/providers. "
			"Set RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL. "
			"Omit to print CSV to stdout."
		),
	)

	args = parser.parse_args(argv[1:])

	if args.command == "list":
		for name in available:
			print(name)
		return

	names = _expand_scraper_args(args.scrapers, available)
	extra = ["--year", str(args.year)]
	sep = "\n---\n"
	blobs: list[str] = []
	for name in names:
		mod = importlib.import_module(f"running_calendar_scrapers.{name}")
		blobs.append(getattr(mod, "run")(extra))

	if args.save_to:
		new_rows: list[dict[str, str]] = []
		for text in blobs:
			new_rows.extend(parse_races_csv(text))
		try:
			_, log_lines = sync_scraped_rows_to_supabase(new_rows)
		except Exception as e:
			print(f"Supabase sync failed: {e}", file=sys.stderr)
			raise SystemExit(1) from e
		for line in log_lines:
			print(line, file=sys.stdout)
		return

	for i, text in enumerate(blobs):
		if i > 0:
			sys.stdout.write(sep)
		sys.stdout.write(text)


if __name__ == "__main__":
	main()
