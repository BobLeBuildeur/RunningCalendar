/**
 * Race listings: loaded at **build time** from PostgreSQL (Supabase) via `loadCalendar()`.
 * Reference data shape matches docs/data-model.md (public.races, race_distances, distances, types, providers).
 *
 * Reference data lives only in PostgreSQL (Supabase); use `npm run validate-db` for integrity checks.
 */
import { loadCalendarFromDatabase } from '../lib/calendarDb';

export type DistanceRow = {
	slug: string;
	/** Distance in kilometres (DB stores integer tenths of a km, e.g. 211 → 21.1) */
	km: number;
	/** Optional human context when the row is not a plain numeric distance (e.g. kids categories) */
	description?: string;
};

export type TypeRow = {
	slug: string;
	/** Display label (e.g. Road, Trail) */
	type: string;
};

export type ProviderRow = {
	slug: string;
	name: string;
	website: string;
};

export type RaceRow = {
	/** ISO 8601 local date-time string for ordering and display */
	sortKey: string;
	city: string;
	state: string;
	country: string;
	name: string;
	/** Slug into `types` */
	typeSlug: string;
	/** Slugs into `distances`; empty when no distances apply */
	distanceSlugs: string[];
	/** Slug into `providers` */
	providerSlug: string;
	/** Canonical detail page for this race (may differ per provider) */
	detailUrl: string;
};

/** Bound helpers + collections after loading from the database. */
export type CalendarModel = {
	races: RaceRow[];
	distances: DistanceRow[];
	types: TypeRow[];
	providers: ProviderRow[];
	formatKmList: (distanceSlugs: string[]) => string;
	kmForDistanceSlug: (slug: string) => number | undefined;
	labelForDistanceSlug: (slug: string) => string;
	labelForTypeSlug: (slug: string) => string | undefined;
	providerForSlug: (slug: string) => ProviderRow | undefined;
	distanceBoundsFromRaces: (raceList: RaceRow[]) => { minKm: number; maxKm: number } | null;
};

/** Formats `sortKey` (YYYY-MM-DDTHH:MM) for the race card meta line. */
export function formatRaceDateTimeDisplay(sortKey: string): string {
	const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(sortKey.trim());
	if (!m) return sortKey;
	const [, y, mo, d, hh, mm] = m;
	const month = Number(mo) - 1;
	const day = Number(d);
	const dt = new Date(Date.UTC(Number(y), month, day, Number(hh), Number(mm)));
	return new Intl.DateTimeFormat('pt-BR', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
		hour12: false,
		timeZone: 'UTC',
	}).format(dt);
}

/** Public URL for race details (always from `detailUrl` in the data model). */
export function raceUrl(race: Pick<RaceRow, 'detailUrl'>): string {
	return race.detailUrl;
}

/** Combined location line for display and filtering: "City, ST, Country". */
export function formatRaceLocationLine(
	race: Pick<RaceRow, 'city' | 'state' | 'country'>,
): string {
	return `${race.city}, ${race.state}, ${race.country}`;
}

/** Min/max km across this race's listed distances, or `null` when none are set. */
export function raceKmRange(race: RaceRow, kmForSlug: (slug: string) => number | undefined): { minKm: number; maxKm: number } | null {
	const kms = race.distanceSlugs.map((slug) => kmForSlug(slug)).filter((k): k is number => k !== undefined);
	if (kms.length === 0) return null;
	return { minKm: Math.min(...kms), maxKm: Math.max(...kms) };
}

/** Smallest/largest km among all races that list at least one distance. */
function computeDistanceBoundsFromRaces(
	raceList: RaceRow[],
	kmForSlug: (slug: string) => number | undefined,
): { minKm: number; maxKm: number } | null {
	let minKm = Infinity;
	let maxKm = -Infinity;
	for (const r of raceList) {
		const range = raceKmRange(r, kmForSlug);
		if (!range) continue;
		minKm = Math.min(minKm, range.minKm);
		maxKm = Math.max(maxKm, range.maxKm);
	}
	if (!Number.isFinite(minKm)) return null;
	return { minKm, maxKm };
}

function buildCalendarModel(
	distances: DistanceRow[],
	types: TypeRow[],
	providers: ProviderRow[],
	races: RaceRow[],
): CalendarModel {
	const distanceKmBySlug = new Map(distances.map((d) => [d.slug, d.km]));
	const distanceDescriptionBySlug = new Map(
		distances.filter((d) => d.description).map((d) => [d.slug, d.description!]),
	);
	const typeLabelBySlug = new Map(types.map((t) => [t.slug, t.type]));
	const providerBySlug = new Map(providers.map((p) => [p.slug, p]));

	const kmForDistanceSlug = (slug: string): number | undefined => distanceKmBySlug.get(slug);

	return {
		races,
		distances,
		types,
		providers,
		formatKmList(distanceSlugs: string[]): string {
			if (distanceSlugs.length === 0) return '';
			return distanceSlugs
				.map((slug) => {
					const km = distanceKmBySlug.get(slug);
					if (km === undefined) throw new Error(`Unknown distance slug: ${slug}`);
					return String(km);
				})
				.join(', ');
		},
		kmForDistanceSlug,
		labelForDistanceSlug(slug: string): string {
			const desc = distanceDescriptionBySlug.get(slug);
			if (desc) return desc;
			const km = distanceKmBySlug.get(slug);
			if (km === undefined) return slug;
			const n = km % 1 === 0 ? String(km) : String(km);
			return `${n} km`;
		},
		labelForTypeSlug(slug: string): string | undefined {
			return typeLabelBySlug.get(slug);
		},
		providerForSlug(slug: string): ProviderRow | undefined {
			return providerBySlug.get(slug);
		},
		distanceBoundsFromRaces(raceList: RaceRow[]) {
			return computeDistanceBoundsFromRaces(raceList, kmForDistanceSlug);
		},
	};
}

/**
 * Deterministic minimal calendar for E2E / agent builds when no database is available.
 * Set `RUNNINGCALENDAR_E2E_FIXTURE=1` during `astro build` (see `preview:e2e` script).
 */
function loadE2eFixtureCalendar(): CalendarModel {
	const distances: DistanceRow[] = [{ slug: '10k', km: 10 }];
	const types: TypeRow[] = [{ slug: 'road', type: 'Road' }];
	const providers: ProviderRow[] = [
		{ slug: 'fixture', name: 'Fixture Org', website: 'https://example.com' },
	];
	const races: RaceRow[] = [];
	for (let d = 1; d <= 30; d++) {
		const day = String(d).padStart(2, '0');
		races.push({
			sortKey: `2026-04-${day}T08:00`,
			city: 'São Paulo',
			state: 'SP',
			country: 'Brasil',
			name: `Corrida fixture ${day}`,
			typeSlug: 'road',
			distanceSlugs: ['10k'],
			providerSlug: 'fixture',
			detailUrl: `https://example.com/fixture-race-2026-04-${day}`,
		});
	}
	return buildCalendarModel(distances, types, providers, races);
}

/**
 * Load all calendar data from Supabase (PostgreSQL). Call from Astro frontmatter
 * (`const calendar = await loadCalendar()`).
 */
export async function loadCalendar(): Promise<CalendarModel> {
	if (process.env.RUNNINGCALENDAR_E2E_FIXTURE === '1') {
		return loadE2eFixtureCalendar();
	}

	const db = await loadCalendarFromDatabase();

	const distances: DistanceRow[] = db.distances.map((d) => ({
		slug: d.slug,
		km: d.km / 10,
		...(d.description ? { description: d.description } : {}),
	}));

	const types: TypeRow[] = db.types.map((t) => ({ slug: t.slug, type: t.type }));
	const providers: ProviderRow[] = db.providers.map((p) => ({
		slug: p.slug,
		name: p.name,
		website: p.website,
	}));

	const distSlugs = new Set(distances.map((d) => d.slug));
	const typeSlugs = new Set(types.map((t) => t.slug));
	const provSlugs = new Set(providers.map((p) => p.slug));

	const races: RaceRow[] = db.races.map((row) => {
		const typeSlug = row.type_slug.trim() || 'road';
		if (!typeSlugs.has(typeSlug)) throw new Error(`Unknown type slug from DB: ${typeSlug}`);
		if (!provSlugs.has(row.provider_slug)) throw new Error(`Unknown provider slug from DB: ${row.provider_slug}`);
		const detailUrl = row.detail_url.trim();
		if (!detailUrl) throw new Error(`Missing detail_url for race: ${row.name}`);
		const slugs = (row.distance_slugs ?? []).filter(Boolean);
		for (const s of slugs) {
			if (!distSlugs.has(s)) throw new Error(`Unknown distance slug from DB: ${s}`);
		}
		return {
			sortKey: row.sort_key.trim(),
			city: row.city.trim(),
			state: row.state.trim(),
			country: row.country.trim(),
			name: row.name.trim(),
			typeSlug,
			distanceSlugs: slugs,
			providerSlug: row.provider_slug.trim(),
			detailUrl,
		};
	});

	return buildCalendarModel(distances, types, providers, races);
}
