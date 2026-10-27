import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // backend FastAPI (backend/api.py)
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (caminho) => caminho.replace(/^\/api/, ''),
      },
    },
  },
})
