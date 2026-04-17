# AI-assisted race scraper

A programmatic Python tool for extracting a single race row from an arbitrary running-race web page using the OpenAI Chat Completions API. Intended for sites whose markup is inconsistent enough that a bespoke HTML scraper would be brittle.

The tool returns a single flat race row matching the `docs/data-model.md` contract (`sortKey`, `city`, `state`, `country`, `name`, `typeSlug`, `distanceSlugs`, `providerSlug`, `detailUrl`) so its output is interchangeable with the existing scrapers under `scrapers/running_calendar_scrapers/`.

## How it works

1. **Loader** — renders the target URL. Tries Cypress (headless Chrome) first via the `cypress/e2e/ai_scraper_fetch.cy.ts` spec, which captures the rendered DOM + main-body `<img>` URLs into a JSON snapshot. Falls back to a plain `requests` fetch when Cypress is not available (e.g. CI or sandboxes without a browser).
2. **Text extractor** — sends cleaned page text to OpenAI (`gpt-4o-mini` by default) using Structured Outputs keyed to the race-row schema in `running_calendar_scrapers/ai_scraper/schema.py`. If the model is not confident it returns `{"insufficient": true}`.
3. **Vision fallback** — **only runs if the text extractor returned nothing**. Forwards up to four main-body image URLs to the same model for multimodal extraction.
4. **Post-processing** — normalises `distanceSlugs` to the canonical `Nkm`/`N-Nkm` kebab form, coerces `providerSlug`/`typeSlug`, defaults `country` to `Brasil`, and echoes the requested URL back into `detailUrl`.

Guardrails honoured:

- Returns **one race per call**; when a page lists several the model is instructed to pick the first.
- Images are consulted **only** when the page text yields no usable data.
- For multi-day events the model uses the **starting day** for `sortKey`.

## Installation

The library lives under `scrapers/running_calendar_scrapers/ai_scraper/` and is installed together with the other scrapers:

```bash
pip install -r scrapers/requirements.txt   # adds openai==1.58.1
npm install                                 # provides Cypress for the loader
export OPENAI_API_KEY=sk-...
```

Cypress is optional: when `npx cypress` is missing the loader silently falls back to `requests`, which works well for static pages but may miss data rendered by JavaScript.

## Programmatic use

```python
from running_calendar_scrapers.ai_scraper import scrape_race_with_ai

result = scrape_race_with_ai("https://www.yescom.com.br/corridatomejerry/2026/index.asp")
print(result.race)   # flat race row dict
print(result.source) # "text" or "image"
```

See the docstrings in `scraper.py` for the full keyword-argument surface (loader preference, model overrides, pre-built OpenAI client for tests, etc.).

## CLI

```bash
python -m running_calendar_scrapers.ai_scraper \
    https://xkrsports.com.br/ktrcampos/ \
    --loader auto --format json
```

Flags:

- `--loader {auto,cypress,requests}` — loader preference (`auto` uses Cypress when available).
- `--format {json,csv}` — `json` (default) emits `{race, source, imagesInspected}`; `csv` emits the race row with the same header as the other scrapers.
- `--text-model MODEL`, `--vision-model MODEL` — override the default OpenAI models.
- `--vision-image-limit N` — cap the number of images passed to the vision fallback (default `4`).

Example CSV output:

```csv
sortKey,city,state,country,name,typeSlug,distanceSlugs,providerSlug,detailUrl
2026-05-31T07:00,São Paulo,SP,Brasil,Fun Run Tom e Jerry 2026,road,2-5km;5km;10km,yescom,https://www.yescom.com.br/corridatomejerry/2026/index.asp
```

## Tests

Offline unit + pipeline tests (no network, mocked OpenAI client):

```bash
cd scrapers && python3 -m pytest tests/test_ai_scraper_distance.py tests/test_ai_scraper_slug.py \
    tests/test_ai_scraper_loader.py tests/test_ai_scraper_pipeline.py
```

The pipeline test in `tests/test_ai_scraper_pipeline.py` exercises:

- the happy-path text extraction (Tom & Jerry, KTR Campos do Jordão) with the example CSV rows from the product brief,
- the image fallback path when the model returns `{"insufficient": true}` on the text pass,
- both-paths-empty → `AIScraperError`,
- no-images-available → `AIScraperError`.
