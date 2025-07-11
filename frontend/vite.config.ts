import { defineConfig } from "vite";
import path from "path";
import vue from "@vitejs/plugin-vue";

// https://vitejs.dev/config/
export default defineConfig({
  base: "/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [
    vue(),
  ],
  server: {
    port: 3000,
    host: true, // Listen on all local IPs
    strictPort: true, // Exit if port is already in use
    hmr: {
      // Ensure HMR works properly
      overlay: true,
    },
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        ws: true, // Proxy websockets
        configure: (proxy, options) => {
          // Proxy error handling
          proxy.on('error', (err, req, res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('Sending Request:', req.method, req.url);
          });
        }
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