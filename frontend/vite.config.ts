import react from '@vitejs/plugin-react'
import path from 'node:path'
import { defineConfig } from 'vite'

// The dev server proxies /api to the FastAPI backend so the frontend can use
// same-origin relative URLs (including SSE streaming and PDF file links).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
