/**
 * Reads src/data/*.csv and prints SQL INSERTs for Supabase (public schema).
 * Run: node scripts/generate-supabase-seed-sql.mjs > /tmp/seed.sql
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, '..', 'src', 'data');

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

function sqlLiteral(s) {
	return `'${String(s).replace(/'/g, "''")}'`;
}

function headerIndex(header, name) {
	const j = header.indexOf(name);
	if (j === -1) throw new Error(`Missing column: ${name}`);
	return j;
}

const providersCsv = readFileSync(join(dataDir, 'providers.csv'), 'utf8');
const typesCsv = readFileSync(join(dataDir, 'types.csv'), 'utf8');
const distancesCsv = readFileSync(join(dataDir, 'distances.csv'), 'utf8');
const racesCsv = readFileSync(join(dataDir, 'races.csv'), 'utf8');

const providersM = parseCsv(providersCsv.trimEnd());
const typesM = parseCsv(typesCsv.trimEnd());
const distancesM = parseCsv(distancesCsv.trimEnd());
const racesM = parseCsv(racesCsv.trimEnd());

console.log('BEGIN;');
console.log('TRUNCATE TABLE public.race_distances, public.races, public.distances, public.types, public.providers RESTART IDENTITY CASCADE;');

const ph = providersM[0].map((h) => h.trim());
const pi = { slug: headerIndex(ph, 'slug'), name: headerIndex(ph, 'name'), website: headerIndex(ph, 'website') };
for (let r = 1; r < providersM.length; r++) {
	const line = providersM[r];
	if (line.every((c) => !c.trim())) continue;
	const slug = (line[pi.slug] ?? '').trim();
	if (!slug) continue;
	console.log(
		`INSERT INTO public.providers (slug, name, website) VALUES (${sqlLiteral(slug)}, ${sqlLiteral((line[pi.name] ?? '').trim())}, ${sqlLiteral((line[pi.website] ?? '').trim())});`,
	);
}

const th = typesM[0].map((h) => h.trim());
const ti = { slug: headerIndex(th, 'slug'), type: headerIndex(th, 'type') };
for (let r = 1; r < typesM.length; r++) {
	const line = typesM[r];
	if (line.every((c) => !c.trim())) continue;
	const slug = (line[ti.slug] ?? '').trim();
	if (!slug) continue;
	console.log(`INSERT INTO public.types (slug, type) VALUES (${sqlLiteral(slug)}, ${sqlLiteral((line[ti.type] ?? '').trim())});`);
}

const dh = distancesM[0].map((h) => h.trim());
const di = { slug: headerIndex(dh, 'slug'), km: headerIndex(dh, 'km') };
const descJ = dh.indexOf('description');
for (let r = 1; r < distancesM.length; r++) {
	const line = distancesM[r];
	if (line.every((c) => !c.trim())) continue;
	const slug = (line[di.slug] ?? '').trim();
	if (!slug) continue;
	const km = (line[di.km] ?? '').trim();
	const desc = descJ >= 0 ? (line[descJ] ?? '').trim() : '';
	const descSql = desc ? sqlLiteral(desc) : 'NULL';
	console.log(
		`INSERT INTO public.distances (slug, km, description) VALUES (${sqlLiteral(slug)}, ${km}, ${descSql});`,
	);
}

const rh = racesM[0].map((h) => h.trim());
const ri = {
	sortKey: headerIndex(rh, 'sortKey'),
	city: headerIndex(rh, 'city'),
	state: headerIndex(rh, 'state'),
	country: headerIndex(rh, 'country'),
	name: headerIndex(rh, 'name'),
	typeSlug: headerIndex(rh, 'typeSlug'),
	distanceSlugs: headerIndex(rh, 'distanceSlugs'),
	providerSlug: headerIndex(rh, 'providerSlug'),
	detailUrl: headerIndex(rh, 'detailUrl'),
};

for (let r = 1; r < racesM.length; r++) {
	const line = racesM[r];
	if (line.every((c) => !c.trim())) continue;
	const typeSlug = ((line[ri.typeSlug] ?? '').trim() || 'road');
	const detailUrl = (line[ri.detailUrl] ?? '').trim();
	console.log(
		`INSERT INTO public.races (sort_key, city, state, country, name, type_slug, provider_slug, detail_url) VALUES (${sqlLiteral(line[ri.sortKey].trim())}, ${sqlLiteral(line[ri.city].trim())}, ${sqlLiteral(line[ri.state].trim())}, ${sqlLiteral(line[ri.country].trim())}, ${sqlLiteral(line[ri.name].trim())}, ${sqlLiteral(typeSlug)}, ${sqlLiteral((line[ri.providerSlug] ?? '').trim())}, ${sqlLiteral(detailUrl)});`,
	);
	const cell = (line[ri.distanceSlugs] ?? '').trim();
	if (!cell) continue;
	const slugs = cell.split(';').map((s) => s.trim()).filter(Boolean);
	for (const ds of slugs) {
		console.log(
			`INSERT INTO public.race_distances (race_id, distance_slug) SELECT id, ${sqlLiteral(ds)} FROM public.races WHERE detail_url = ${sqlLiteral(detailUrl)};`,
		);
	}
}

console.log('COMMIT;');
