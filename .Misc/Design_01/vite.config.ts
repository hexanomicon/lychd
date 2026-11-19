import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Pre-bundle everything up front so a dependency discovered mid-session
  // cannot produce a second copy of React in the dev server.
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-dom/client', 'react-router-dom', 'lucide-react'],
  },
  resolve: { dedupe: ['react', 'react-dom'] },
})
