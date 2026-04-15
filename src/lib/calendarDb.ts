/**
 * Load calendar entities from PostgreSQL (Supabase) at build time.
 * Uses the same public schema as documented in docs/data-model.md.
 */
import pg from 'pg';

export type DbDistanceRow = { slug: string; km: number; description: string | null };
export type DbTypeRow = { slug: string; type: string };
export type DbProviderRow = { slug: string; name: string; website: string };
export type DbRaceRow = {
	sort_key: string;
	city: string;
	state: string;
	country: string;
	name: string;
	type_slug: string;
	provider_slug: string;
	detail_url: string;
	distance_slugs: string[] | null;
};

function databaseUrl(): string {
	const u =
		(process.env.RUNNINGCALENDAR_DATABASE_URL || process.env.DATABASE_URL || process.env.SUPABASE_DB_URL || '')
			.trim();
	if (!u) {
		throw new Error(
			'Set RUNNINGCALENDAR_DATABASE_URL, DATABASE_URL, or SUPABASE_DB_URL to your Supabase PostgreSQL connection string (session mode URI from Project Settings → Database).',
		);
	}
	return u;
}

export async function loadCalendarFromDatabase(): Promise<{
	distances: DbDistanceRow[];
	types: DbTypeRow[];
	providers: DbProviderRow[];
	races: DbRaceRow[];
}> {
	const pool = new pg.Pool({
		connectionString: databaseUrl(),
		max: 1,
	});
	try {
		const [distRes, typeRes, provRes, raceRes] = await Promise.all([
			pool.query<{
				slug: string;
				km: string | number;
				description: string | null;
			}>(`SELECT slug, km, description FROM public.distances ORDER BY slug`),
			pool.query<{ slug: string; type: string }>(`SELECT slug, type FROM public.types ORDER BY slug`),
			pool.query<{ slug: string; name: string; website: string }>(
				`SELECT slug, name, website FROM public.providers ORDER BY slug`,
			),
			pool.query<{
				sort_key: string;
				city: string;
				state: string;
				country: string;
				name: string;
				type_slug: string;
				provider_slug: string;
				detail_url: string;
				distance_slugs: string[] | null;
			}>(`
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
			`),
		]);

		const distances: DbDistanceRow[] = distRes.rows.map((row) => ({
			slug: row.slug,
			km: typeof row.km === 'number' ? row.km : Number(row.km),
			description: row.description,
		}));

		return {
			distances,
			types: typeRes.rows,
			providers: provRes.rows,
			races: raceRes.rows.map((r) => ({
				...r,
				distance_slugs: r.distance_slugs ?? [],
			})),
		};
	} finally {
		await pool.end();
	}
}
