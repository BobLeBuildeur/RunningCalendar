<script lang="ts">
	import DualRangeSlider from './DualRangeSlider.svelte';

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

	$effect(() => {
		document.dispatchEvent(
			new CustomEvent('runningcalendar:distance', {
				detail: { minKm, maxKm, start, end },
				bubbles: true,
			}),
		);
	});
</script>

<div class="race-distance-filter">
	<p class="race-distance-filter__label" id="{sliderId}-heading">
		<svg
			class="race-distance-filter__label-icon"
			width="16"
			height="16"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			aria-hidden="true"
		>
			<path
				d="M4 19V5M4 19H20M4 19L8 15M4 19L8 23M20 19V5M20 19L16 15M20 19L16 23"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		</svg>
		Distance
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
		formatMaxLabel={() => `${maxKm} km+`}
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
