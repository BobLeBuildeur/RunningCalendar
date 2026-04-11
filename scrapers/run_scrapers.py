#!/usr/bin/env python3
"""Run scrapers and print CSV to stdout (for CI or local inspection).

Each scrapper is a module ``running_calendar_scrapers/<name>.py`` defining
``run(argv: list[str] | None = None) -> str`` returning CSV text. Modules are
discovered by filename (see ``list`` command).

Examples::

	python3 run_scrapers.py list
	python3 run_scrapers.py run iguana
	python3 run_scrapers.py run iguana yescom
	python3 run_scrapers.py run all
	python3 run_scrapers.py run yescom --yescom-year 2026

Legacy (same as ``run``)::

	python3 run_scrapers.py iguana yescom
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path


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
		"--yescom-year",
		type=int,
		default=2026,
		help="Forwarded to scrapers that support it (e.g. yescom); others ignore it",
	)

	args = parser.parse_args(argv[1:])

	if args.command == "list":
		for name in available:
			print(name)
		return

	names = _expand_scraper_args(args.scrapers, available)
	extra = ["--yescom-year", str(args.yescom_year)]
	sep = "\n---\n"
	for i, name in enumerate(names):
		mod = importlib.import_module(f"running_calendar_scrapers.{name}")
		text = getattr(mod, "run")(extra)
		if i > 0:
			sys.stdout.write(sep)
		sys.stdout.write(text)


if __name__ == "__main__":
	main()
