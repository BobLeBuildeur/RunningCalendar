describe('Filter label analytics', () => {
	beforeEach(() => {
		cy.visit('/RunningCalendar/', {
			onBeforeLoad(win) {
				(win as unknown as { __posthog: { capture: ReturnType<typeof cy.stub> } }).__posthog = {
					capture: cy.stub().as('posthogCapture'),
				};
			},
		});
		cy.get('[data-testid="race-distance-filter"]').should('have.attr', 'data-hydrated', 'true');
		cy.get('[data-testid="race-date-filter"]').should('have.attr', 'data-hydrated', 'true');
		cy.get('@posthogCapture').invoke('resetHistory');
	});

	it('captures filter_label_clicked when a filter heading is clicked', () => {
		cy.get('[data-rc-filter-label="location"]').click();
		cy.get('@posthogCapture').should('have.been.calledWith', 'filter_label_clicked', {
			filter: 'location',
			source_page: '/RunningCalendar/',
		});

		cy.get('[data-rc-filter-label="date"]').click();
		cy.get('@posthogCapture').should('have.been.calledWith', 'filter_label_clicked', {
			filter: 'date',
			source_page: '/RunningCalendar/',
		});
	});
});
