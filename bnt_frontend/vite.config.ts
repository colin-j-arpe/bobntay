import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  // In production the built assets are served from Django's STATIC_URL (/static/),
  // so index.html must reference them as /static/assets/.... In development the
  // Vite dev server serves from /, so React Router can match routes normally.
  base: mode === 'production' ? '/static/' : '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    // In development, proxy API requests to the Django dev server.
    proxy: {
      '/search': 'http://localhost:8000',
      '/parse': 'http://localhost:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
}))
