import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The Core API (FastAPI, :8002) is proxied so the browser sees one origin.
const api = process.env.API_URL ?? 'http://127.0.0.1:8002'
const routes = ['/reports', '/stats', '/map', '/messages', '/conversations', '/assistant', '/static', '/health']

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: Object.fromEntries(routes.map((r) => [r, api])) },
})
