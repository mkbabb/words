import { defineConfig } from 'vite';
import path from 'path';
import vue from '@vitejs/plugin-vue';

import tailwindcss from '@tailwindcss/vite';
import autoprefixer from 'autoprefixer';

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  css: {
    postcss: {
      plugins: [autoprefixer()],
    },
  },
  plugins: [vue(), tailwindcss()],
  server: {
    port: 3000,
    host: true, // Listen on all local IPs
    strictPort: true, // Exit if port is already in use
    hmr: {
      // Ensure HMR works properly
      overlay: true,
    },
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        secure: false,
        ws: true, // Proxy websockets
        configure: (proxy, _options) => {
          // Proxy error handling
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (_proxyReq, req, _res) => {
            console.log('Sending Request:', req.method, req.url);
          });
        },
      },
    },
  },
  build: {
    // Modern build optimizations
    target: 'es2020',
    minify: 'esbuild',
    reportCompressedSize: false, // Faster builds
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Optimize chunking
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
  optimizeDeps: {
    // Pre-bundle dependencies for faster cold starts
    include: ['vue', 'vue-router', 'pinia'],
  },
});
