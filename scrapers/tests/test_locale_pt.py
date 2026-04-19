"""Tests for the shared Brazilian Portuguese locale helpers (principle 1.2, §4.3, §4.7)."""

from __future__ import annotations

import pytest

from running_calendar_scrapers.locale_pt import (
	EN_MONTH_ABBR,
	PT_MONTH_ABBR,
	PT_MONTH_FULL,
	br_state_uf,
	pt_month_number,
)


def test_en_month_abbr_shape():
	assert len(EN_MONTH_ABBR) == 12
	assert EN_MONTH_ABBR[0] == "Jan"
	assert EN_MONTH_ABBR[11] == "Dec"


def test_pt_month_abbr_completeness():
	assert len(PT_MONTH_ABBR) == 12
	assert set(PT_MONTH_ABBR.values()) == set(range(1, 13))


def test_pt_month_full_completeness():
	assert len(PT_MONTH_FULL) == 12
	assert set(PT_MONTH_FULL.values()) == set(range(1, 13))


@pytest.mark.parametrize(
	"token, expected",
	[
		("jan", 1),
		("Jan", 1),
		("janeiro", 1),
		("Janeiro", 1),
		("fev", 2),
		("fevereiro", 2),
		("mar", 3),
		("Março", 3),
		("marco", 3),
		("março", 3),
		("MARÇO", 3),
		("abr", 4),
		("abril", 4),
		("mai", 5),
		("maio", 5),
		("jun", 6),
		("jul", 7),
		("ago", 8),
		("set", 9),
		("out", 10),
		("nov", 11),
		("dez", 12),
		("dezembro", 12),
		# Whitespace tolerated.
		("  jan  ", 1),
	],
)
def test_pt_month_number_accepts_abbrev_and_full(token, expected):
	assert pt_month_number(token) == expected


@pytest.mark.parametrize("token", ["", "   ", "foo", "xyz", "abc"])
def test_pt_month_number_returns_none_for_garbage(token):
	assert pt_month_number(token) is None


def test_pt_month_number_prefix_matching_matches_legacy_behaviour():
	"""Legacy iguana/yescom code used ``mon_s.lower()[:3]`` as the lookup key.

	Preserving that behaviour means any token whose first 3 letters happen to
	match an abbreviation resolves (e.g. ``"janeir"`` → January). Documented
	here so a future change doesn't tighten the matching by accident.
	"""
	assert pt_month_number("janeir") == 1
	assert pt_month_number("janfoo") == 1


@pytest.mark.parametrize(
	"name, expected",
	[
		("Minas Gerais", "MG"),
		("minas gerais", "MG"),
		("MINAS GERAIS", "MG"),
		("São Paulo", "SP"),
		("sao paulo", "SP"),
		("Rio de Janeiro", "RJ"),
		("Espírito Santo", "ES"),
		("Pará", "PA"),
		("Distrito Federal", "DF"),
	],
)
def test_br_state_uf_accepts_accented_and_normalised(name, expected):
	assert br_state_uf(name) == expected


@pytest.mark.parametrize("name", ["", "   ", "Nowhere", "XY"])
def test_br_state_uf_returns_none_for_unknown(name):
	assert br_state_uf(name) is None
