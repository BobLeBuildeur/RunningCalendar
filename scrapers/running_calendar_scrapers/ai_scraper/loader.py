"""Render a target URL and extract page text + main-body image URLs.

Preferred path: invoke the bundled Cypress spec
(``cypress/e2e/ai_scraper_fetch.cy.ts``) so JS-heavy race sites render before
scraping. Falls back to a plain ``requests`` fetch when Cypress or ``npx`` are
unavailable (CI/dev containers without a browser).

All captured data is returned as a :class:`LoadedPage` dataclass to keep the
rest of the pipeline loader-agnostic.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"


@dataclass(frozen=True)
class LoadedPage:
	"""Structured snapshot of a target page used by the extractor.

	- ``url``: Canonical event URL (echoed from the caller).
	- ``title``: ``document.title`` or ``<title>`` content; may be empty.
	- ``text``: Readable text content extracted from the page body (whitespace
	  collapsed; scripts/styles removed).
	- ``html``: Raw HTML captured from the rendered page (useful for debugging).
	- ``images``: Absolute URLs of ``<img>`` elements within the main body,
	  already de-duplicated in document order. Intended for the vision fallback.
	"""

	url: str
	title: str
	text: str
	html: str
	images: tuple[str, ...]


def _cypress_project_root() -> Path:
	"""Repo root that contains ``cypress.config.ts``."""
	return Path(__file__).resolve().parents[3]


def _cypress_available() -> bool:
	"""True when ``npx`` is on PATH and Cypress is installed in the workspace."""
	if not shutil.which("npx"):
		return False
	cypress_bin = _cypress_project_root() / "node_modules" / ".bin" / "cypress"
	return cypress_bin.exists()


def _clean_text(html: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
		tag.decompose()
	text = soup.get_text(" ", strip=True)
	return re.sub(r"\s+", " ", text).strip()


def _extract_images(html: str, base_url: str) -> list[str]:
	soup = BeautifulSoup(html, "html.parser")
	main = soup.select_one("main, article, [role=main], #content, #main")
	scope = main if main else soup
	seen: list[str] = []
	for img in scope.select("img"):
		src = (img.get("src") or img.get("data-src") or "").strip()
		if not src or src.startswith("data:"):
			continue
		absolute = urljoin(base_url, src)
		try:
			parsed = urlparse(absolute)
		except ValueError:
			continue
		if parsed.scheme not in {"http", "https"}:
			continue
		if absolute not in seen:
			seen.append(absolute)
	return seen


def _title(html: str) -> str:
	soup = BeautifulSoup(html, "html.parser")
	t = soup.title
	if t and t.string:
		return t.string.strip()
	h1 = soup.find("h1")
	if h1:
		return h1.get_text(" ", strip=True)
	return ""


def load_via_requests(url: str, *, timeout: int = 30) -> LoadedPage:
	"""Render via an ``HTTP GET``; use for environments without a browser."""
	resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
	resp.raise_for_status()
	if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
		resp.encoding = resp.apparent_encoding
	html = resp.text
	return LoadedPage(
		url=url,
		title=_title(html),
		text=_clean_text(html),
		html=html,
		images=tuple(_extract_images(html, url)),
	)


def load_via_cypress(url: str, *, timeout: int = 120) -> LoadedPage:
	"""Render the URL inside headless Cypress and capture DOM + images.

	Writes a JSON snapshot to ``ai_scraper_snapshot.json`` in a temporary
	directory that the Cypress spec is told about via the ``TARGET_URL`` and
	``SNAPSHOT_PATH`` environment variables.
	"""
	if not _cypress_available():
		raise RuntimeError("Cypress is not installed; run `npm install` in the repo root")

	project_root = _cypress_project_root()
	spec = project_root / "cypress" / "e2e" / "ai_scraper_fetch.cy.ts"
	if not spec.exists():
		raise RuntimeError(f"Cypress spec missing: {spec}")

	with tempfile.TemporaryDirectory(prefix="ai_scraper_") as tmp:
		snapshot = Path(tmp) / "snapshot.json"
		env = {
			**os.environ,
			"TARGET_URL": url,
			"SNAPSHOT_PATH": str(snapshot),
			# Skip the default base-url check so we can hit any external site.
			"CYPRESS_baseUrl": "http://127.0.0.1",
		}
		cmd = [
			"npx",
			"cypress",
			"run",
			"--quiet",
			"--browser",
			"chrome",
			"--spec",
			str(spec),
			"--config",
			"video=false,screenshotOnRunFailure=false",
		]
		proc = subprocess.run(
			cmd,
			cwd=str(project_root),
			env=env,
			capture_output=True,
			text=True,
			timeout=timeout,
			check=False,
		)
		if not snapshot.exists():
			stderr = (proc.stderr or "")[-4000:]
			stdout = (proc.stdout or "")[-1000:]
			raise RuntimeError(
				f"Cypress did not produce a snapshot (exit={proc.returncode}).\n"
				f"stdout tail: {stdout}\nstderr tail: {stderr}",
			)
		data = json.loads(snapshot.read_text(encoding="utf-8"))

	html = data.get("html") or ""
	title = data.get("title") or _title(html)
	images_raw = data.get("images") or []
	images: list[str] = []
	for src in images_raw:
		if not isinstance(src, str) or not src or src.startswith("data:"):
			continue
		absolute = urljoin(url, src)
		if urlparse(absolute).scheme in {"http", "https"} and absolute not in images:
			images.append(absolute)
	return LoadedPage(
		url=url,
		title=title,
		text=_clean_text(html),
		html=html,
		images=tuple(images),
	)


def load_page(url: str, *, prefer: str = "auto") -> LoadedPage:
	"""Render ``url`` using Cypress when available, or fall back to ``requests``.

	``prefer`` accepts ``"auto"`` (default — Cypress if installed, else
	requests), ``"cypress"`` (hard fail without Cypress), or ``"requests"``
	(skip the browser entirely).
	"""
	if prefer == "requests":
		return load_via_requests(url)
	if prefer == "cypress":
		return load_via_cypress(url)
	if _cypress_available():
		try:
			return load_via_cypress(url)
		except Exception:
			# Fall back so the CLI remains usable in headless CI environments.
			pass
	return load_via_requests(url)


def iter_main_body_images(page: LoadedPage, *, limit: int = 4) -> Iterable[str]:
	"""Yield up to ``limit`` image URLs in document order; used by the vision fallback."""
	for i, src in enumerate(page.images):
		if i >= limit:
			break
		yield src
