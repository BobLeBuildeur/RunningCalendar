<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		children,
		interactive = false,
		...rest
	}: {
		children?: Snippet;
		/** When true, render a button (keyboard-accessible) and pointer cursor. */
		interactive?: boolean;
		[key: string]: unknown;
	} = $props();
</script>

{#if interactive}
	<button type="button" class="badge badge--interactive" {...rest}>
		{@render children?.()}
	</button>
{:else}
	<span class="badge" {...rest}>{@render children?.()}</span>
{/if}

<style>
	.badge {
		display: inline-block;
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--radius-lg);
		font-size: var(--text-caption);
		font-weight: var(--font-weight-medium);
		line-height: 1.2;
		color: var(--color-text-primary);
		background: color-mix(in srgb, var(--color-secondary) 30%, var(--color-background));
		border: none;
		font: inherit;
		text-align: inherit;
	}

	.badge--interactive {
		cursor: pointer;
	}

	.badge--interactive:hover {
		background: color-mix(in srgb, var(--color-secondary) 45%, var(--color-background));
	}

	.badge--interactive:focus-visible {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}
</style>
