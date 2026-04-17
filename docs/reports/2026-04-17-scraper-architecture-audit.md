# Scraper architecture audit — 2026-04-17

**Scope.** `scrapers/` package (legacy per-provider scrapers + `ai_scraper/` + orchestration).
**Rubric.** The five principles codified in `.cursor/rules/architecture-principles.mdc` (single responsibility, ports & adapters, dependency inversion, single source of truth, testability / open-closed).
**Method.** Static read of every `.py` file under `scrapers/` and `scrapers/tests/`, cross-referenced against `docs/data-model.md` and the existing cursor rules.

The scrapers ship a working pipeline and reasonable unit tests, but the module layout has accreted and several shared concepts are duplicated or misplaced. None of the gaps below is a blocker; together they explain why writing a fifth scraper, or swapping the LLM backend, currently requires edits in many unrelated files.

## Executive summary

| # | Principle | Severity | Count | Examples |
|---|-----------|----------|-------|----------|
| 1 | Single responsibility per module | **High** | 5 | `iguana.py` mixes 7 concerns; `db_ref.py` hosts test fixtures |
| 2 | Separation of concerns (ports & adapters) | **High** | 4 | no HTTP / DB / LLM / browser ports; tests monkey-patch deep paths |
| 3 | Dependency inversion & explicit configuration | Medium | 3 | four copies of `_session()`; implicit DB connection on every scrape |
| 4 | Single source of truth (DRY) | **High** | 7 | `ScrapedRace` lives in `iguana.py`; two parallel race-row schemas; duplicated month tables |
| 5 | Testability & open-closed extensibility | Medium | 4 | no `Scraper` protocol; unit-unreachable SQL contains a typo (`CALESCE`) |

Net assessment: the package has **one architecturally central module (`iguana.py`)** that every other scraper quietly depends on, and **two parallel contracts for the race row** (legacy `RACES_HEADER` vs `RACE_ROW_KEYS`). Fixing those two items would unlock most of the improvements below with minimal behaviour change.

## Principle 1 — Single responsibility per module

> "A module should have one reason to change."

### 1.1 `iguana.py` mixes seven concerns

`scrapers/running_calendar_scrapers/iguana.py` (290 lines) is simultaneously:

1. the Iguana-specific HTTP fetcher (`_session`, `fetch_race_article`, `CALENDAR_URL`);
2. the Iguana HTML parser (`_parse_event_datetime`, `_parse_location`, `_parse_title`, `_parse_distance_labels`);
3. the canonical race-row **dataclass** `ScrapedRace` (imported by every other scraper);
4. the canonical **CSV header** `RACES_HEADER` (imported by `yescom.py`, `merge_csv.py`);
5. the generic CSV writer `format_races_csv` / reader `parse_races_csv`;
6. a month-token table `_PT_MONTHS` / `_EN_MONTHS`;
7. a CLI `run(argv)`.

Any change to the shared row shape, CSV serialisation, or month handling touches this Iguana-named file, and every other scraper's import graph fans out through it. Recommendation: extract `ScrapedRace`, `RACES_HEADER`, and the CSV helpers to `race_row.py`; keep `iguana.py` provider-specific.

### 1.2 `corre_brasil.py`, `running_land.py`, `yescom.py` replicate the same pattern

Each file is simultaneously HTTP fetcher + parser + DB whitelist loader + CSV serialiser + CLI. The duplicated scaffolding obscures what is provider-specific (parsing) versus generic (session, CSV, validation, CLI).

### 1.3 `db_ref.py` hosts test fixture data

`fixture_km_to_slug_iguana_html_tests()` and `fixture_km_to_slug_corre_brasil_repeater()` ship hard-coded maps for offline HTML fixtures. Test fixtures in a production-DB module are a smell: they change for **test** reasons but live next to functions that change for **schema** reasons. Move to `scrapers/tests/_fixtures.py`.

### 1.4 `supabase_sync.py` smears normalisation into the sync step

`sync_scraped_rows_to_supabase` both opens the transaction (infrastructure) and calls `partition_scraped_races` (pure validation). The "load existing keys" query and the "insert race + distances" transaction are one atomic unit, but the normalisation step is not — it could (and should) be run before any DB connection is opened, so tests of the sync code path do not need a live Postgres.

### 1.5 `run_scrapers.py` couples CLI, module discovery, and sync

`discover_scraper_names()` reaches into the package filesystem with `Path(...).glob("*.py")` and calls `importlib.import_module` as a side effect of listing. A registry-based discovery (each scraper registers itself via an explicit list or entry point) would make the orchestrator dependency-light and typeable.

## Principle 2 — Separation of concerns (ports & adapters)

> "Domain logic must be runnable without a database, a browser, or a network."

### 2.1 No HTTP port

Every scraper imports `requests` directly and builds a `requests.Session` inline. There is no `HttpClient` interface, no retry/back-off policy, no rate-limiter. Tests that want to avoid live HTTP have to monkey-patch the module-level `requests` attribute or patch `fetch_*` deep imports (see `test_iguana_live_optional.py:23`, `test_ai_scraper_pipeline.py:79`). A small `Protocol` (`def get(url: str, *, timeout: int) -> str`) injected into each scraper would enable in-process fakes and shared retry logic.

### 2.2 No reference-data port

Parsers call `load_valid_provider_slugs()` / `load_distance_slugs_by_km()` which each open a **new Postgres connection** in `db_ref._connect`. Consequences:

- A single scrape opens **three** DB connections before the first HTTP request.
- `scrape_corre_brasil_calendar()` cannot run without `RUNNINGCALENDAR_DATABASE_URL`, so offline tests must monkey-patch module globals.

Recommendation: a `ReferenceData` port exposing `km_to_slug`, `valid_types`, `valid_providers` as immutable values; the composition root (CLI entry point) resolves it once and passes it into the scraper.

### 2.3 No LLM port

`ai_scraper/extractor.py` constructs its own `OpenAI` client via `_build_client()` and reads `OPENAI_API_KEY` from `os.environ`. Only the optional `client=` kwarg lets tests stub it out, and the coupling to OpenAI-specific SDK shapes (`chat.completions.create`, `response_format={...}`) leaks into the scraper. A minimal `LLMExtractor.extract(prompt) -> dict` port with `OpenAIChatAdapter` would isolate provider lock-in.

### 2.4 No browser/loader port

`ai_scraper/loader.py::load_via_cypress` shells out via `subprocess.run(["npx", "cypress", …])` directly inside the scraper pipeline. Running tests requires monkey-patching `load_page` at `running_calendar_scrapers.ai_scraper.scraper.load_page` — a well-known code smell that the seam is on the wrong side of the import boundary. A `PageLoader.load(url) -> LoadedPage` protocol with `CypressLoader` / `RequestsLoader` adapters would remove the monkey-patch.

## Principle 3 — Dependency inversion & explicit configuration

> "Functions receive dependencies as arguments; only the composition root reads env vars."

### 3.1 Four copies of `_session()`

`iguana.py:65`, `corre_brasil.py:74`, `running_land.py:53`, `yescom.py:48` each define a private `_session()` with a `USER_AGENT` constant. Three use `RunningCalendarBot/1.0 …` verbatim; `running_land.py` silently uses a **different** Chrome UA because its target's WAF blocks bots. That divergence is invisible from any single file. A shared `make_session(user_agent: str = DEFAULT)` helper would make the override explicit.

### 3.2 `database_url_from_env()` is called from multiple modules

Both `db_ref._connect` and `supabase_sync.sync_scraped_rows_to_supabase` read env vars independently. If the run-time wants to use a pooler for reads and the primary for writes, there is nowhere to express that: the knob is buried inside every consumer. One composition root should resolve the config once and hand typed `psycopg2` connections (or a `Database` object) to anything that needs them.

### 3.3 Scrapers reach into `os.environ` and the filesystem implicitly

`ai_scraper/loader.py::load_via_cypress` mutates `os.environ` and writes a `tempfile` to coordinate with the Cypress spec. This is fine as the private implementation of a `PageLoader` adapter, but with no port it's also the scraper's **public contract**. Pushing the env handling to the adapter hides the side effect from the pipeline.

## Principle 4 — Single source of truth (DRY)

> "Every shared concept is defined once."

### 4.1 `ScrapedRace` and `RACES_HEADER` live in `iguana.py`

The canonical race-row dataclass is defined in a provider-specific module and re-exported across the codebase:

- `corre_brasil.py:14` — `from …iguana import ScrapedRace, format_races_csv`
- `running_land.py:14` — same
- `yescom.py:12` — `from …iguana import RACES_HEADER, ScrapedRace, scraped_to_csv_rows`
- `merge_csv.py:16` — `from …iguana import RACES_HEADER, parse_races_csv`

If Iguana the provider goes away, deleting `iguana.py` becomes impossible. Move to `race_row.py` (or a `_shared/` sub-package).

### 4.2 Two parallel race-row schemas

| Source | Keys | Location |
|--------|------|----------|
| Legacy scrapers | `RACES_HEADER` tuple (9 keys) | `iguana.py:238` |
| AI scraper | `RACE_ROW_KEYS` tuple (9 keys) | `ai_scraper/schema.py:22` |

The two lists are **identical today** but drift-prone: any change has to be mirrored. The AI scraper should import `RACE_ROW_KEYS = RACES_HEADER` (renamed to something provider-neutral), not re-declare it.

### 4.3 Duplicated Portuguese month tables

| File | Identifier | Keys |
|------|-----------|------|
| `iguana.py` | `_PT_MONTHS` | `"jan"`, `"fev"`, … (3-letter abbrevs) |
| `yescom.py` | `_MONTH_TOKEN` | `"jan"`, `"fev"`, … (same) |
| `corre_brasil.py` | `_PT_MONTHS` | `"janeiro"`, `"fevereiro"`, … (full words) |

Three tables for the same concept, with one renamed and one extended. A `pt_month(raw: str) -> int | None` helper in a shared locale module would normalise both spellings.

### 4.4 Duplicated `USER_AGENT`

Four string literals across `iguana.py`, `corre_brasil.py`, `running_land.py`, `yescom.py`, `ai_scraper/loader.py`. See §3.1; the semantic divergence (RunningLand uses a Chrome UA) is the hazard, not the duplication.

### 4.5 Duplicated distance-label heuristics

| Function | Behaviour |
|----------|-----------|
| `iguana._distance_slugs_from_labels` | reject unknown km (raises) |
| `corre_brasil._distance_slugs_from_blob` | silently drop unknown km |
| `running_land._distance_slugs_from_modality_ids` | silently drop unknown km |
| `ai_scraper.distance.normalize_distance_slugs` | accept **any** tenths-of-km value, bypassing the DB whitelist |

Four parsers, four policies about what to do when a km value is not in `public.distances`. The AI scraper's policy is especially divergent: it invents slugs like `3-7km` that might not exist in the reference table, and the downstream inserter would fail. The scraper pipeline has no shared `label → km → validated slug` step.

### 4.6 Hard-coded type-slug whitelist in the AI scraper

`ai_scraper/scraper.py:62` — `if type_slug not in {"road", "trail", "adventure"}: type_slug = "road"`. Legacy scrapers call `load_valid_type_slugs()` against the live DB; this one hard-codes the set. Adding a new type in Supabase requires a code edit here.

### 4.7 Brazilian state-name map only in `corre_brasil.py`

`_BR_STATE_NAME_TO_UF` (26 entries, `corre_brasil.py:22-50`) is a shared Brazilian concept. `running_land.py` and `yescom.py` parse state tokens with different, weaker heuristics (`len(token) == 2 and token.isalpha()`). Move to a neutral `br_locale.py` so all three scrapers and the AI post-processor can normalise `"Minas Gerais"` identically.

## Principle 5 — Testability and open-closed extensibility

> "Adding a new scraper, loader, or extractor should not require editing the orchestrator."

### 5.1 No `Scraper` protocol

`run_scrapers.py:50` discovers scrapers by filesystem glob and calls `getattr(mod, "run", None)`. The orchestrator has **no typed interface** to talk to: `run(argv)` takes an `argv` list and returns a string CSV, with behaviour contractually defined only in prose. A `Protocol`:

```python
class Scraper(Protocol):
    name: str
    def scrape(self, *, year: int, session: HttpClient, ref: ReferenceData) -> list[ScrapedRace]: ...
```

… would make `run_scrapers.py` dependency-light, testable without `importlib`, and refuse to register a malformed scraper at startup.

### 5.2 Tests monkey-patch deep attribute paths

`test_ai_scraper_pipeline.py:79` patches `"running_calendar_scrapers.ai_scraper.scraper.load_page"`. `test_iguana_live_optional.py:23` imports `db_ref` via `__import__(…)` to call `load_distance_slugs_by_km`. Both indicate the seam is on the wrong side of the module boundary: the scraper should accept a `PageLoader` argument, and ref-data should be a parameter, not a module-level import.

### 5.3 Unreachable DB code hides a real bug (observable symptom)

`db_ref.py:103` contains a SQL typo: `CALESCE(...)` instead of `COALESCE(...)`. The function `load_races_for_provider` is only called from `test_iguana_vs_database.py` and `test_iguana_live_optional.py`, both of which are live-DB tests (skipped without `RUNNINGCALENDAR_DATABASE_URL`). Because there is no unit-level seam (the function takes no injectable connection and opens its own `psycopg2.connect`), no offline test runs it, and the typo has survived commit. This is exactly the class of defect principle 5 is designed to prevent: untestable code rots silently. Fix the typo, and add a unit test that passes a fake cursor with a canned row set.

### 5.4 Open/closed violation on the race-row shape

Adding one column (e.g. `endDate`) to the row requires edits in **five** places that do not reference each other directly:

1. `iguana.py::ScrapedRace` dataclass,
2. `iguana.py::RACES_HEADER` tuple,
3. `iguana.py::scraped_to_csv_rows`,
4. `supabase_sync.py` `INSERT` SQL,
5. `merge_csv.py::normalize_race_row` (per-key normalisation).

Plus `ai_scraper/schema.py::RACE_ROW_KEYS` and the JSON schema. A single `RaceRow` definition with field metadata (e.g. `Field(normalize=lambda s: s.strip())`) driven off a typed dataclass would collapse these five edits into one.

## Recommended remediation order

These are ordered by value-to-effort (not by severity), with cross-references to the principles above:

1. **Extract `race_row.py`** — move `ScrapedRace`, `RACES_HEADER`, `RACE_ROW_KEYS`, `format_races_csv`, `parse_races_csv`, `scraped_to_csv_rows` into a neutral module (addresses §1.1, §4.1, §4.2). Low-risk rename.
2. **Introduce three ports** (`HttpClient`, `ReferenceData`, `PageLoader`) in a `ports.py` module; default adapters keep current behaviour (§2.1, §2.2, §2.4). Medium effort, high payoff on testability.
3. **Fix `CALESCE` → `COALESCE` in `db_ref.py:103`** and add a fake-cursor unit test (§5.3). Five-minute fix; visible-quality win.
4. **Shared locale module** for Portuguese months and Brazilian-state UF mapping (§4.3, §4.7). Removes drift risk.
5. **Define `Scraper` protocol and an explicit registry** in `run_scrapers.py` (§1.5, §5.1). Typed orchestration replaces filesystem discovery.
6. **Pull hard-coded type whitelist and `country="Brasil"` default** out of `ai_scraper/scraper.py::_postprocess` (§4.6). Replace with injected `ReferenceData`.

## What already looks good

- `docs/data-model.md` is a genuine single source of truth for the wire shape — respected by every scraper's output keys.
- `merge_csv.py::partition_scraped_races` is a clean pure function: take `(new_rows, existing_keys)` and return `(to_add, dups, skips)`. That is the right shape; it just needs to live in a module that does **only** normalisation (no cross-imports into `iguana.py`).
- The AI scraper's post-processing is already testable end-to-end via an injected client (see `test_ai_scraper_pipeline.py`). Generalising that pattern to the legacy scrapers is the unlock.

## Appendix — file-to-principle map

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
