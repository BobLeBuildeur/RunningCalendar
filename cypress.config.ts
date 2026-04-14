import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://127.0.0.1:4321',
		supportFile: false,
		specPattern: 'cypress/e2e/**/*.cy.ts',
		video: true,
		videosFolder: 'artifacts/ui/cypress-videos',
	},
});
