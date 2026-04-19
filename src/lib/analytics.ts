import posthog from 'posthog-js';

export const SOURCE_PAGE = '/RunningCalendar/';

/** Emitted with every `location_selected`, `distance_range_selected`, `date_range_selected`, or `saved_filter_selected` event. */
export const CALENDAR_FILTERED_EVENT = 'calendar_filtered';

export type FilterSelectionTrigger =
	| 'location_selected'
	| 'distance_range_selected'
	| 'date_range_selected'
	| 'saved_filter_selected';

declare global {
	interface Window {
		__posthog?: typeof posthog;
		/** Set after PostHog init; used by inline scripts that cannot import modules. */
		__rcCapture?: (event: string, props: Record<string, unknown>) => void;
	}
}

export function initPosthog(): void {
	const key = import.meta.env.PUBLIC_POSTHOG_KEY;
	if (!key || typeof key !== 'string') return;

	const apiHost =
		typeof import.meta.env.PUBLIC_POSTHOG_HOST === 'string' && import.meta.env.PUBLIC_POSTHOG_HOST.length > 0
			? import.meta.env.PUBLIC_POSTHOG_HOST
			: 'https://us.i.posthog.com';

	posthog.init(key, {
		api_host: apiHost,
		persistence: 'localStorage+cookie',
		capture_pageview: false,
		capture_pageleave: true,
	});

	window.__posthog = posthog;
	window.__rcCapture = (event, props) => {
		posthog.capture(event, props);
	};

	let refPath: string | undefined;
	try {
		if (document.referrer) refPath = new URL(document.referrer).pathname;
	} catch {
		refPath = undefined;
	}

	posthog.capture('calendar_viewed', {
		source_page: refPath,
		base_path: import.meta.env.BASE_URL,
	});
}

export function captureEvent(event: string, props: Record<string, unknown>): void {
	window.__posthog?.capture(event, props);
}

/** Fires the specific filter event, then a generic `calendar_filtered` with `filter_trigger`. */
export function captureFilterSelectionEvent(
	trigger: FilterSelectionTrigger,
	props: Record<string, unknown>,
): void {
	captureEvent(trigger, props);
	captureEvent(CALENDAR_FILTERED_EVENT, {
		filter_trigger: trigger,
		source_page: typeof props.source_page === 'string' ? props.source_page : SOURCE_PAGE,
	});
}
