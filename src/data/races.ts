/**
 * Race listings sourced from https://iguanasports.com.br and
 * https://iguanasports.com.br/blogs/calendario-corridas-de-rua (as of bootstrap).
 * Link slugs match paths under /blogs/calendario-corridas-de-rua/ on that site.
 *
 * Distances are normalized in `distances.csv` (slug + km); races reference them by slug.
 * Race kinds are normalized in `types.csv` (slug + type label); races reference them via `typeSlug`.
 * Organizers are normalized in `providers.csv`; races reference them via `providerSlug`.
 */
import distancesCsv from './distances.csv?raw';
import providersCsv from './providers.csv?raw';
import racesCsv from './races.csv?raw';
import typesCsv from './types.csv?raw';

export type DistanceRow = {
	slug: string;
	/** Distance in kilometres */
	km: number;
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
	/** ISO 8601 local date-time string for ordering */
	sortKey: string;
	/** Human-readable date and time as shown on the source site */
	dateTimeDisplay: string;
	city: string;
	state: string;
	country: string;
	name: string;
	/** Slug into `types` */
	typeSlug: string;
	/** Slugs into `distances`; empty when the event is age-based rather than distance-based */
	distanceSlugs: string[];
	/** If set, shown instead of a numeric distance list (e.g. kids events) */
	distancesNote?: string;
	/** Path segment after .../calendario-corridas-de-rua/ */
	calendarSlug: string;
	/** Slug into `providers` */
	providerSlug: string;
	/** Canonical detail page for this race (may differ per provider) */
	detailUrl: string;
};

const base = 'https://iguanasports.com.br/blogs/calendario-corridas-de-rua';

/** Minimal RFC 4180-style CSV parser (quoted fields, commas). */
function parseCsv(text: string): string[][] {
	const rows: string[][] = [];
	let row: string[] = [];
	let field = '';
	let i = 0;
	let inQuotes = false;

	const pushField = () => {
		row.push(field);
		field = '';
	};
	const pushRow = () => {
		rows.push(row);
		row = [];
	};

	while (i < text.length) {
		const c = text[i];
		if (inQuotes) {
			if (c === '"') {
				if (text[i + 1] === '"') {
					field += '"';
					i += 2;
					continue;
				}
				inQuotes = false;
				i++;
				continue;
			}
			field += c;
			i++;
			continue;
		}
		if (c === '"') {
			inQuotes = true;
			i++;
			continue;
		}
		if (c === ',') {
			pushField();
			i++;
			continue;
		}
		if (c === '\r') {
			i++;
			continue;
		}
		if (c === '\n') {
			pushField();
			pushRow();
			i++;
			continue;
		}
		field += c;
		i++;
	}
	pushField();
	if (row.some((cell) => cell.length > 0)) pushRow();

	return rows;
}

function parseKmCell(cell: string): number {
	const t = cell.trim();
	const n = Number(t);
	if (Number.isNaN(n)) throw new Error(`Invalid km value: ${t}`);
	return n;
}

function rowsToDistances(matrix: string[][]): DistanceRow[] {
	if (matrix.length < 2) return [];
	const header = matrix[0].map((h) => h.trim());
	const idx = (name: string) => {
		const j = header.indexOf(name);
		if (j === -1) throw new Error(`Missing CSV column: ${name}`);
		return j;
	};
	const I = { slug: idx('slug'), km: idx('km') };

	const out: DistanceRow[] = [];
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const slug = line[I.slug]?.trim() ?? '';
		if (!slug) continue;
		out.push({ slug, km: parseKmCell(line[I.km] ?? '') });
	}
	return out;
}

function parseDistanceSlugs(cell: string, validSlugs: ReadonlySet<string>): string[] {
	const t = cell.trim();
	if (!t) return [];
	return t
		.split(';')
		.map((s) => s.trim())
		.filter(Boolean)
		.map((s) => {
			if (!validSlugs.has(s)) throw new Error(`Unknown distance slug in races.csv: ${s}`);
			return s;
		});
}

function rowsToProviders(matrix: string[][]): ProviderRow[] {
	if (matrix.length < 2) return [];
	const header = matrix[0].map((h) => h.trim());
	const idx = (name: string) => {
		const j = header.indexOf(name);
		if (j === -1) throw new Error(`Missing CSV column: ${name}`);
		return j;
	};
	const I = { slug: idx('slug'), name: idx('name'), website: idx('website') };

	const out: ProviderRow[] = [];
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const slug = line[I.slug]?.trim() ?? '';
		if (!slug) continue;
		out.push({
			slug,
			name: (line[I.name] ?? '').trim(),
			website: (line[I.website] ?? '').trim(),
		});
	}
	return out;
}

function rowsToTypes(matrix: string[][]): TypeRow[] {
	if (matrix.length < 2) return [];
	const header = matrix[0].map((h) => h.trim());
	const idx = (name: string) => {
		const j = header.indexOf(name);
		if (j === -1) throw new Error(`Missing CSV column: ${name}`);
		return j;
	};
	const I = { slug: idx('slug'), type: idx('type') };

	const out: TypeRow[] = [];
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const slug = line[I.slug]?.trim() ?? '';
		if (!slug) continue;
		out.push({ slug, type: (line[I.type] ?? '').trim() });
	}
	return out;
}

function rowsToRaces(
	matrix: string[][],
	validDistanceSlugs: ReadonlySet<string>,
	validTypeSlugs: ReadonlySet<string>,
	validProviderSlugs: ReadonlySet<string>,
): RaceRow[] {
	if (matrix.length < 2) return [];
	const header = matrix[0].map((h) => h.trim());
	const idx = (name: string) => {
		const j = header.indexOf(name);
		if (j === -1) throw new Error(`Missing CSV column: ${name}`);
		return j;
	};
	const I = {
		sortKey: idx('sortKey'),
		dateTimeDisplay: idx('dateTimeDisplay'),
		city: idx('city'),
		state: idx('state'),
		country: idx('country'),
		name: idx('name'),
		typeSlug: idx('typeSlug'),
		distanceSlugs: idx('distanceSlugs'),
		distancesNote: idx('distancesNote'),
		calendarSlug: idx('calendarSlug'),
		providerSlug: idx('providerSlug'),
		detailUrl: idx('detailUrl'),
	};

	const out: RaceRow[] = [];
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const note = line[I.distancesNote]?.trim();
		const typeSlug = (line[I.typeSlug] ?? '').trim();
		if (!typeSlug) throw new Error(`Missing typeSlug for race row: ${line[I.name] ?? r}`);
		if (!validTypeSlugs.has(typeSlug)) throw new Error(`Unknown type slug in races.csv: ${typeSlug}`);
		const providerSlug = (line[I.providerSlug] ?? '').trim();
		if (!providerSlug) throw new Error(`Missing providerSlug for race row: ${line[I.name] ?? r}`);
		if (!validProviderSlugs.has(providerSlug))
			throw new Error(`Unknown provider slug in races.csv: ${providerSlug}`);
		const detailUrl = (line[I.detailUrl] ?? '').trim();
		if (!detailUrl) throw new Error(`Missing detailUrl for race row: ${line[I.name] ?? r}`);
		out.push({
			sortKey: line[I.sortKey].trim(),
			dateTimeDisplay: line[I.dateTimeDisplay].trim(),
			city: line[I.city].trim(),
			state: line[I.state].trim(),
			country: line[I.country].trim(),
			name: line[I.name].trim(),
			typeSlug,
			distanceSlugs: parseDistanceSlugs(line[I.distanceSlugs] ?? '', validDistanceSlugs),
			distancesNote: note || undefined,
			calendarSlug: line[I.calendarSlug].trim(),
			providerSlug,
			detailUrl,
		});
	}
	return out;
}

const distancesMatrix = parseCsv(distancesCsv.trimEnd());
export const distances: DistanceRow[] = rowsToDistances(distancesMatrix).sort((a, b) =>
	a.slug.localeCompare(b.slug),
);

const typesMatrix = parseCsv(typesCsv.trimEnd());
export const types: TypeRow[] = rowsToTypes(typesMatrix).sort((a, b) => a.slug.localeCompare(b.slug));

const providersMatrix = parseCsv(providersCsv.trimEnd());
export const providers: ProviderRow[] = rowsToProviders(providersMatrix).sort((a, b) =>
	a.slug.localeCompare(b.slug),
);

const distanceKmBySlug = new Map(distances.map((d) => [d.slug, d.km]));
const validDistanceSlugs = new Set(distances.map((d) => d.slug));
const typeLabelBySlug = new Map(types.map((t) => [t.slug, t.type]));
const validTypeSlugs = new Set(types.map((t) => t.slug));
const validProviderSlugs = new Set(providers.map((p) => p.slug));
const providerBySlug = new Map(providers.map((p) => [p.slug, p]));

const racesMatrix = parseCsv(racesCsv.trimEnd());
export const races: RaceRow[] = rowsToRaces(
	racesMatrix,
	validDistanceSlugs,
	validTypeSlugs,
	validProviderSlugs,
).sort((a, b) => a.sortKey.localeCompare(b.sortKey));

export function raceUrl(race: Pick<RaceRow, 'calendarSlug' | 'detailUrl'>): string {
	return race.detailUrl || `${base}/${race.calendarSlug}`;
}

/** Formats km values for the given distance slugs (order preserved). */
export function formatKmList(distanceSlugs: string[]): string {
	if (distanceSlugs.length === 0) return '';
	return distanceSlugs
		.map((slug) => {
			const km = distanceKmBySlug.get(slug);
			if (km === undefined) throw new Error(`Unknown distance slug: ${slug}`);
			return String(km);
		})
		.join(', ');
}

export function kmForDistanceSlug(slug: string): number | undefined {
	return distanceKmBySlug.get(slug);
}

export function labelForTypeSlug(slug: string): string | undefined {
	return typeLabelBySlug.get(slug);
}

export function providerForSlug(slug: string): ProviderRow | undefined {
	return providerBySlug.get(slug);
}
