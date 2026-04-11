<script lang="ts">
	import {
		formatKmList,
		labelForTypeSlug,
		raceUrl,
		type RaceRow,
	} from '../data/races';

	let { race }: { race: RaceRow } = $props();

	function distancesDisplay(r: RaceRow): string {
		if (r.distancesNote) return r.distancesNote;
		const s = formatKmList(r.distanceSlugs);
		return s ? `${s} km` : '—';
	}

	const typeLabel = $derived(labelForTypeSlug(race.typeSlug) ?? race.typeSlug);
	const href = $derived(raceUrl(race.calendarSlug));
	const distances = $derived(distancesDisplay(race));
</script>

<li class="race-item">
	<div class="race-item__grid">
		<div class="race-item__cell">
			<span class="race-item__label">Date and time</span>
			<span class="race-item__value">{race.dateTimeDisplay}</span>
		</div>
		<div class="race-item__cell">
			<span class="race-item__label">Location</span>
			<span class="race-item__value">{race.city}, {race.state}, {race.country}</span>
		</div>
		<div class="race-item__cell">
			<span class="race-item__label">Name</span>
			<span class="race-item__value">{race.name}</span>
		</div>
		<div class="race-item__cell">
			<span class="race-item__label">Type</span>
			<span class="race-item__value">{typeLabel}</span>
		</div>
		<div class="race-item__cell">
			<span class="race-item__label">Distances (km)</span>
			<span class="race-item__value">{distances}</span>
		</div>
		<div class="race-item__cell">
			<span class="race-item__label">Link</span>
			<span class="race-item__value">
				<a href={href}>{href}</a>
			</span>
		</div>
	</div>
</li>

<style>
	.race-item {
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid #333;
		border-bottom: none;
	}

	.race-item:last-child {
		border-bottom: 1px solid #333;
	}

	.race-item__grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 0;
	}

	@media (max-width: 720px) {
		.race-item__grid {
			grid-template-columns: 1fr;
		}
	}

	.race-item__cell {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		border-right: 1px solid #ccc;
		border-bottom: 1px solid #ccc;
	}

	.race-item__cell:nth-child(3n) {
		border-right: none;
	}

	.race-item__cell:nth-child(n + 4) {
		border-bottom: none;
	}

	@media (max-width: 720px) {
		.race-item__cell {
			border-right: none;
		}

		.race-item__cell:not(:last-child) {
			border-bottom: 1px solid #ccc;
		}
	}

	.race-item__label {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: #444;
	}

	.race-item__value {
		word-break: break-word;
	}
</style>
