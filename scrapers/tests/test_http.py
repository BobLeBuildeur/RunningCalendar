"""Tests for the shared HTTP session helper (principle 1.1, §4.4)."""

from __future__ import annotations

from running_calendar_scrapers.http import DEFAULT_USER_AGENT, make_session


def test_default_user_agent_identifies_bot():
	assert "RunningCalendarBot" in DEFAULT_USER_AGENT
	assert "github.com/boblebuildeur/RunningCalendar" in DEFAULT_USER_AGENT


def test_make_session_sets_default_user_agent():
	session = make_session()
	assert session.headers["User-Agent"] == DEFAULT_USER_AGENT


def test_make_session_accepts_user_agent_override():
	session = make_session(user_agent="Mozilla/5.0 Fake")
	assert session.headers["User-Agent"] == "Mozilla/5.0 Fake"


def test_make_session_merges_extra_headers():
	session = make_session(
		extra_headers={
			"Accept": "application/json",
			"Referer": "https://example.com/",
		}
	)
	assert session.headers["User-Agent"] == DEFAULT_USER_AGENT
	assert session.headers["Accept"] == "application/json"
	assert session.headers["Referer"] == "https://example.com/"


def test_every_scraper_uses_shared_helper():
	"""Guard: scrapers must not re-declare their own USER_AGENT constant.

	This is the drift risk that motivated extracting ``http.make_session``.
	If a new scraper is added that hard-codes a UA, this test will fail.
	"""
	import running_calendar_scrapers.corre_brasil as corre_brasil
	import running_calendar_scrapers.iguana as iguana
	import running_calendar_scrapers.yescom as yescom

	# These three bot-friendly scrapers should not redeclare the constant.
	for module in (iguana, yescom, corre_brasil):
		assert not hasattr(module, "USER_AGENT"), (
			f"{module.__name__} re-declared USER_AGENT; import DEFAULT_USER_AGENT from "
			"running_calendar_scrapers.http instead"
		)
