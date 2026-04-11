// @ts-check
import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

// https://astro.build/config
// GitHub project pages: site origin + repo name as path segment
// (see https://docs.astro.build/en/guides/deploy/github/)
export default defineConfig({
	site: 'https://boblebuildeur.github.io',
	base: '/RunningCalendar/',
	integrations: [svelte()],
});
