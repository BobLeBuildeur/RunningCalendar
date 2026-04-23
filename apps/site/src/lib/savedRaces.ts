/**
 * Saved races persistence.
 *
 * Saved races are stored in `localStorage` under a single key as an array of
 * stable race identifiers. A race's identifier is its `detailUrl`, which is
 * the canonical public URL for the race in the data model (see
 * `docs/data-model.md`).
 *
 * This module is safe to import in both browser islands and server-rendered
 * Astro frontmatter: every access guards against a missing `window` /
 * `localStorage` (e.g. during SSR or pre-render).
 */

export const SAVED_RACES_STORAGE_KEY = 'runningcalendar:saved-races';
export const SAVED_RACES_CHANGE_EVENT = 'runningcalendar:saved-change';

/** Detail describing the full post-change set of saved race ids. */
export type SavedRacesChangeDetail = {
	ids: ReadonlySet<string>;
};

function getStorage(): Storage | null {
	if (typeof window === 'undefined') return null;
	try {
		return window.localStorage;
	} catch {
		return null;
	}
}

/** Returns the current saved-race id set. Empty set when storage is unavailable or empty. */
export function readSavedRaces(): Set<string> {
	const storage = getStorage();
	if (!storage) return new Set();
	const raw = storage.getItem(SAVED_RACES_STORAGE_KEY);
	if (!raw) return new Set();
	try {
		const parsed: unknown = JSON.parse(raw);
		if (!Array.isArray(parsed)) return new Set();
		return new Set(parsed.filter((x): x is string => typeof x === 'string' && x.length > 0));
	} catch {
		return new Set();
	}
}

function writeSavedRaces(ids: Set<string>): void {
	const storage = getStorage();
	if (!storage) return;
	storage.setItem(SAVED_RACES_STORAGE_KEY, JSON.stringify(Array.from(ids)));
	if (typeof document !== 'undefined') {
		const detail: SavedRacesChangeDetail = { ids: new Set(ids) };
		document.dispatchEvent(
			new CustomEvent<SavedRacesChangeDetail>(SAVED_RACES_CHANGE_EVENT, { detail }),
		);
	}
}

export function isRaceSaved(id: string): boolean {
	return readSavedRaces().has(id);
}

/** Add a race id to the saved set. No-op if already saved. */
export function saveRace(id: string): void {
	if (!id) return;
	const ids = readSavedRaces();
	if (ids.has(id)) return;
	ids.add(id);
	writeSavedRaces(ids);
}

/** Remove a race id from the saved set. No-op if not present. */
export function unsaveRace(id: string): void {
	if (!id) return;
	const ids = readSavedRaces();
	if (!ids.has(id)) return;
	ids.delete(id);
	writeSavedRaces(ids);
}

/** Toggle a race id; returns the new state (true = saved). */
export function toggleSavedRace(id: string): boolean {
	const ids = readSavedRaces();
	if (ids.has(id)) {
		ids.delete(id);
		writeSavedRaces(ids);
		return false;
	}
	ids.add(id);
	writeSavedRaces(ids);
	return true;
}
