/// <reference types="astro/client" />

declare module '*.csv?raw' {
	const src: string;
	export default src;
}
