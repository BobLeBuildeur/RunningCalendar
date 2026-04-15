#!/usr/bin/env node
/**
 * Compare Supabase public.* data to src/data/*.csv (reference parity check).
 * Requires RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL.
 *
 * Run: node scripts/compare-db-to-csv.mjs
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import pg from 'pg';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(__dirname, '..');
const dataDir = join(repoRoot, 'src', 'data');

function databaseUrl() {
	const u = (
		process.env.RUNNINGCALENDAR_DATABASE_URL ||
		process.env.DATABASE_URL ||
		process.env.SUPABASE_DB_URL ||
		''
	).trim();
	if (!u) {
		throw new Error(
			'Set RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL (Supabase session mode Postgres URI).',
		);
	}
	return u;
}

/**
 * Join key for races: trimmed detail URL as stored (CSV `detailUrl` ↔ DB `detail_url`).
 * Use exact strings so `www.` vs bare host are distinct, matching seeded rows.
 */
function raceKeyFromDetailUrl(url) {
	return (url || '').trim();
}

function parseCsv(text) {
	const rows = [];
	let row = [];
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

function slugOrderFromDistancesCsv(matrix) {
	const header = matrix[0].map((h) => h.trim());
	const si = header.indexOf('slug');
	const ki = header.indexOf('km');
	const order = new Map();
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const slug = (line[si] ?? '').trim();
		if (!slug) continue;
		const km = Number((line[ki] ?? '').trim());
		order.set(slug, km / 10);
	}
	return order;
}

function sortDistanceSlugs(slugs, slugToKm) {
	return [...new Set(slugs)].sort((a, b) => (slugToKm.get(a) ?? 0) - (slugToKm.get(b) ?? 0));
}

function loadRacesFromCsv() {
	const raw = readFileSync(join(dataDir, 'races.csv'), 'utf8');
	const matrix = parseCsv(raw.trimEnd());
	const distMatrix = parseCsv(readFileSync(join(dataDir, 'distances.csv'), 'utf8').trimEnd());
	const slugToKm = slugOrderFromDistancesCsv(distMatrix);

	const header = matrix[0].map((h) => h.trim());
	const I = {
		sortKey: header.indexOf('sortKey'),
		city: header.indexOf('city'),
		state: header.indexOf('state'),
		country: header.indexOf('country'),
		name: header.indexOf('name'),
		typeSlug: header.indexOf('typeSlug'),
		distanceSlugs: header.indexOf('distanceSlugs'),
		providerSlug: header.indexOf('providerSlug'),
		detailUrl: header.indexOf('detailUrl'),
	};

	const byKey = new Map();
	for (let r = 1; r < matrix.length; r++) {
		const line = matrix[r];
		if (line.every((c) => !c.trim())) continue;
		const detailUrl = (line[I.detailUrl] ?? '').trim();
		const cell = (line[I.distanceSlugs] ?? '').trim();
		const rawSlugs = cell ? cell.split(';').map((s) => s.trim()).filter(Boolean) : [];
		const typeSlug = ((line[I.typeSlug] ?? '').trim() || 'road');
		const row = {
			sortKey: line[I.sortKey].trim(),
			city: line[I.city].trim(),
			state: line[I.state].trim(),
			country: line[I.country].trim(),
			name: line[I.name].trim(),
			typeSlug,
			distanceSlugs: sortDistanceSlugs(rawSlugs, slugToKm),
			providerSlug: line[I.providerSlug].trim(),
			detailUrl,
		};
		const k = raceKeyFromDetailUrl(detailUrl);
		if (byKey.has(k)) throw new Error(`CSV duplicate detailUrl: ${detailUrl}`);
		byKey.set(k, row);
	}
	return byKey;
}

async function loadRacesFromDb(pool) {
	const distMatrix = parseCsv(readFileSync(join(dataDir, 'distances.csv'), 'utf8').trimEnd());
	const slugToKm = slugOrderFromDistancesCsv(distMatrix);

	const { rows } = await pool.query(`
		SELECT
			r.sort_key,
			r.city,
			r.state,
			r.country,
			r.name,
			r.type_slug,
			r.provider_slug,
			r.detail_url,
			COALESCE(
				(
					SELECT array_agg(s.slug ORDER BY s.km)
					FROM (
						SELECT rd.distance_slug AS slug, d.km
						FROM public.race_distances rd
						INNER JOIN public.distances d ON d.slug = rd.distance_slug
						WHERE rd.race_id = r.id
					) s
				),
				ARRAY[]::text[]
			) AS distance_slugs
		FROM public.races r
		ORDER BY r.sort_key
	`);

	const byKey = new Map();
	for (const row of rows) {
		const detailUrl = String(row.detail_url ?? '').trim();
		const rawSlugs = row.distance_slugs ?? [];
		const typeSlug = String(row.type_slug ?? '').trim() || 'road';
		const o = {
			sortKey: String(row.sort_key ?? '').trim(),
			city: String(row.city ?? '').trim(),
			state: String(row.state ?? '').trim(),
			country: String(row.country ?? '').trim(),
			name: String(row.name ?? '').trim(),
			typeSlug,
			distanceSlugs: sortDistanceSlugs(rawSlugs, slugToKm),
			providerSlug: String(row.provider_slug ?? '').trim(),
			detailUrl,
		};
		const k = raceKeyFromDetailUrl(detailUrl);
		if (byKey.has(k)) throw new Error(`DB duplicate detail_url: ${detailUrl}`);
		byKey.set(k, o);
	}
	return byKey;
}

function rowEqual(a, b) {
	const keys = ['sortKey', 'city', 'state', 'country', 'name', 'typeSlug', 'providerSlug', 'detailUrl'];
	for (const k of keys) {
		if (a[k] !== b[k]) return { ok: false, field: k, left: a[k], right: b[k] };
	}
	if (a.distanceSlugs.length !== b.distanceSlugs.length) {
		return { ok: false, field: 'distanceSlugs', left: a.distanceSlugs.join(';'), right: b.distanceSlugs.join(';') };
	}
	for (let i = 0; i < a.distanceSlugs.length; i++) {
		if (a.distanceSlugs[i] !== b.distanceSlugs[i]) {
			return {
				ok: false,
				field: 'distanceSlugs',
				left: a.distanceSlugs.join(';'),
				right: b.distanceSlugs.join(';'),
			};
		}
	}
	return { ok: true };
}

async function compareReferenceTables(pool) {
	const checks = [
		{ table: 'providers', file: 'providers.csv', cols: ['slug', 'name', 'website'] },
		{ table: 'types', file: 'types.csv', cols: ['slug', 'type'] },
		{ table: 'distances', file: 'distances.csv', cols: ['slug', 'km', 'description'] },
	];

	for (const { table, file, cols } of checks) {
		const matrix = parseCsv(readFileSync(join(dataDir, file), 'utf8').trimEnd());
		const header = matrix[0].map((h) => h.trim());
		const idx = Object.fromEntries(cols.map((c) => [c, header.indexOf(c)]));
		const csvRows = [];
		for (let r = 1; r < matrix.length; r++) {
			const line = matrix[r];
			if (line.every((c) => !c.trim())) continue;
			const o = {};
			for (const c of cols) {
				o[c] = (line[idx[c]] ?? '').trim();
			}
			if (file === 'distances.csv' && !o.description) o.description = null;
			else if (file === 'distances.csv') o.description = o.description || null;
			csvRows.push(o);
		}
		const { rows: dbRows } = await pool.query(`SELECT ${cols.join(', ')} FROM public.${table} ORDER BY slug`);
		if (csvRows.length !== dbRows.length) {
			throw new Error(`${file} vs ${table}: row count ${csvRows.length} (CSV) !== ${dbRows.length} (DB)`);
		}
		const normDb = (db) => {
			const o = { ...db };
			if (file === 'distances.csv') {
				o.km = String(o.km);
				o.description = o.description == null ? '' : String(o.description);
			}
			return o;
		};
		const csvBySlug = new Map(csvRows.map((r) => [r.slug, r]));
		for (const db of dbRows.map(normDb)) {
			const c = csvBySlug.get(db.slug);
			if (!c) throw new Error(`${table}: DB has slug ${db.slug} missing in CSV`);
			for (const col of cols) {
				const cv = col === 'description' && !c[col] ? '' : String(c[col] ?? '');
				const dv =
					col === 'km'
						? String(db[col])
						: col === 'description'
							? db[col] == null
								? ''
								: String(db[col])
							: String(db[col] ?? '');
				if (cv !== dv) {
					throw new Error(`${table} slug=${db.slug}: column ${col} CSV=${JSON.stringify(cv)} DB=${JSON.stringify(dv)}`);
				}
			}
		}
	}
}

async function main() {
	const pool = new pg.Pool({ connectionString: databaseUrl(), max: 1 });
	try {
		await compareReferenceTables(pool);
		const csvRaces = loadRacesFromCsv();
		const dbRaces = await loadRacesFromDb(pool);

		if (csvRaces.size !== dbRaces.size) {
			const onlyCsv = [...csvRaces.keys()].filter((k) => !dbRaces.has(k));
			const onlyDb = [...dbRaces.keys()].filter((k) => !csvRaces.has(k));
			throw new Error(
				`races.csv vs public.races: count ${csvRaces.size} !== ${dbRaces.size}. Only CSV: ${onlyCsv.slice(0, 5).join(', ')} Only DB: ${onlyDb.slice(0, 5).join(', ')}`,
			);
		}

		for (const [k, csvRow] of csvRaces) {
			const dbRow = dbRaces.get(k);
			if (!dbRow) {
				throw new Error(`Missing in DB for CSV detailUrl (normalized): ${k}`);
			}
			const cmp = rowEqual(csvRow, dbRow);
			if (!cmp.ok) {
				throw new Error(
					`Mismatch detailUrl ${csvRow.detailUrl}: field ${cmp.field} CSV=${JSON.stringify(cmp.left)} DB=${JSON.stringify(cmp.right)}`,
				);
			}
		}

		console.log(
			`compare-db-to-csv: OK — providers, types, distances, and ${csvRaces.size} race(s) match.`,
		);
	} finally {
		await pool.end();
	}
}

main().catch((e) => {
	console.error(e.message || e);
	process.exit(1);
});
