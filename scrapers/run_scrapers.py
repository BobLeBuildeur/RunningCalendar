#!/usr/bin/env python3
"""Run scrapers and print CSV to stdout (for CI or local inspection)."""

from __future__ import annotations

import argparse
import sys

from running_calendar_scrapers.iguana import format_races_csv, scrape_iguana_calendar
from running_calendar_scrapers.yescom import format_yescom_csv, scrape_yescom_calendar


def main() -> None:
	parser = argparse.ArgumentParser(description="RunningCalendar data scrapers")
	parser.add_argument(
		"provider",
		choices=("iguana", "yescom", "all"),
		help="Which scraper to run",
	)
	parser.add_argument(
		"--yescom-year",
		type=int,
		default=2026,
		help="Year parameter for Yescom calendar (default: 2026)",
	)
	args = parser.parse_args()

	if args.provider in ("iguana", "all"):
		races = scrape_iguana_calendar()
		sys.stdout.write(format_races_csv(races))
		if args.provider == "all":
			sys.stdout.write("\n")
	if args.provider == "yescom":
		races = scrape_yescom_calendar(args.yescom_year)
		sys.stdout.write(format_yescom_csv(races))
	if args.provider == "all":
		sys.stdout.write("---YESCOM---\n")
		races = scrape_yescom_calendar(args.yescom_year)
		sys.stdout.write(format_yescom_csv(races))


if __name__ == "__main__":
	main()
