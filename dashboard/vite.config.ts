import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// In dev, the Core API is proxied so the browser sees one origin. In
// production, set VITE_API_BASE_URL to the API's URL (CORS_ORIGINS on the API
// must list this site).
const api = process.env.API_URL ?? 'http://127.0.0.1:8000'
const routes = ['/reports', '/devices', '/detect', '/potholes', '/map', '/authorities', '/export', '/analytics',
  '/weather', '/offices', '/auth', '/public', '/messages', '/conversations', '/assistant', '/static', '/health']

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: Object.fromEntries(routes.map((r) => [r, api])) },
  build: { chunkSizeWarningLimit: 700 },
  test: { environment: 'node', include: ['src/**/*.test.ts'] },
})
