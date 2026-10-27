import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    // Cloudflare Quick Tunnel: o subdomínio muda a cada execução do cloudflared
    allowedHosts: ['.trycloudflare.com'],
    proxy: {
      // backend FastAPI (backend/api.py)
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (caminho) => caminho.replace(/^\/api/, ''),
      },
    },
  },
})
