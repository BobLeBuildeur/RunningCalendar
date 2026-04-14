<script lang="ts">
	import { MoveHorizontal } from 'lucide';
	import { onMount } from 'svelte';
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
		return `${formatKm(s)} — ${formatKm(e)}`;
	}

	let start = $state(minKm);
	let end = $state(maxKm);
	let hydrated = $state(false);

	onMount(() => {
		hydrated = true;
	});

	$effect(() => {
		document.dispatchEvent(
			new CustomEvent('runningcalendar:distance', {
				detail: { minKm, maxKm, start, end },
				bubbles: true,
			}),
		);
	});
</script>

<div
	class="race-distance-filter"
	data-testid="race-distance-filter"
	data-hydrated={hydrated ? 'true' : 'false'}
>
	<p class="race-distance-filter__label" id="{sliderId}-heading">
		<LucideIcon icon={MoveHorizontal} class="race-distance-filter__label-icon" size={16} aria-hidden={true} />
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
