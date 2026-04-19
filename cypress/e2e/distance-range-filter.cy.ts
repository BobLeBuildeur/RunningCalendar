/**
 * Distance filter uses DualRangeSlider: thumbs must map to absolute km on the full track,
 * and min must never exceed max.
 */
describe('Distance range filter', () => {
	beforeEach(() => {
		cy.visit('/RunningCalendar/');
		cy.get('[data-testid="race-distance-filter"]').should('be.visible');
		// SSR renders the slider; Svelte `oninput` handlers attach after island hydration.
		cy.get('[data-testid="race-distance-filter"]').should('have.attr', 'data-hydrated', 'true');
	});

	function setRangeValue(testId: string, value: number) {
		cy.get(`[data-testid="${testId}"]`).then(($el) => {
			const el = $el[0] as HTMLInputElement;
			const win = el.ownerDocument.defaultView;
			if (!win) throw new Error('no window');
			const nativeSet = Object.getOwnPropertyDescriptor(
				win.HTMLInputElement.prototype,
				'value',
			)?.set;
			if (!nativeSet) throw new Error('native value setter missing');
			nativeSet.call(el, String(value));
			el.dispatchEvent(new win.Event('input', { bubbles: true }));
		});
	}

	function setRangeStart(value: number) {
		setRangeValue('race-distance-filter-range-start', value);
	}

	function setRangeEnd(value: number) {
		setRangeValue('race-distance-filter-range-end', value);
	}

	it('shows the same absolute km for min and max when both thumbs are at the same value', () => {
		const v = 21.1; // midpoint of 0–41.195 km; both thumbs align at the same track position
		setRangeStart(v);
		cy.get('#race-distance-filter-value').should('contain', '21.1 km');
		setRangeEnd(v);
		cy.get('#race-distance-filter-value').should('have.text', '21.1 km — 21.1 km');
	});

	it('clamps min so it cannot move above max', () => {
		setRangeEnd(10);
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.value', '10');
		cy.get('#race-distance-filter-value').should('contain', '10 km');
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.attr', 'max', '10');
		setRangeStart(25);
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.value', '10');
		cy.get('#race-distance-filter-value').should('contain', '10 km — 10 km');
	});

	it('does not shift min when only max changes', () => {
		setRangeStart(5);
		cy.get('#race-distance-filter-value').should('contain', '5 km');
		setRangeEnd(15);
		cy.get('#race-distance-filter-value').should('contain', '5 km').and('contain', '15 km');

		setRangeEnd(30);
		cy.get('#race-distance-filter-value').should('contain', '5 km').and('contain', '30 km');
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.value', '5');
	});

	it('clamps max so it cannot move below min', () => {
		setRangeStart(20);
		cy.get('#race-distance-filter-value').should('contain', '20 km');
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.attr', 'min', '20');
		setRangeEnd(8);
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.value', '20');
		cy.get('#race-distance-filter-value').should('contain', '20 km — 20 km');
	});

	it('exposes native bounds so start thumb cannot pass end and end cannot pass start', () => {
		setRangeStart(15);
		setRangeEnd(25);
		cy.get('[data-testid="race-distance-filter-range-start"]').should('have.attr', 'max', '25');
		cy.get('[data-testid="race-distance-filter-range-end"]').should('have.attr', 'min', '15');
	});

	it('when end is at max (41.195 km), summary shows open upper bound', () => {
		setRangeEnd(41.195);
		cy.get('#race-distance-filter-value').should('contain', '41.195 km ou mais');
	});

	it('when end is at max, includes races at or above marathon distance', () => {
		setRangeStart(40);
		setRangeEnd(41.195);
		cy.get('.race-card[data-distance-kms="42.195"]').first().should('be.visible');
		cy.get('.race-card[data-distance-kms="5"]').first().should('be.hidden');
	});
});
