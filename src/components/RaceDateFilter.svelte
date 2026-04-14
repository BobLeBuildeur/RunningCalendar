<script lang="ts">
	import { Calendar } from 'lucide';
	import { onMount } from 'svelte';
	import DateRangePicker from './DateRangePicker.svelte';
	import LucideIcon from './LucideIcon.svelte';

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
		<LucideIcon icon={Calendar} class="race-date-filter__label-icon" size={16} aria-hidden={true} />
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
