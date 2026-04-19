"""Shared Brazilian Portuguese locale helpers for scrapers.

Before this module there were three independent Portuguese month tables:

- ``iguana.py::_PT_MONTHS`` — 3-letter abbreviations (``jan``, ``fev``, …).
- ``yescom.py::_MONTH_TOKEN`` — same 3-letter abbreviations, different name.
- ``corre_brasil.py::_PT_MONTHS`` — full-word forms (``janeiro``, ``fevereiro``, …)
  with a one-off ``marco`` fallback for the accented ``março``.

Plus a Brazilian state-name → UF map that only lived in ``corre_brasil.py``,
while Yescom and Running Land fell back to weaker ``len == 2 and isalpha``
heuristics to pick up a state token.

The helpers below expose one normalised view of each concept:

- :func:`pt_month_number` accepts abbreviated or full Portuguese month tokens,
  with or without diacritics, and returns ``1..12`` or ``None``.
- :data:`EN_MONTH_ABBR` is the canonical English 3-letter tuple used for
  human-readable display strings.
- :func:`br_state_uf` maps a Brazilian state name (``"Minas Gerais"``,
  ``"sao paulo"``) to its 2-letter UF (``"MG"``, ``"SP"``) or ``None``.

See ``docs/reports/2026-04-17-scraper-architecture-audit.md`` §1.2, §4.3, §4.7.
"""

from __future__ import annotations

import unicodedata

__all__ = [
	"EN_MONTH_ABBR",
	"PT_MONTH_ABBR",
	"PT_MONTH_FULL",
	"br_state_uf",
	"normalize_pt_token",
	"pt_month_number",
]


EN_MONTH_ABBR: tuple[str, ...] = (
	"Jan",
	"Feb",
	"Mar",
	"Apr",
	"May",
	"Jun",
	"Jul",
	"Aug",
	"Sep",
	"Oct",
	"Nov",
	"Dec",
)
"""English 3-letter month abbreviations indexed ``EN_MONTH_ABBR[month - 1]``."""


PT_MONTH_ABBR: dict[str, int] = {
	"jan": 1,
	"fev": 2,
	"mar": 3,
	"abr": 4,
	"mai": 5,
	"jun": 6,
	"jul": 7,
	"ago": 8,
	"set": 9,
	"out": 10,
	"nov": 11,
	"dez": 12,
}
"""Portuguese 3-letter month abbreviations → 1-indexed month number."""


PT_MONTH_FULL: dict[str, int] = {
	"janeiro": 1,
	"fevereiro": 2,
	"marco": 3,  # normalised from "março" via NFKD + accent stripping
	"abril": 4,
	"maio": 5,
	"junho": 6,
	"julho": 7,
	"agosto": 8,
	"setembro": 9,
	"outubro": 10,
	"novembro": 11,
	"dezembro": 12,
}
"""Portuguese full-word months (accent-stripped) → 1-indexed month number."""


def normalize_pt_token(raw: str) -> str:
	"""Lowercase, trim, and strip diacritics from a Portuguese token."""
	stripped = unicodedata.normalize("NFKD", (raw or "").strip().lower())
	return "".join(ch for ch in stripped if not unicodedata.combining(ch))


def pt_month_number(raw: str) -> int | None:
	"""Return 1..12 for a Portuguese month token, or ``None``.

	Accepts abbreviated (``"jan"``, ``"Dez"``) and full-word (``"janeiro"``,
	``"Março"``) forms, case-insensitive, with or without diacritics. Also
	tolerates the common ``"marco"`` misspelling (accent stripped).
	"""
	token = normalize_pt_token(raw)
	if not token:
		return None
	if token in PT_MONTH_FULL:
		return PT_MONTH_FULL[token]
	short = token[:3]
	return PT_MONTH_ABBR.get(short)


_BR_STATE_NAME_TO_UF: dict[str, str] = {
	"acre": "AC",
	"alagoas": "AL",
	"amapa": "AP",
	"amazonas": "AM",
	"bahia": "BA",
	"ceara": "CE",
	"distrito federal": "DF",
	"espirito santo": "ES",
	"goias": "GO",
	"maranhao": "MA",
	"mato grosso": "MT",
	"mato grosso do sul": "MS",
	"minas gerais": "MG",
	"para": "PA",
	"paraiba": "PB",
	"parana": "PR",
	"pernambuco": "PE",
	"piaui": "PI",
	"rio de janeiro": "RJ",
	"rio grande do norte": "RN",
	"rio grande do sul": "RS",
	"rondonia": "RO",
	"roraima": "RR",
	"santa catarina": "SC",
	"sao paulo": "SP",
	"sergipe": "SE",
	"tocantins": "TO",
}


def br_state_uf(raw: str) -> str | None:
	"""Return the 2-letter UF for a Brazilian state name, or ``None``.

	Matching is case-insensitive and tolerates diacritics (``"São Paulo"``
	resolves to ``"SP"``).
	"""
	token = normalize_pt_token(raw)
	if not token:
		return None
	return _BR_STATE_NAME_TO_UF.get(token)
