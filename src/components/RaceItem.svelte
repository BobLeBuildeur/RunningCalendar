<script lang="ts">
	import Badge from './Badge.svelte';
	import { kmForDistanceSlug, raceUrl, type RaceRow } from '../data/races';

	let { race }: { race: RaceRow } = $props();

	const href = $derived(raceUrl(race.calendarSlug));

	/** Match mock: "26 Apr 2026 • 06:00" from CSV "26 Apr 2026, 06:00" */
	const dateTimeLine = $derived(race.dateTimeDisplay.replace(/,\s*/, ' • '));

	const locationLine = $derived(`${race.city}, ${race.state}, ${race.country}`);

	type DistanceBadge = { label: string };

	function distanceBadges(r: RaceRow): DistanceBadge[] {
		if (r.distancesNote) return [{ label: r.distancesNote }];
		const slugs = r.distanceSlugs;
		if (slugs.length === 0) return [];

		const maxVisible = 3;
		const labels = slugs.map((slug) => {
			const km = kmForDistanceSlug(slug);
			if (km === undefined) return slug;
			const n = km % 1 === 0 ? String(km) : String(km);
			return `${n}km`;
		});

		if (labels.length <= maxVisible) return labels.map((label) => ({ label }));

		const rest = labels.length - maxVisible;
		return [
			...labels.slice(0, maxVisible).map((label) => ({ label })),
			{ label: `+${rest}` },
		];
	}

	const badges = $derived(distanceBadges(race));
</script>

<li class="race-card">
	<article class="race-card__surface">
		<header class="race-card__section race-card__section--header">
			<p class="race-card__datetime">{dateTimeLine}</p>
			{#if badges.length > 0}
				<ul class="race-card__badges" aria-label="Distances">
					{#each badges as b (b.label)}
						<li class="race-card__badge-slot">
							<Badge>{b.label}</Badge>
						</li>
					{/each}
				</ul>
			{/if}
		</header>

		<div class="race-card__section race-card__section--main">
			<h2 class="race-card__title">{race.name}</h2>
			<p class="race-card__location">{locationLine}</p>
		</div>

		<footer class="race-card__section race-card__section--footer">
			<a class="race-card__action" href={href}>
				View Details
				<span class="race-card__action-icon" aria-hidden="true">→</span>
			</a>
		</footer>
	</article>
</li>

<style>
	.race-card {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.race-card__surface {
		background: var(--color-background);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-sm);
		padding: var(--space-lg);
	}

	.race-card__section {
		margin: 0;
	}

	.race-card__section + .race-card__section {
		padding-top: var(--space-md);
		border-top: 1px solid var(--color-border);
	}

	.race-card__section--header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-md);
	}

	.race-card__datetime {
		margin: 0;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-medium);
		color: var(--color-text-secondary);
		line-height: 1.4;
	}

	.race-card__badges {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: var(--space-xs);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.race-card__badge-slot {
		display: inline-block;
	}

	.race-card__section--main {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.race-card__title {
		margin: 0;
		font-size: var(--text-h2);
		font-weight: var(--font-weight-bold);
		color: var(--color-text-primary);
		line-height: 1.25;
	}

	.race-card__location {
		margin: 0;
		font-size: var(--text-body);
		font-weight: var(--font-weight-regular);
		color: var(--color-text-secondary);
		line-height: 1.4;
	}

	.race-card__section--footer {
		display: flex;
		justify-content: flex-end;
	}

	.race-card__action {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-primary);
		text-decoration: none;
		line-height: 1.2;
	}

	.race-card__action:hover {
		color: var(--color-primary-hover);
	}

	.race-card__action:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
		border-radius: var(--radius-sm);
	}

	.race-card__action-icon {
		font-size: 1.1em;
	}
</style>
