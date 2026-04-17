"""CLI for the AI-assisted scraper.

Usage::

	python -m running_calendar_scrapers.ai_scraper <url> [--loader auto|cypress|requests]
		[--format json|csv] [--text-model MODEL] [--vision-model MODEL]

Prints a single structured race row to stdout.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys

from running_calendar_scrapers.ai_scraper.scraper import AIScraperError, scrape_race_with_ai
from running_calendar_scrapers.ai_scraper.schema import RACE_ROW_KEYS


def _format_csv(row: dict[str, str]) -> str:
	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=list(RACE_ROW_KEYS), lineterminator="\n")
	writer.writeheader()
	writer.writerow(row)
	return buf.getvalue()


def main(argv: list[str] | None = None) -> int:
	parser = argparse.ArgumentParser(
		prog="ai_scraper",
		description="Scrape a single race row from an arbitrary running-race URL using OpenAI.",
	)
	parser.add_argument("url", help="Event URL to scrape")
	parser.add_argument(
		"--loader",
		choices=["auto", "cypress", "requests"],
		default="auto",
		help="Page loader preference (default: auto — Cypress if available, requests otherwise)",
	)
	parser.add_argument(
		"--format",
		choices=["json", "csv"],
		default="json",
		help="Output format (default: json)",
	)
	parser.add_argument("--text-model", default=None)
	parser.add_argument("--vision-model", default=None)
	parser.add_argument(
		"--vision-image-limit",
		type=int,
		default=4,
		help="Maximum main-body images forwarded to the vision fallback",
	)
	args = parser.parse_args(argv)

	try:
		result = scrape_race_with_ai(
			args.url,
			prefer_loader=args.loader,
			text_model=args.text_model,
			vision_model=args.vision_model,
			vision_image_limit=args.vision_image_limit,
		)
	except AIScraperError as exc:
		print(f"ai_scraper: {exc}", file=sys.stderr)
		return 2
	except Exception as exc:
		print(f"ai_scraper: unexpected error: {exc}", file=sys.stderr)
		return 1

	if args.format == "csv":
		sys.stdout.write(_format_csv(result.race))
	else:
		payload = {
			"race": result.race,
			"source": result.source,
			"imagesInspected": result.images_inspected,
		}
		sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
	return 0


if __name__ == "__main__":
	sys.exit(main())
