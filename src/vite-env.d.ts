/// <reference types="astro/client" />

interface ImportMetaEnv {
	readonly PUBLIC_POSTHOG_KEY?: string;
	/** PostHog ingest host (e.g. https://us.i.posthog.com). Defaults in code if unset. */
	readonly PUBLIC_POSTHOG_HOST?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
