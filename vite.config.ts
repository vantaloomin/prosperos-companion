import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Port 5175 and backend 8775 keep the Companion clear of Prospero's Study (5173 and 8765).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5175,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8775' },
  },
})
