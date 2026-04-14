<script lang="ts">
	import { onMount } from 'svelte';
	import DateRangePicker from './DateRangePicker.svelte';

	let {
		fieldId = 'race-date-filter',
	}: {
		fieldId?: string;
	} = $props();

	let hydrated = $state(false);

	onMount(() => {
		hydrated = true;
	});
</script>

<div
	class="race-date-filter"
	data-testid="race-date-filter"
	data-hydrated={hydrated ? 'true' : 'false'}
>
	<p class="race-date-filter__label" id="{fieldId}-heading">
		<svg
			class="race-date-filter__label-icon"
			width="16"
			height="16"
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
			aria-hidden="true"
		>
			<rect x="3" y="5" width="18" height="16" rx="2" stroke="currentColor" stroke-width="2" />
			<path d="M3 10h18" stroke="currentColor" stroke-width="2" />
			<path d="M8 3v4M16 3v4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
		</svg>
		Date
	</p>
	<DateRangePicker id={fieldId} labelledBy="{fieldId}-heading" />
</div>

<style>
	.race-date-filter {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
		width: 100%;
	}

	.race-date-filter__label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		margin: 0;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		line-height: 1.3;
	}

	.race-date-filter__label-icon {
		flex-shrink: 0;
		color: var(--color-primary);
	}
</style>
