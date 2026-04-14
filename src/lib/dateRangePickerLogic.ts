/** Calendar day key (YYYY-MM-DD), local date — used for range selection logic. */

export type DateKey = string;

export type OutputState = 'inactive' | 'invalid' | 'valid';

export function outputState(start: DateKey | null, end: DateKey | null): OutputState {
	if (!start && !end) return 'inactive';
	if (start && end) return 'valid';
	return 'invalid';
}

/** Apply a day click given current range; implements the spec’s selection rules. */
export function applyDayClick(
	start: DateKey | null,
	end: DateKey | null,
	day: DateKey,
): { start: DateKey | null; end: DateKey | null } {
	if (!start && !end) {
		return { start: day, end: null };
	}

	if (start && !end) {
		if (day === start) return { start: null, end: null };
		if (day < start) return { start: day, end: start };
		return { start, end: day };
	}

	// both set
	if (day < start!) return { start: day, end };
	if (day === start!) return { start: end!, end: null };
	if (day === end!) return { start, end: null };
	if (day > end!) return { start, end: day };
	// start < day < end
	return { start, end: day };
}

export function pad2(n: number): string {
	return String(n).padStart(2, '0');
}

export function toDateKey(y: number, m0: number, d: number): DateKey {
	return `${y}-${pad2(m0 + 1)}-${pad2(d)}`;
}

export function parseDateKey(key: DateKey): { y: number; m0: number; d: number } | null {
	const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
	if (!m) return null;
	const y = Number(m[1]);
	const mo = Number(m[2]) - 1;
	const d = Number(m[3]);
	if (!Number.isFinite(y) || mo < 0 || mo > 11 || d < 1 || d > 31) return null;
	return { y, m0: mo, d };
}

export function formatMDY(key: DateKey | null): string {
	if (!key) return '';
	const p = parseDateKey(key);
	if (!p) return key;
	const dt = new Date(p.y, p.m0, p.d);
	return new Intl.DateTimeFormat('pt-BR', {
		day: 'numeric',
		month: 'numeric',
		year: 'numeric',
	}).format(dt);
}
