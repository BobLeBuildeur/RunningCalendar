"""Shared PostgreSQL connection settings (Supabase session URI from env)."""

from __future__ import annotations

import os


def database_url_from_env() -> str:
	"""Return connection URI from env (same keys as Node ``calendarDb``)."""
	for key in ("RUNNINGCALENDAR_DATABASE_URL", "DATABASE_URL", "SUPABASE_DB_URL"):
		v = (os.environ.get(key) or "").strip()
		if v:
			return v
	raise RuntimeError(
		"Set RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL to a PostgreSQL connection URI "
		"(e.g. Supabase session mode: postgresql://postgres.[ref]:[password]@...:5432/postgres).",
	)
