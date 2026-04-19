"""Shared HTTP session helpers for scrapers.

Every provider scraper used to declare its own ``USER_AGENT`` constant and
private ``_session()`` factory. That pattern silently drifted: three scrapers
use the ``RunningCalendarBot/1.0 …`` identifier, while Running Land uses a
Chrome UA because its edge/WAF blocks non-browser tokens on GraphQL. With the
constant duplicated four times, the divergence was invisible from any single
file.

This module centralises the bot identifier and exposes :func:`make_session`
so callers can build a :class:`requests.Session` with consistent defaults.
Callers that need a different identifier (Running Land's Chrome UA) pass it
explicitly — the override is now *visible* rather than a copy-paste quirk.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §1.1, §1.2,
§3.1, and §4.4.
"""

from __future__ import annotations

from typing import Mapping

import requests

DEFAULT_USER_AGENT = "RunningCalendarBot/1.0 (+https://github.com/boblebuildeur/RunningCalendar)"
"""Identifier used by scrapers that hit bot-friendly endpoints.

Sites that reject non-browser UAs (currently Running Land) pass an override
when calling :func:`make_session`.
"""


def make_session(
	*,
	user_agent: str = DEFAULT_USER_AGENT,
	extra_headers: Mapping[str, str] | None = None,
) -> requests.Session:
	"""Return a :class:`requests.Session` with the shared defaults applied.

	Parameters
	----------
	user_agent:
		``User-Agent`` header value. Defaults to :data:`DEFAULT_USER_AGENT`.
	extra_headers:
		Additional request headers merged on top of the defaults (e.g.
		``Accept``, ``Referer``, ``Accept-Language``).
	"""
	session = requests.Session()
	session.headers.update({"User-Agent": user_agent})
	if extra_headers:
		session.headers.update(dict(extra_headers))
	return session


__all__ = ["DEFAULT_USER_AGENT", "make_session"]
