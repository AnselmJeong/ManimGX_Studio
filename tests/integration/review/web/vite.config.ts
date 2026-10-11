import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  // `bun run dev` serves the panel with hot reload; the API is the FastAPI server
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
