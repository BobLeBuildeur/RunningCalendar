<script lang="ts">
	import { onMount } from 'svelte';
	import { initPosthog } from '../lib/analytics';

	onMount(() => {
		initPosthog();
	});
</script>
