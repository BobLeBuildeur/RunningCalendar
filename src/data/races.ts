/**
 * Race listings sourced from https://iguanasports.com.br and
 * https://iguanasports.com.br/blogs/calendario-corridas-de-rua (as of bootstrap).
 * Link slugs match paths under /blogs/calendario-corridas-de-rua/ on that site.
 */
import racesCsv from './races.csv?raw';

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

function parseDistancesKm(cell: string): number[] {
	const t = cell.trim();
	if (!t) return [];
	return t
		.split(';')
		.map((s) => s.trim())
		.filter(Boolean)
		.map((s) => {
			const n = Number(s);
			if (Number.isNaN(n)) throw new Error(`Invalid km value: ${s}`);
			return n;
		});
}

function rowsToRaces(matrix: string[][]): RaceRow[] {
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
		distancesKm: idx('distancesKm'),
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
			distancesKm: parseDistancesKm(line[I.distancesKm] ?? ''),
			distancesNote: note || undefined,
			calendarSlug: line[I.calendarSlug].trim(),
		});
	}
	return out;
}

const parsed = parseCsv(racesCsv.trimEnd());
export const races: RaceRow[] = rowsToRaces(parsed).sort((a, b) =>
	a.sortKey.localeCompare(b.sortKey),
);

export function raceUrl(slug: string): string {
	return `${base}/${slug}`;
}

export function formatKmList(km: number[]): string {
	if (km.length === 0) return '';
	return km.map((n) => String(n)).join(', ');
}
