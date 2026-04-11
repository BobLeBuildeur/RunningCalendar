#!/usr/bin/env python3
"""Run scrapers and print CSV to stdout (for CI or local inspection).

Each scrapper is a module ``running_calendar_scrapers/<name>.py`` defining
``run(argv: list[str] | None = None) -> str`` returning CSV text. Modules are
discovered by filename (see ``list`` command).

Use ``--save-to`` to merge scraper output into ``src/data/races.csv`` (or a given
path): rows are normalized, duplicates skipped (reported on stdout), new rows appended.

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

from running_calendar_scrapers.csv_io import repo_root
from running_calendar_scrapers.iguana import parse_races_csv
from running_calendar_scrapers.merge_csv import load_races_csv_file, merge_new_races, write_races_csv


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
	default_races = repo_root() / "src/data/races.csv"
	p_run.add_argument(
		"--save-to",
		nargs="?",
		type=Path,
		default=None,
		const=default_races,
		metavar="PATH",
		help=(
			"Merge scraped races into this CSV (default: <repo>/src/data/races.csv). "
			"Normalizes rows, skips duplicates (prints notice). Omit to print CSV to stdout."
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

	if args.save_to is not None:
		out_path = args.save_to.resolve()
		data_dir = out_path.parent
		new_rows: list[dict[str, str]] = []
		for text in blobs:
			new_rows.extend(parse_races_csv(text))
		existing = load_races_csv_file(out_path)
		combined, dups, skips = merge_new_races(new_rows, existing, data_dir=data_dir)
		for msg in dups:
			print(msg, file=sys.stdout)
		for msg in skips:
			print(msg, file=sys.stdout)
		added = len(combined) - len(existing)
		if added == 0:
			print(f"No new rows; left {out_path} unchanged ({len(existing)} row(s)).", file=sys.stdout)
			return
		write_races_csv(out_path, combined)
		print(f"Wrote {out_path} ({added} new row(s), {len(combined)} total).", file=sys.stdout)
		return

	for i, text in enumerate(blobs):
		if i > 0:
			sys.stdout.write(sep)
		sys.stdout.write(text)


if __name__ == "__main__":
	main()
