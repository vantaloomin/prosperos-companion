import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Libraries change rarely, so they get their own chunks the browser can keep cached. Icons share
// one chunk rather than a file per icon for each lazily loaded view.
const VENDOR = ['react', 'react-dom', 'scheduler', '@tanstack/react-query']

// Port 5175 and backend 8775 keep the Companion clear of Prospero's Study (5173 and 8765).
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const match = id.match(/node_modules[\\/]((?:@[^\\/]+[\\/])?[^\\/]+)[\\/]/)
          const name = match?.[1].replace('\\', '/')
          if (name === 'lucide-react') return 'icons'
          if (name && VENDOR.includes(name)) return 'vendor'
        },
      },
    },
  },
  server: {
    port: 5175,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8775' },
  },
})
