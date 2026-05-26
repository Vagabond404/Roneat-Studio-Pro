import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/eel.js': 'http://localhost:8000',
      '/eel': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    outDir: '../web',
    emptyOutDir: true,
  }
})
