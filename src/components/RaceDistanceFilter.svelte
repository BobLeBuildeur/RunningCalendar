<script lang="ts">
	import { SportShoe } from 'lucide';
	import { onMount } from 'svelte';
	import { captureEvent, SOURCE_PAGE } from '../lib/analytics';
	import DualRangeSlider from './DualRangeSlider.svelte';
	import LucideIcon from './LucideIcon.svelte';

	let {
		minKm,
		maxKm,
		step = 0.1,
		sliderId = 'race-distance-slider',
	}: {
		minKm: number;
		maxKm: number;
		step?: number;
		sliderId?: string;
	} = $props();

	function formatKm(v: number): string {
		const n = v % 1 === 0 ? String(v) : String(v);
		return `${n} km`;
	}

	function formatRange(s: number, e: number): string {
		const atMax = e >= maxKm - 1e-6;
		if (atMax) {
			return `${formatKm(s)} — ${formatKm(maxKm)} ou mais`;
		}
		return `${formatKm(s)} — ${formatKm(e)}`;
	}

	let start = $state(minKm);
	let end = $state(maxKm);
	let hydrated = $state(false);
	/** Skip analytics on the first $effect run (initial hydration sync). */
	let distanceAnalyticsReady = $state(false);

	onMount(() => {
		hydrated = true;
		function onDistanceFromBadge(e: Event) {
			const ce = e as CustomEvent<{ km?: unknown }>;
			const raw = ce.detail?.km;
			if (typeof raw !== 'number' || !Number.isFinite(raw)) return;
			const k = Math.min(Math.max(raw, minKm), maxKm);
			start = k;
			end = k;
		}
		document.addEventListener('runningcalendar:distance-from-badge', onDistanceFromBadge);
		return () => document.removeEventListener('runningcalendar:distance-from-badge', onDistanceFromBadge);
	});

	$effect(() => {
		document.dispatchEvent(
			new CustomEvent('runningcalendar:distance', {
				detail: { minKm, maxKm, start, end },
				bubbles: true,
			}),
		);
		if (!distanceAnalyticsReady) {
			distanceAnalyticsReady = true;
			return;
		}
		captureEvent('distance_range_selected', {
			distance_min_km: start,
			distance_max_km: end,
			source_page: SOURCE_PAGE,
		});
	});
</script>

<div
	class="race-distance-filter"
	data-testid="race-distance-filter"
	data-hydrated={hydrated ? 'true' : 'false'}
>
	<p class="race-distance-filter__label" id="{sliderId}-heading" data-rc-filter-label="distance">
		<LucideIcon icon={SportShoe} class="race-distance-filter__label-icon" size={16} aria-hidden={true} />
		Distância
	</p>
	<DualRangeSlider
		id={sliderId}
		labelledBy="{sliderId}-heading"
		min={minKm}
		max={maxKm}
		bind:start
		bind:end
		{step}
		formatValue={formatKm}
		formatMinLabel={() => `${minKm} km`}
		formatMaxLabel={() => `${maxKm} km ou mais`}
		formatRange={formatRange}
	/>
</div>

<style>
	.race-distance-filter {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
		width: 100%;
	}

	.race-distance-filter__label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		margin: 0;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		line-height: 1.3;
	}

	.race-distance-filter__label-icon {
		flex-shrink: 0;
		color: var(--color-primary);
	}
</style>
