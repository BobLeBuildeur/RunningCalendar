<script lang="ts">
	import { Heart } from 'lucide';
	import { onMount } from 'svelte';
	import { captureFilterSelectionEvent, SOURCE_PAGE } from '../lib/analytics';
	import LucideIcon from './LucideIcon.svelte';

	let {
		fieldId = 'race-saved-filter',
	}: {
		fieldId?: string;
	} = $props();

	let checked = $state(false);
	let hydrated = $state(false);

	onMount(() => {
		hydrated = true;
	});

	function dispatch(next: boolean): void {
		document.dispatchEvent(
			new CustomEvent('runningcalendar:savedfilter', {
				detail: { active: next },
				bubbles: true,
			}),
		);
	}

	function onChange(event: Event): void {
		const target = event.currentTarget as HTMLInputElement;
		checked = target.checked;
		dispatch(checked);
		captureFilterSelectionEvent('saved_filter_selected', {
			saved_only: checked,
			source_page: SOURCE_PAGE,
		});
	}
</script>

<div
	class="race-saved-filter"
	data-testid="race-saved-filter"
	data-hydrated={hydrated ? 'true' : 'false'}
>
	<p class="race-saved-filter__label" id="{fieldId}-heading" data-rc-filter-label="saved">
		<LucideIcon
			icon={Heart}
			class="race-saved-filter__label-icon"
			size={16}
			aria-hidden={true}
		/>
		Salvas
	</p>
	<label class="race-saved-filter__control" for={fieldId}>
		<input
			id={fieldId}
			type="checkbox"
			class="race-saved-filter__checkbox"
			aria-labelledby="{fieldId}-heading"
			checked={checked}
			onchange={onChange}
		/>
		<span class="race-saved-filter__text">Somente corridas salvas</span>
	</label>
</div>

<style>
	.race-saved-filter {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		min-width: 0;
		width: 100%;
	}

	.race-saved-filter__label {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		margin: 0;
		font-size: var(--text-meta);
		font-weight: var(--font-weight-semibold);
		color: var(--color-text-primary);
		line-height: 1.3;
	}

	.race-saved-filter__label-icon {
		flex-shrink: 0;
		color: var(--color-primary);
	}

	.race-saved-filter__control {
		display: inline-flex;
		align-items: center;
		gap: var(--space-sm);
		padding: var(--space-sm) var(--space-md);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		background: var(--color-background);
		color: var(--color-text-primary);
		font-size: var(--text-body);
		line-height: 1.4;
		cursor: pointer;
	}

	.race-saved-filter__control:hover {
		border-color: var(--color-primary);
	}

	.race-saved-filter__control:focus-within {
		border-color: var(--color-primary);
		box-shadow: 0 0 0 3px rgb(11 110 79 / 18%);
	}

	.race-saved-filter__checkbox {
		width: 1rem;
		height: 1rem;
		margin: 0;
		accent-color: var(--color-primary);
		cursor: pointer;
	}

	.race-saved-filter__text {
		font-size: var(--text-meta);
		color: var(--color-text-primary);
	}
</style>
