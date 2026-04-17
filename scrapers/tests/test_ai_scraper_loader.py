"""Offline tests for the loader's HTML cleaning + image discovery."""

from __future__ import annotations

from pathlib import Path

from running_calendar_scrapers.ai_scraper.loader import (
	_clean_text,
	_extract_images,
	_title,
	iter_main_body_images,
	LoadedPage,
)


_FIXTURES = Path(__file__).parent / "fixtures" / "ai_scraper"


def test_clean_text_drops_scripts_and_collapses_whitespace():
	html = "<html><body><script>x=1</script><p>Hello    world</p></body></html>"
	assert _clean_text(html) == "Hello world"


def test_extract_images_absolute_and_dedup():
	html = (_FIXTURES / "tom_jerry.html").read_text(encoding="utf-8")
	imgs = _extract_images(html, "https://www.yescom.com.br/corridatomejerry/2026/index.asp")
	assert imgs == ["https://www.yescom.com.br/img/banner.jpg"]


def test_title_prefers_title_tag():
	html = "<html><head><title>Hi</title></head><body><h1>Other</h1></body></html>"
	assert _title(html) == "Hi"


def test_iter_main_body_images_limit():
	page = LoadedPage(
		url="https://example.com",
		title="",
		text="",
		html="",
		images=tuple(f"https://example.com/{i}.jpg" for i in range(10)),
	)
	assert list(iter_main_body_images(page, limit=3)) == [
		"https://example.com/0.jpg",
		"https://example.com/1.jpg",
		"https://example.com/2.jpg",
	]
