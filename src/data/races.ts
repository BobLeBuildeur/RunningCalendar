/**
 * Race listings sourced from https://iguanasports.com.br and
 * https://iguanasports.com.br/blogs/calendario-corridas-de-rua (as of bootstrap).
 * Link slugs match paths under /blogs/calendario-corridas-de-rua/ on that site.
 */
export type RaceRow = {
	/** ISO 8601 local date-time string for ordering */
	sortKey: string;
	/** Human-readable date and time as shown on the source site */
	dateTimeDisplay: string;
	city: string;
	state: string;
	country: string;
	name: string;
	/** Distances in kilometres; empty when the event is age-based rather than distance-based */
	distancesKm: number[];
	/** If set, shown instead of a numeric distance list (e.g. kids events) */
	distancesNote?: string;
	/** Path segment after .../calendario-corridas-de-rua/ */
	calendarSlug: string;
};

const base = 'https://iguanasports.com.br/blogs/calendario-corridas-de-rua';

export const races: RaceRow[] = [
	{
		sortKey: '2026-04-26T06:00',
		dateTimeDisplay: '26 Apr 2026, 06:00',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Seven Run 2026',
		distancesKm: [7, 14, 21.1, 28],
		calendarSlug: 'seven-run-2026',
	},
	{
		sortKey: '2026-05-31T07:00',
		dateTimeDisplay: '31 May 2026, 07:00',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'SP10K Challenge 2026',
		distancesKm: [10],
		calendarSlug: '10k-sp-challenge-2026',
	},
	{
		sortKey: '2026-06-21T05:45',
		dateTimeDisplay: '21 Jun 2026, 05:45',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Mizuno Athenas Run Stronger 2026',
		distancesKm: [6, 12, 18, 25],
		calendarSlug: 'athenas-run-stronger-2026',
	},
	{
		sortKey: '2026-06-21T08:30',
		dateTimeDisplay: '21 Jun 2026, 08:30',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Athenas Kids Run Stronger 2026',
		distancesKm: [],
		distancesNote: 'Kids (ages 3–13); distances not listed in km on source',
		calendarSlug: 'athenas-kids-run-stronger-2026',
	},
	{
		sortKey: '2026-07-26T05:15',
		dateTimeDisplay: '26 Jul 2026, 05:15',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Nike SP City Marathon 2026',
		distancesKm: [21.1, 42.2],
		calendarSlug: 'sp-city-marathon-2026',
	},
	{
		sortKey: '2026-08-30T05:30',
		dateTimeDisplay: '30 Aug 2026, 05:30',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Run The Bridge 2026',
		distancesKm: [5, 10, 15, 30],
		calendarSlug: 'run-the-bridge-2026',
	},
	{
		sortKey: '2026-10-18T05:30',
		dateTimeDisplay: '18 Oct 2026, 05:30',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Mizuno Athenas Run Longer 2026',
		distancesKm: [7, 14, 21.1, 28],
		calendarSlug: 'athenas-run-longer-2026',
	},
	{
		sortKey: '2026-10-18T08:30',
		dateTimeDisplay: '18 Oct 2026, 08:30',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: 'Athenas Kids Run Longer 2026',
		distancesKm: [],
		distancesNote: 'Kids (ages 3–13); distances not listed in km on source',
		calendarSlug: 'athenas-kids-run-longer-2026',
	},
	{
		sortKey: '2026-11-29T06:00',
		dateTimeDisplay: '29 Nov 2026, 06:00',
		city: 'São Paulo',
		state: 'SP',
		country: 'Brasil',
		name: "Venus Women's Half Marathon 2026",
		distancesKm: [5, 10, 15, 21.1],
		calendarSlug: 'venus-womens-half-marathon-2026',
	},
].sort((a, b) => a.sortKey.localeCompare(b.sortKey));

export function raceUrl(slug: string): string {
	return `${base}/${slug}`;
}

export function formatKmList(km: number[]): string {
	if (km.length === 0) return '';
	return km.map((n) => String(n)).join(', ');
}
