#!/usr/bin/env node
/**
 * Validates src/data/*.csv column sets, formats, and FK integrity.
 * Run: node scripts/validate-csv.mjs
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dataDir = join(__dirname, '..', 'src', 'data');

const SLUG_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

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

function assertSlug(name, value, ctx) {
	const t = (value ?? '').trim();
	if (!t) throw new Error(`${ctx}: missing slug for ${name}`);
	if (!SLUG_RE.test(t)) throw new Error(`${ctx}: invalid slug ${name}=${JSON.stringify(t)}`);
}

function assertUrl(name, value, ctx) {
	const t = (value ?? '').trim();
	if (!t) throw new Error(`${ctx}: missing ${name}`);
	try {
		const u = new URL(t);
		if (u.protocol !== 'http:' && u.protocol !== 'https:') throw new Error('bad protocol');
	} catch {
		throw new Error(`${ctx}: invalid URL ${name}=${JSON.stringify(t)}`);
	}
}

function load(name) {
	const raw = readFileSync(join(dataDir, name), 'utf8');
	const matrix = parseCsv(raw.trimEnd());
	if (matrix.length < 1) throw new Error(`${name}: empty file`);
	return matrix;
}

function main() {
	const distanceSlugs = new Set();
	const typeSlugs = new Set();
	const providerSlugs = new Set();

	const mProv = load('providers.csv');
	const hProv = mProv[0].map((h) => h.trim());
	if (hProv.join(',') !== 'slug,name,website') {
		throw new Error(`providers.csv: expected header slug,name,website got ${hProv.join(',')}`);
	}
	for (let r = 1; r < mProv.length; r++) {
		const line = mProv[r];
		if (line.every((c) => !c.trim())) continue;
		const ctx = `providers.csv row ${r + 1}`;
		const slug = line[0]?.trim() ?? '';
		assertSlug('slug', slug, ctx);
		if (providerSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug ${slug}`);
		providerSlugs.add(slug);
		if (!(line[1] ?? '').trim()) throw new Error(`${ctx}: missing name`);
		assertUrl('website', line[2], ctx);
	}
	if (providerSlugs.size === 0) throw new Error('providers.csv: no data rows');

	const mTypes = load('types.csv');
	const hTypes = mTypes[0].map((h) => h.trim());
	if (hTypes.join(',') !== 'slug,type') {
		throw new Error(`types.csv: expected header slug,type got ${hTypes.join(',')}`);
	}
	for (let r = 1; r < mTypes.length; r++) {
		const line = mTypes[r];
		if (line.every((c) => !c.trim())) continue;
		const ctx = `types.csv row ${r + 1}`;
		const slug = line[0]?.trim() ?? '';
		assertSlug('slug', slug, ctx);
		if (typeSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug ${slug}`);
		typeSlugs.add(slug);
		if (!(line[1] ?? '').trim()) throw new Error(`${ctx}: missing type`);
	}
	if (typeSlugs.size === 0) throw new Error('types.csv: no data rows');

	const mDist = load('distances.csv');
	const hDist = mDist[0].map((h) => h.trim());
	if (hDist.join(',') !== 'slug,km,description') {
		throw new Error(`distances.csv: expected header slug,km,description got ${hDist.join(',')}`);
	}
	for (let r = 1; r < mDist.length; r++) {
		const line = mDist[r];
		if (line.every((c) => !c.trim())) continue;
		const ctx = `distances.csv row ${r + 1}`;
		const slug = line[0]?.trim() ?? '';
		assertSlug('slug', slug, ctx);
		if (distanceSlugs.has(slug)) throw new Error(`${ctx}: duplicate slug ${slug}`);
		distanceSlugs.add(slug);
		const kmRaw = (line[1] ?? '').trim();
		if (!kmRaw) throw new Error(`${ctx}: missing km`);
		const km = Number(kmRaw);
		if (!Number.isFinite(km) || !Number.isInteger(km)) {
			throw new Error(`${ctx}: km must be an integer, got ${JSON.stringify(kmRaw)}`);
		}
	}
	if (distanceSlugs.size === 0) throw new Error('distances.csv: no data rows');

	const mRace = load('races.csv');
	const header = mRace[0].map((h) => h.trim());
	const expected = [
		'sortKey',
		'city',
		'state',
		'country',
		'name',
		'typeSlug',
		'distanceSlugs',
		'providerSlug',
		'detailUrl',
	];
	if (header.length !== expected.length || header.some((h, i) => h !== expected[i])) {
		throw new Error(`races.csv: expected header ${expected.join(',')} got ${header.join(',')}`);
	}
	const isoRe = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
	for (let r = 1; r < mRace.length; r++) {
		const line = mRace[r];
		if (line.every((c) => !c.trim())) continue;
		const ctx = `races.csv row ${r + 1}`;
		const sortKey = line[0]?.trim() ?? '';
		if (!isoRe.test(sortKey)) {
			throw new Error(`${ctx}: sortKey must be ISO date-time YYYY-MM-DDTHH:MM, got ${JSON.stringify(sortKey)}`);
		}
		for (let j = 1; j <= 4; j++) {
			if (!(line[j] ?? '').trim()) throw new Error(`${ctx}: missing field at column ${j + 1}`);
		}
		const typeSlug = ((line[5] ?? '').trim() || 'road');
		assertSlug('typeSlug', typeSlug, ctx);
		if (!typeSlugs.has(typeSlug)) throw new Error(`${ctx}: unknown typeSlug ${typeSlug}`);

		const distCell = (line[6] ?? '').trim();
		if (distCell) {
			for (const part of distCell.split(';')) {
				const s = part.trim();
				if (!s) continue;
				assertSlug('distanceSlugs token', s, ctx);
				if (!distanceSlugs.has(s)) throw new Error(`${ctx}: unknown distance slug ${s}`);
			}
		}

		const providerSlug = line[7]?.trim() ?? '';
		assertSlug('providerSlug', providerSlug, ctx);
		if (!providerSlugs.has(providerSlug)) throw new Error(`${ctx}: unknown providerSlug ${providerSlug}`);

		assertUrl('detailUrl', line[8], ctx);
	}

	console.log('validate-csv: OK');
}

main();
