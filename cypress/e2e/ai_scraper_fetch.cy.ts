/// <reference types="cypress" />

/**
 * Headless Cypress spec driven by the Python AI-scraper loader.
 *
 * Consumes two environment variables (set by `scrapers/running_calendar_scrapers/ai_scraper/loader.py`):
 *   - TARGET_URL: absolute URL of the race page to snapshot.
 *   - SNAPSHOT_PATH: absolute path where the JSON snapshot should be written.
 *
 * Outputs a JSON file with { url, title, html, images[] }; the Python side
 * cleans the HTML and hands text/images to the OpenAI extractor.
 */

const TARGET_URL = Cypress.env('TARGET_URL') as string | undefined;
const SNAPSHOT_PATH = Cypress.env('SNAPSHOT_PATH') as string | undefined;

describe('ai_scraper_fetch', () => {
	it('captures rendered DOM + main-body images', () => {
		if (!TARGET_URL || !SNAPSHOT_PATH) {
			throw new Error('TARGET_URL and SNAPSHOT_PATH env vars must be set');
		}

		cy.visit(TARGET_URL, { failOnStatusCode: false, timeout: 60_000 });
		cy.wait(1500);

		cy.document().then((doc) => {
			const title = doc.title || '';
			const html = doc.documentElement.outerHTML;
			const scope =
				doc.querySelector('main') ||
				doc.querySelector('article') ||
				doc.querySelector('[role=main]') ||
				doc.body;
			const images: string[] = [];
			scope.querySelectorAll('img').forEach((el) => {
				const src =
					(el as HTMLImageElement).src ||
					el.getAttribute('data-src') ||
					'';
				if (src && !src.startsWith('data:') && !images.includes(src)) {
					images.push(src);
				}
			});
			cy.writeFile(SNAPSHOT_PATH, { url: TARGET_URL, title, html, images });
		});
	});
});
