# Scraper architecture audit — 2026-04-17

**Scope.** `scrapers/` package (legacy per-provider scrapers + `ai_scraper/` + orchestration).
**Rubric.** The five principles codified in `.cursor/rules/architecture-principles.mdc` (single responsibility, ports & adapters, dependency inversion, single source of truth, testability / open-closed).
**Method.** Static read of every `.py` file under `scrapers/` and `scrapers/tests/`, cross-referenced against `docs/data-model.md` and the existing cursor rules.

The scrapers ship a working pipeline and reasonable unit tests, but the module layout has accreted and several shared concepts are duplicated or misplaced. None of the gaps below is a blocker; together they explain why writing a fifth scraper, or swapping the LLM backend, currently requires edits in many unrelated files.

## Executive summary

| # | Principle | Severity | Count | Examples |
|---|-----------|----------|-------|----------|
| 1 | Single responsibility per module | **High** | 5 | ✅ resolved — see §1.1–§1.5 |
| 2 | Separation of concerns (ports & adapters) | **High** | 4 | ✅ resolved — see §2.1–§2.4 |
| 3 | Dependency inversion & explicit configuration | Medium | 3 | ✅ resolved — see §3.1–§3.3 |
| 4 | Single source of truth (DRY) | **High** | 7 | ✅ resolved — see §4.1–§4.7 |
| 5 | Testability & open-closed extensibility | Medium | 4 | ✅ resolved — see §5.1–§5.4 |

Original net assessment: the package had **one architecturally central module (`iguana.py`)** that every other scraper quietly depended on, and **two parallel contracts for the race row** (legacy `RACES_HEADER` vs `RACE_ROW_KEYS`). Both items are now resolved via `race_row.py`, `http.py`, and `locale_pt.py`; `iguana.py` is provider-specific again.

## Principle 1 — Single responsibility per module

> "A module should have one reason to change."

> **Status: resolved in this PR.** Each sub-item below now carries a "resolved" note pointing at the commit that addressed it. The original text is preserved for context.

### 1.1 `iguana.py` mixes seven concerns ✅ resolved

Original: `iguana.py` was the HTTP fetcher **and** HTML parser **and** canonical `ScrapedRace` dataclass **and** CSV writer **and** month table **and** CLI.

**Resolution.** Shared concerns extracted to neutral modules: `race_row.py` owns `ScrapedRace`, `RACES_HEADER`, and the CSV helpers (commit `7ef8cba`, part of Principle 5 work); `http.py` owns the session factory and `DEFAULT_USER_AGENT`; `locale_pt.py` owns the Portuguese month / state helpers. `iguana.py` now contains only the Iguana-specific HTTP fetcher, parser, and CLI. Backwards-compatible re-exports remain so existing `from iguana import ...` imports keep working.

### 1.2 `corre_brasil.py`, `running_land.py`, `yescom.py` replicate the same pattern ✅ resolved (scaffolding)

Original: each provider file duplicated HTTP session + month table + locale scaffolding around its parser.

**Resolution.** `http.make_session` and `locale_pt.pt_month_number` / `EN_MONTH_ABBR` / `br_state_uf` collapse the scaffolding duplication; each provider file is now parser + CLI + a one-line `_session()` thin wrapper. Remaining per-provider concerns (DB whitelist loader call, CSV formatting) are delegated via imports rather than re-implemented. Tracking under Principle 2 (reference-data port) for the rest.

### 1.3 `db_ref.py` hosts test fixture data ✅ resolved

Original: `fixture_km_to_slug_iguana_html_tests()` and `fixture_km_to_slug_corre_brasil_repeater()` lived in a production DB module.

**Resolution.** Moved to `scrapers/tests/_fixtures.py` (renamed `km_to_slug_iguana_html_tests` / `km_to_slug_corre_brasil_repeater` — the `fixture_` prefix was redundant once the module itself conveys role). `db_ref.py` is now schema-shaped reference loaders only.

### 1.4 `supabase_sync.py` smears normalisation into the sync step ✅ resolved

Original: `sync_scraped_rows_to_supabase` both opened the psycopg2 transaction and ran normalisation, so the planning logic could only be tested through a live Postgres.

**Resolution.** Extracted `plan_supabase_sync(rows, existing_keys, *, data_dir) -> SupabaseSyncPlan` as a pure function with no DB imports. `sync_scraped_rows_to_supabase` is now the composition root: fetch existing keys → plan → apply plan → commit/rollback. It also accepts an injectable `conn=` kwarg so callers can share a transaction. `tests/test_supabase_sync.py` covers the planner (insert / duplicate / FK skip) and the composition root via a fake DB-API connection (happy path, dup short-circuit, INSERT rollback, empty-rows noop).

### 1.5 `run_scrapers.py` couples CLI, module discovery, and sync ✅ resolved

Original: `discover_scraper_names()` walked `Path.glob("*.py")` and called `importlib.import_module` as a side effect of listing.

**Resolution.** Replaced by the typed `Scraper` Protocol and explicit `SCRAPER_ENTRIES` registry in `scraper_registry.py` (commit `2dd6233`, already covered under Principle 5.1). `run_scrapers.py` now depends on `available_scrapers()` / `expand_scraper_names()` / `get_scraper()` and has no filesystem awareness.

## Principle 2 — Separation of concerns (ports & adapters)

> "Domain logic must be runnable without a database, a browser, or a network."

> **Status: resolved in this PR.** Each sub-item below now carries a "resolved" note pointing at the commit or module that addressed it. The original text is preserved for context.

### 2.1 No HTTP port ✅ resolved

Original: every scraper imported `requests` directly; no typed `HttpClient` interface.

**Resolution.** `ports.HttpClient` Protocol + `RequestsHttpClient` adapter centralise HTTP GET semantics (retry-friendly entry point, one-place handling of Yescom's ISO-8859-1 encoding quirk). Tests can pass any object with `get_text(url, *, timeout)` as an in-process fake. The existing `session: requests.Session | None` scraper kwargs remain as the legacy seam; callers that want a typed HTTP port use `RequestsHttpClient`. Covered by `tests/test_http_client_port.py`.

### 2.2 No reference-data port ✅ resolved

Original: parsers opened three independent Postgres connections (one each for `load_distance_slugs_by_km` / `load_valid_type_slugs` / `load_valid_provider_slugs`) before the first HTTP request.

**Resolution.** `ports.ReferenceData` is a frozen snapshot; `load_reference_data_from_db(conn)` builds it from a **single** connection (injectable). Every provider scraper now accepts `reference_data=`; if omitted it consults the process-wide composition context (`context.py`) first, and only falls back to a live DB query as a last resort. `run_scrapers.main` loads it once per CLI invocation (`run all` now opens one connection instead of `3 × N`). Covered by `tests/test_reference_data.py`.

### 2.3 No LLM port ✅ resolved

Original: `ai_scraper/extractor.py` constructed its own `OpenAI` client and leaked SDK specifics (`chat.completions.create`, `response_format={...}`) into the scraper pipeline.

**Resolution.** `ports.LLMExtractor` Protocol + `OpenAILLMExtractor` default adapter. `scrape_race_with_ai(..., extractor=...)` accepts any object with `extract_from_text` / `extract_from_images` methods. The legacy `client=` / `text_model=` / `vision_model=` kwargs still work as a shim that builds the default adapter. Covered by `tests/test_llm_extractor_port.py`.

### 2.4 No browser/loader port ✅ resolved

Original: `ai_scraper/loader.py::load_via_cypress` shelled out via `subprocess.run(["npx", "cypress", …])` and mutated `os.environ` directly inside the pipeline.

**Resolution.** `ports.PageLoader` Protocol + `RequestsLoader` / `CypressLoader` / `default_page_loader(prefer)` adapters. All subprocess / env-var / tempfile side effects live inside `CypressLoader`; the pipeline only sees `.load(url)`. `scrape_race_with_ai(..., page_loader=...)` accepts either the legacy `(url, prefer) -> LoadedPage` callable or a port instance. Covered by `tests/test_page_loader_port.py`.

## Principle 3 — Dependency inversion & explicit configuration

> "Functions receive dependencies as arguments; only the composition root reads env vars."

> **Status: resolved in this PR.** Each sub-item below now carries a "resolved" note pointing at the commit or module that addressed it. The original text is preserved for context.

### 3.1 Four copies of `_session()` ✅ resolved

Original: `iguana`, `corre_brasil`, `running_land`, `yescom`, and `ai_scraper/loader` each owned a private `_session()` + `USER_AGENT` constant.

**Resolution.** `http.py::make_session` and `DEFAULT_USER_AGENT` own the default; Running Land's Chrome UA is now an **explicit override** (`BROWSER_USER_AGENT` + `extra_headers`) rather than a copy-paste quirk (commit `a20f60e`, cross-referenced under §4.4).

### 3.2 `database_url_from_env()` is called from multiple modules ✅ resolved

Original: `db_ref._connect` and `supabase_sync.sync_scraped_rows_to_supabase` read env vars independently; no composition root resolved the config once.

**Resolution.** The CLI is now the single composition root: it calls `load_reference_data_from_db()` once (one connection, three SELECTs), publishes the resulting `ReferenceData` to `context.py`, and hands the same snapshot to every scraper. `supabase_sync.sync_scraped_rows_to_supabase` already accepts an injectable `conn=` kwarg (from §1.4), so tests and advanced callers can supply a pooled connection without any env-var plumbing. The `database_url_from_env` helper is still the default fallback, but no pipeline code reads it unconditionally.

### 3.3 Scrapers reach into `os.environ` and the filesystem implicitly ✅ resolved

Original: `load_via_cypress` mutated `os.environ` and wrote a `tempfile` inside the scraper pipeline.

**Resolution.** Those side effects are now contained inside the `CypressLoader` adapter (see §2.4). The pipeline only sees `PageLoader.load(url)`; no other scraper code touches `os.environ`, `tempfile`, or `subprocess`.

## Principle 4 — Single source of truth (DRY)

> "Every shared concept is defined once."

> **Status: resolved in this PR.** Each sub-item below now carries a "resolved" note pointing at the commit or section that addressed it. The original text is preserved for context.

### 4.1 `ScrapedRace` and `RACES_HEADER` live in `iguana.py` ✅ resolved

Original: the canonical race-row dataclass lived in a provider-specific module; every other scraper imported from `iguana`.

**Resolution.** Extracted to `race_row.py` in commit `7ef8cba` (see also §5.4). Every provider scraper and `supabase_sync.py` / `merge_csv.py` now import from the neutral module; `iguana.py` re-exports the names for backwards compatibility.

### 4.2 Two parallel race-row schemas ✅ resolved

Original: `RACES_HEADER` (legacy) and `RACE_ROW_KEYS` (AI scraper) were two independent 9-tuples of the same keys.

**Resolution.** `ai_scraper/schema.py` imports `RACE_ROW_KEYS` from `race_row`; both tuples are the same object (guarded by `tests/test_race_row.py::test_single_source_of_truth_for_csv_header`).

### 4.3 Duplicated Portuguese month tables ✅ resolved

Original: three month tables (`_PT_MONTHS` in iguana, `_MONTH_TOKEN` in yescom, `_PT_MONTHS` full-words in corre_brasil).

**Resolution.** Collapsed into `locale_pt.py::pt_month_number(raw)` which accepts abbreviated and full-word forms, with or without diacritics (commit `9c677f7`). Legacy prefix-match semantics preserved, covered by `tests/test_locale_pt.py`.

### 4.4 Duplicated `USER_AGENT` ✅ resolved

Original: four `USER_AGENT` string literals drifted silently between bot-friendly (`RunningCalendarBot/1.0 …`) and Chrome (`running_land`).

**Resolution.** `http.py::DEFAULT_USER_AGENT` and `make_session()` own the default; Running Land's Chrome UA is now an **explicit override** (`BROWSER_USER_AGENT` + `extra_headers`) rather than a copy-paste quirk (commit `a20f60e`). `tests/test_http.py::test_every_scraper_uses_shared_helper` asserts no provider re-declares the constant.

### 4.5 Duplicated distance-label heuristics ✅ resolved

Original: four scrapers implemented the same looks-up / dedupe / sort step with subtly different policies on unknown km. The AI scraper was the worst offender — it could invent slugs like `3-7km` absent from `public.distances`, which would later fail FK validation during `--save-to`.

**Resolution.** New `distance_slugs.py::kms_to_distance_slugs(kms, km_to_slug, *, strict)` centralises the looks-up / dedupe / sort logic. The three provider scrapers now delegate to it (`strict=True` for Iguana, `strict=False` for Corre Brasil and Running Land). `ai_scraper.distance.normalize_distance_slugs` gained an optional `valid_slugs=` whitelist so callers can pass the `public.distances` slug set to drop invented entries. Covered by `tests/test_distance_slugs.py` and `tests/test_ai_scraper_injected_whitelists.py`.

### 4.6 Hard-coded type-slug whitelist in the AI scraper ✅ resolved

Original: `ai_scraper/scraper.py::_postprocess` hard-coded `{road, trail, adventure}` and the `country="Brasil"` default.

**Resolution.** `scrape_race_with_ai()` now accepts `valid_types=`, `valid_distance_slugs=`, and `default_country=` kwargs. When the model produces a type outside the whitelist, the fallback is `road` if present in the whitelist, otherwise the alphabetically-first registered slug (never silent reintroduction of `road`). The legacy `{road, trail, adventure}` set is exported as `DEFAULT_VALID_TYPE_SLUGS` for composition-root callers that need to opt into the historical behaviour. Covered by `tests/test_ai_scraper_injected_whitelists.py`.

### 4.7 Brazilian state-name map only in `corre_brasil.py` ✅ resolved

Original: the 26-entry state-UF map lived only inside `corre_brasil.py`; `running_land.py` and `yescom.py` fell back to weaker heuristics.

**Resolution.** Moved to `locale_pt.py::br_state_uf(raw)`; shares the same NFKD accent-stripping helper as the month table (commit `9c677f7`). Covered by `tests/test_locale_pt.py::test_br_state_uf_accepts_accented_and_normalised`.

## Principle 5 — Testability and open-closed extensibility

> "Adding a new scraper, loader, or extractor should not require editing the orchestrator."

> **Status: resolved in this PR.** Each sub-item below now carries a "resolved" note pointing at the commit that addressed it. The original text is preserved for context.

### 5.1 No `Scraper` protocol ✅ resolved

Original: `run_scrapers.py:50` discovered scrapers by filesystem glob and called `getattr(mod, "run", None)`. The orchestrator had **no typed interface** to talk to.

**Resolution.** `scrapers/running_calendar_scrapers/scraper_registry.py` now defines a runtime-checkable `Scraper` `Protocol` and an explicit `SCRAPER_ENTRIES` registry. `run_scrapers.py` calls `available_scrapers()`, `expand_scraper_names()`, and `get_scraper(name).load_run()` instead of walking `Path(...).glob("*.py")` and `importlib.import_module`. Unknown names raise a `KeyError` with a "Add an entry to `SCRAPER_ENTRIES`" remediation hint. Covered by `tests/test_scraper_registry.py`.

### 5.2 Tests monkey-patch deep attribute paths ✅ resolved (partial)

Original: `test_ai_scraper_pipeline.py:79` patched `"running_calendar_scrapers.ai_scraper.scraper.load_page"`. The seam was on the wrong side of the module boundary.

**Resolution.** `scrape_race_with_ai()` now accepts a `page_loader: PageLoader | None = None` kwarg where `PageLoader = Callable[[str, str], LoadedPage]`. The pipeline tests inject a fake via `page_loader=` and no longer touch `monkeypatch`. `test_iguana_live_optional.py`'s `__import__(...)` call remains (it is an intentionally live / opt-in test) and is tracked separately under principle 2 (no reference-data port).

### 5.3 Unreachable DB code hides a real bug ✅ resolved

Original: `db_ref.py:103` contained `CALESCE(...)` (typo). `load_races_for_provider` opened its own `psycopg2.connect`, so no offline test ran the query.

**Resolution.** Typo fixed to `COALESCE(`. The SQL is extracted to the module-level `_LOAD_RACES_FOR_PROVIDER_SQL` constant, and `load_races_for_provider(provider_slug, *, conn=None)` now takes an optional injectable connection. `tests/test_db_ref_load_races.py` uses a fake DB-API connection to assert (a) the SQL constant contains `COALESCE` and not `CALESCE`, and (b) the row-to-dict projection handles empty `type_slug` and NULL distance aggregation.

### 5.4 Open/closed violation on the race-row shape ✅ resolved

Original: Adding a column required edits in **five** files (`ScrapedRace`, `RACES_HEADER`, `scraped_to_csv_rows`, the `INSERT` SQL, `normalize_race_row`) plus the AI schema.

**Resolution.** `scrapers/running_calendar_scrapers/race_row.py` now owns the shape as a tuple of `RaceRowField` descriptors. `ScrapedRace`, `RACES_HEADER`, `RACE_ROW_KEYS`, the INSERT column list (`RACE_DB_INSERT_COLUMNS`), and the CSV helpers are all derived from that one tuple. `ai_scraper/schema.py` imports `RACE_ROW_KEYS` from `race_row`, `supabase_sync.py` builds its INSERT SQL from `RACE_DB_INSERT_COLUMNS`, and every scraper imports `ScrapedRace`/`format_races_csv` from `race_row` (with `iguana.py` re-exporting for backwards compatibility). A module-level invariant guards against `ScrapedRace` field drift, and `tests/test_race_row.py` asserts the single-source-of-truth property explicitly.

## Recommended remediation order

These are ordered by value-to-effort (not by severity), with cross-references to the principles above:

1. ✅ **Extract `race_row.py`** — `ScrapedRace`, `RACES_HEADER`, `RACE_ROW_KEYS`, `format_races_csv`, `parse_races_csv`, `scraped_to_csv_rows` now live in a neutral module (§1.1, §4.1, §4.2, §5.4).
2. ✅ **Introduce ports** (`HttpClient`, `ReferenceData`, `LLMExtractor`, `PageLoader`) in a `ports.py` module with default adapters — landed in this PR (§2.1, §2.2, §2.3, §2.4).
3. ✅ **Fix `CALESCE` → `COALESCE` in `db_ref.py`** and cover with a fake-cursor unit test (§5.3).
4. ✅ **Shared locale module** for Portuguese months and Brazilian-state UF mapping (§4.3, §4.7) — implemented as `locale_pt.py`.
5. ✅ **Define `Scraper` protocol and an explicit registry** in `run_scrapers.py` (§1.5, §5.1). Typed orchestration replaces filesystem discovery.
6. ✅ **Pull hard-coded type whitelist and `country="Brasil"` default** out of `ai_scraper/scraper.py::_postprocess` (§4.6) — injected via `valid_types=` / `valid_distance_slugs=` / `default_country=` kwargs on `scrape_race_with_ai`.

## What already looks good

- `docs/data-model.md` is a genuine single source of truth for the wire shape — respected by every scraper's output keys.
- `merge_csv.py::partition_scraped_races` is a clean pure function: take `(new_rows, existing_keys)` and return `(to_add, dups, skips)`. That is the right shape; it just needs to live in a module that does **only** normalisation (no cross-imports into `iguana.py`).
- The AI scraper's post-processing is already testable end-to-end via an injected client (see `test_ai_scraper_pipeline.py`). Generalising that pattern to the legacy scrapers is the unlock.

## Appendix — file-to-principle map

This matrix reflects the **original audit state**. See the per-section "resolved" notes above for the current state after this PR.

| File | P1 | P2 | P3 | P4 | P5 |
|------|----|----|----|----|----|
| `iguana.py` | §1.1 | §2.1 | §3.1 | §4.1 §4.3 §4.4 §4.5 | §5.4 |
| `corre_brasil.py` | §1.2 | §2.1 §2.2 | §3.1 | §4.3 §4.4 §4.5 §4.7 | — |
| `running_land.py` | §1.2 | §2.1 §2.2 | §3.1 | §4.3 §4.4 §4.5 | — |
| `yescom.py` | §1.2 | §2.1 §2.2 | §3.1 | §4.3 §4.4 | — |
| `db_ref.py` | §1.3 | §2.2 | §3.2 | — | §5.3 |
| `supabase_sync.py` | §1.4 | §2.2 | §3.2 | — | — |
| `merge_csv.py` | — | — | — | §4.5 | §5.4 |
| `run_scrapers.py` | §1.5 | — | — | — | §5.1 |
| `ai_scraper/loader.py` | — | §2.4 | §3.3 | §4.4 | §5.2 |
| `ai_scraper/extractor.py` | — | §2.3 | §3.3 | — | §5.2 |
| `ai_scraper/scraper.py` | — | §2.3 §2.4 | — | §4.2 §4.6 | §5.4 |

---

*Report generated 2026-04-17 by an automated architecture review against `.cursor/rules/architecture-principles.mdc`.*
