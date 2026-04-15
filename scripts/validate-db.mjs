#!/usr/bin/env node
/**
 * Validates public.providers, public.types, public.distances, public.races, public.race_distances:
 * slug formats, URLs, sortKey shape, and FK integrity (matches former CSV validation rules).
 * Requires RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL.
 */

import pg from 'pg';

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

const SLUG_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const ISO_SORT = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

function assertSlug(ctx, name, value) {
	const t = (value ?? '').trim();
	if (!t) throw new Error(`${ctx}: missing ${name}`);
	if (!SLUG_RE.test(t)) throw new Error(`${ctx}: invalid slug ${name}=${JSON.stringify(t)}`);
}

function assertUrl(ctx, name, value) {
	const t = (value ?? '').trim();
	if (!t) throw new Error(`${ctx}: missing ${name}`);
	try {
		const u = new URL(t);
		if (u.protocol !== 'http:' && u.protocol !== 'https:') throw new Error('bad protocol');
	} catch {
		throw new Error(`${ctx}: invalid URL ${name}=${JSON.stringify(t)}`);
	}
}

async function main() {
	const pool = new pg.Pool({ connectionString: databaseUrl(), max: 1 });
	try {
		const { rows: provRows } = await pool.query(
			`SELECT slug, name, website FROM public.providers ORDER BY slug`,
		);
		const providerSlugs = new Set();
		for (let i = 0; i < provRows.length; i++) {
			const r = provRows[i];
			const ctx = `providers row ${i + 1} (${r.slug})`;
			assertSlug(ctx, 'slug', r.slug);
			const slug = String(r.slug).trim();
			if (providerSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug`);
			providerSlugs.add(slug);
			if (!(r.name ?? '').toString().trim()) throw new Error(`${ctx}: missing name`);
			assertUrl(ctx, 'website', r.website);
		}
		if (providerSlugs.size === 0) throw new Error('providers: no rows');

		const { rows: typeRows } = await pool.query(`SELECT slug, type FROM public.types ORDER BY slug`);
		const typeSlugs = new Set();
		for (let i = 0; i < typeRows.length; i++) {
			const r = typeRows[i];
			const ctx = `types row ${i + 1} (${r.slug})`;
			assertSlug(ctx, 'slug', r.slug);
			const slug = String(r.slug).trim();
			if (typeSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug`);
			typeSlugs.add(slug);
			if (!(r.type ?? '').toString().trim()) throw new Error(`${ctx}: missing type`);
		}
		if (typeSlugs.size === 0) throw new Error('types: no rows');

		const { rows: distRows } = await pool.query(
			`SELECT slug, km, description FROM public.distances ORDER BY slug`,
		);
		const distanceSlugs = new Set();
		for (let i = 0; i < distRows.length; i++) {
			const r = distRows[i];
			const ctx = `distances row ${i + 1} (${r.slug})`;
			assertSlug(ctx, 'slug', r.slug);
			const slug = String(r.slug).trim();
			if (distanceSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug`);
			distanceSlugs.add(slug);
			const km = Number(r.km);
			if (!Number.isFinite(km) || !Number.isInteger(km)) {
				throw new Error(`${ctx}: km must be an integer tenths-of-km, got ${JSON.stringify(r.km)}`);
			}
		}
		if (distanceSlugs.size === 0) throw new Error('distances: no rows');

		const { rows: raceRows } = await pool.query(`
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
						SELECT string_agg(rd.distance_slug, ';' ORDER BY d.km)
						FROM public.race_distances rd
						INNER JOIN public.distances d ON d.slug = rd.distance_slug
						WHERE rd.race_id = r.id
					),
					''
				) AS distance_slugs_cell
			FROM public.races r
			ORDER BY r.sort_key
		`);

		const detailUrls = new Set();
		for (let i = 0; i < raceRows.length; i++) {
			const line = raceRows[i];
			const ctx = `races row ${i + 1} (${line.detail_url})`;
			const sortKey = String(line.sort_key ?? '').trim();
			if (!ISO_SORT.test(sortKey)) {
				throw new Error(`${ctx}: sort_key must be YYYY-MM-DDTHH:MM, got ${JSON.stringify(sortKey)}`);
			}
			for (const col of ['city', 'state', 'country', 'name']) {
				if (!(line[col] ?? '').toString().trim()) throw new Error(`${ctx}: missing ${col}`);
			}
			const typeSlug = (String(line.type_slug ?? '').trim() || 'road');
			assertSlug(ctx, 'type_slug', typeSlug);
			if (!typeSlugs.has(typeSlug)) throw new Error(`${ctx}: unknown type_slug ${typeSlug}`);

			const distCell = String(line.distance_slugs_cell ?? '').trim();
			if (distCell) {
				for (const part of distCell.split(';')) {
					const s = part.trim();
					if (!s) continue;
					assertSlug(ctx, 'distance slug', s);
					if (!distanceSlugs.has(s)) throw new Error(`${ctx}: unknown distance slug ${s}`);
				}
			}

			assertSlug(ctx, 'provider_slug', line.provider_slug);
			const providerSlug = String(line.provider_slug).trim();
			if (!providerSlugs.has(providerSlug)) throw new Error(`${ctx}: unknown provider_slug ${providerSlug}`);

			assertUrl(ctx, 'detail_url', line.detail_url);
			const du = String(line.detail_url).trim();
			if (detailUrls.has(du)) throw new Error(`${ctx}: duplicate detail_url`);
			detailUrls.add(du);
		}

		const { rows: orphanRd } = await pool.query(`
			SELECT rd.race_id, rd.distance_slug
			FROM public.race_distances rd
			LEFT JOIN public.races r ON r.id = rd.race_id
			WHERE r.id IS NULL
			LIMIT 5
		`);
		if (orphanRd.length > 0) {
			throw new Error(`race_distances: orphan race_id (missing races row)`);
		}

		const { rows: badDist } = await pool.query(`
			SELECT rd.distance_slug
			FROM public.race_distances rd
			LEFT JOIN public.distances d ON d.slug = rd.distance_slug
			WHERE d.slug IS NULL
			LIMIT 5
		`);
		if (badDist.length > 0) {
			throw new Error(`race_distances: unknown distance_slug ${badDist[0].distance_slug}`);
		}

		console.log(
			`validate-db: OK — ${providerSlugs.size} provider(s), ${typeSlugs.size} type(s), ${distanceSlugs.size} distance(s), ${raceRows.length} race(s).`,
		);
	} finally {
		await pool.end();
	}
}

main().catch((e) => {
	console.error(e.message || e);
	process.exit(1);
});
