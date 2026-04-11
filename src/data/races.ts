/**
 * Race listings sourced from https://iguanasports.com.br and
 * https://iguanasports.com.br/blogs/calendario-corridas-de-rua (as of bootstrap).
 * Link slugs match paths under /blogs/calendario-corridas-de-rua/ on that site.
 *
 * Distances are normalized in `distances.csv` (slug + km); races reference them by slug.
 */
import distancesCsv from './distances.csv?raw';
import racesCsv from './races.csv?raw';

export type DistanceRow = {
	slug: string;
	/** Distance in kilometres */
	km: number;
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
	/** Slugs into `distances`; empty when the event is age-based rather than distance-based */
	distanceSlugs: string[];
	/** If set, shown instead of a numeric distance list (e.g. kids events) */
	distancesNote?: string;
	/** Path segment after .../calendario-corridas-de-rua/ */
	calendarSlug: string;
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

function rowsToRaces(matrix: string[][], validSlugs: ReadonlySet<string>): RaceRow[] {
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
		distanceSlugs: idx('distanceSlugs'),
		distancesNote: idx('distancesNote'),
		calendarSlug: idx('calendarSlug'),
	};

	const out: RaceRow[] = [];
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const note = line[I.distancesNote]?.trim();
		out.push({
			sortKey: line[I.sortKey].trim(),
			dateTimeDisplay: line[I.dateTimeDisplay].trim(),
			city: line[I.city].trim(),
			state: line[I.state].trim(),
			country: line[I.country].trim(),
			name: line[I.name].trim(),
			distanceSlugs: parseDistanceSlugs(line[I.distanceSlugs] ?? '', validSlugs),
			distancesNote: note || undefined,
			calendarSlug: line[I.calendarSlug].trim(),
		});
	}
	return out;
}

const distancesMatrix = parseCsv(distancesCsv.trimEnd());
export const distances: DistanceRow[] = rowsToDistances(distancesMatrix).sort((a, b) =>
	a.slug.localeCompare(b.slug),
);

const distanceKmBySlug = new Map(distances.map((d) => [d.slug, d.km]));
const validDistanceSlugs = new Set(distances.map((d) => d.slug));

const racesMatrix = parseCsv(racesCsv.trimEnd());
export const races: RaceRow[] = rowsToRaces(racesMatrix, validDistanceSlugs).sort((a, b) =>
	a.sortKey.localeCompare(b.sortKey),
);

export function raceUrl(slug: string): string {
	return `${base}/${slug}`;
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
