/**
 * Short walkthrough for screen recording (see artifacts/ui/cypress-videos/).
 * Run: npm run test:e2e:demo
 */
describe('Date range picker demo', () => {
	it('opens calendar, selects a range, applies, and filters', () => {
		cy.clock(new Date(2026, 3, 10).getTime(), ['Date']);
		cy.visit('/RunningCalendar/');

		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-testid="date-range-popover"]').should('be.visible');
		cy.wait(400);

		cy.get('[data-day="2026-04-10"]').click();
		cy.wait(300);
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'invalid');
		cy.wait(300);

		cy.get('[data-day="2026-04-12"]').click();
		cy.wait(300);
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'valid');
		cy.wait(300);

		cy.get('[data-testid="drp-apply"]').click();
		cy.get('[data-testid="date-range-popover"]').should('not.exist');
		cy.wait(400);

		cy.get('.race-card:not([hidden])').should('have.length.greaterThan', 0);
	});
});
