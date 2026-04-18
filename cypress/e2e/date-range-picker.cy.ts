describe('Date range picker', () => {
	beforeEach(() => {
		cy.clock(new Date(2026, 3, 10).getTime(), ['Date']);
		cy.visit('/RunningCalendar/', {
			onBeforeLoad(win) {
				// Stub PostHog so `captureEvent` can be asserted without a real key.
				(win as unknown as { __posthog: { capture: ReturnType<typeof cy.stub> } }).__posthog = {
					capture: cy.stub().as('posthogCapture'),
				};
			},
		});
		cy.get('[data-testid="race-date-filter"]').should('have.attr', 'data-hydrated', 'true');
	});

	it('starts collapsed and inactive', () => {
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'inactive');
		cy.get('[data-testid="date-range-popover"]').should('not.exist');
	});

	it('expands on trigger click and collapses on blur', () => {
		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-testid="date-range-popover"]').should('be.visible');
		cy.get('.page-header__title').click();
		cy.get('[data-testid="date-range-popover"]').should('not.exist');
	});

	it('is invalid with only a start date and does not filter races', () => {
		cy.get('.race-card:not([hidden])').its('length').as('initialCount');

		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-testid="date-range-popover"]').should('be.visible');
		cy.get('[data-day="2026-04-10"]').click();
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'invalid');
		cy.get('[data-testid="drp-invalid-icon"]').should('be.visible');

		cy.get('@initialCount').then((n) => {
			cy.get('.race-card:not([hidden])').should('have.length', Number(n));
		});
	});

	it('becomes valid with two dates and filters races by inclusive date range', () => {
		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-testid="date-range-popover"]').should('be.visible');
		cy.get('[data-day="2026-04-10"]').click();
		cy.get('[data-day="2026-04-12"]').click();
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'valid');
		cy.get('[data-testid="drp-valid-icon"]').should('be.visible');

		cy.get('.race-card:not([hidden])').each(($el) => {
			const d = $el.attr('data-race-date');
			expect(d, 'race date').to.be.a('string');
			expect(d! >= '2026-04-10' && d! <= '2026-04-12', `${d} in range`).to.be.true;
		});

		cy.get('.race-card:not([hidden])').should('have.length.greaterThan', 0);
	});

	it('debounces date_range_selected and sends start/end on the analytics payload', () => {
		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-day="2026-04-10"]').click();
		cy.get('[data-day="2026-04-12"]').click();
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'valid');

		cy.get('@posthogCapture').should('not.have.been.calledWith', 'date_range_selected');
		cy.tick(400);
		cy.get('@posthogCapture').should('have.been.calledWith', 'date_range_selected', {
			start: '2026-04-10',
			end: '2026-04-12',
			date_range_start: '2026-04-10',
			date_range_end: '2026-04-12',
			source_page: '/RunningCalendar/',
		});
	});

	it('clears the filter when the range is cleared', () => {
		cy.get('[data-testid="date-range-trigger"]').click();
		cy.get('[data-testid="date-range-popover"]').should('be.visible');
		cy.get('[data-day="2026-04-10"]').click();
		cy.get('[data-day="2026-04-15"]').click();
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'valid');

		cy.get('[data-testid="drp-clear-footer"]').click();
		cy.get('[data-testid="date-range-picker"]').should('have.attr', 'data-state', 'inactive');

		cy.get('.race-card:not([hidden])').should('have.length.greaterThan', 5);
	});
});
