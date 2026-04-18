<script lang="ts">
	/**
	 * SSR-only heart toggle. Interactivity (read/write `localStorage`, toggle
	 * visual state, dispatch change events) is handled by delegated inline JS in
	 * `src/pages/index.astro` so that we do not have to hydrate a Svelte island
	 * for every race card. See `src/lib/savedRaces.ts` for the shared storage
	 * contract (key + change-event name). All styles for `.save-race` live in
	 * `src/styles/global.css` so state selectors such as `[data-saved='true']`
	 * match the button reliably after client-side upgrades.
	 */
	import { Heart } from 'lucide';
	import LucideIcon from './LucideIcon.svelte';

	let {
		raceId,
		raceName,
		size = 20,
	}: {
		raceId: string;
		raceName?: string;
		size?: number;
	} = $props();

	const baseAriaLabel = raceName
		? `Salvar ${raceName} nas corridas salvas`
		: 'Salvar nas corridas salvas';
	const savedAriaLabel = raceName
		? `Remover ${raceName} das corridas salvas`
		: 'Remover das corridas salvas';
</script>

<button
	type="button"
	class="save-race"
	data-testid="save-race-button"
	data-race-id={raceId}
	data-race-name={raceName ?? ''}
	data-saved="false"
	aria-pressed="false"
	aria-label={baseAriaLabel}
	data-label-save={baseAriaLabel}
	data-label-unsave={savedAriaLabel}
	title="Salvar corrida"
>
	<LucideIcon
		icon={Heart}
		{size}
		class="save-race__icon"
		fill="none"
		aria-hidden={true}
	/>
</button>
