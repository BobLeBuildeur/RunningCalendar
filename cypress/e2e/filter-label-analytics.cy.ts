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

	it('captures calendar_filtered with location_selected when the location filter changes', () => {
		cy.get('#race-location-filter option')
			.eq(1)
			.then(($opt) => {
				const val = String($opt.val());
				cy.get('#race-location-filter').select(val);
				cy.get('@posthogCapture').should('have.been.calledWith', 'location_selected', {
					location_value: val,
					source_page: '/RunningCalendar/',
				});
				cy.get('@posthogCapture').should('have.been.calledWith', 'calendar_filtered', {
					filter_trigger: 'location_selected',
					source_page: '/RunningCalendar/',
				});
			});
	});
});
