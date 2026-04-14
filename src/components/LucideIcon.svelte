<script lang="ts">
	import type { IconNode } from 'lucide';
	import defaultAttributes from 'lucide/dist/esm/defaultAttributes.js';

	let {
		icon,
		size = 24,
		strokeWidth = 2,
		class: className = '',
		...rest
	}: {
		icon: IconNode;
		size?: number;
		strokeWidth?: number | string;
		class?: string;
		[key: string]: unknown;
	} = $props();
</script>

<svg
	{...defaultAttributes}
	{...rest}
	width={size}
	height={size}
	stroke-width={strokeWidth}
	class={className}
>
	{#each icon as [tag, attrs], i (i)}
		<svelte:element this={tag} {...attrs} />
	{/each}
</svg>
