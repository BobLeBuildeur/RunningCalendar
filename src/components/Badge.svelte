<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children?: Snippet } = $props();
</script>

<span class="badge">{@render children?.()}</span>

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
	}
</style>
