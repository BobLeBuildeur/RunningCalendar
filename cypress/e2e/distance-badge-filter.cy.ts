/**
 * Clicking a race distance badge sets both slider thumbs to that distance (km).
 */
describe('Distance badge sets filter range', () => {
	beforeEach(() => {
		cy.visit('/RunningCalendar/');
		cy.get('[data-testid="race-distance-filter"]').should('be.visible');
		cy.get('[data-testid="race-distance-filter"]').should('have.attr', 'data-hydrated', 'true');
	});

	it('sets start and end to the badge km when a numeric distance badge is clicked', () => {
		cy.get('[data-testid="race-distance-badge"][data-distance-km="5"]').first().click();
		cy.get('#race-distance-filter-value').should('contain', '5 km').and('contain', '5 km —');
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.value', '5');
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.value', '5');
	});

	it('applies half-marathon km from badge (21.1)', () => {
		cy.get('[data-testid="race-distance-badge"][data-distance-km="21.1"]').first().click();
		cy.get('#race-distance-filter-value').should('have.text', '21.1 km — 21.1 km');
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.value', '21.1');
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.value', '21.1');
	});
});
