import { defineConfig } from 'vite';
import path from 'path';
import vue from '@vitejs/plugin-vue';
import type { IncomingMessage, ServerResponse } from 'http';
import http from 'http';

import tailwindcss from '@tailwindcss/vite';
import autoprefixer from 'autoprefixer';

const API_TARGET = process.env.VITE_API_URL || 'http://127.0.0.1:8000';

// https://vitejs.dev/config/
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  publicDir: 'public',
  css: {
    postcss: {
      plugins: [autoprefixer()],
    },
  },
  plugins: [
    vue(),
    tailwindcss(),
    // Custom plugin to handle SSE proxying (bypasses http-proxy buffering)
    {
      name: 'sse-proxy',
      configureServer(server) {
        server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
          if (!req.url?.includes('/stream')) {
            return next();
          }
          // Only handle /api paths that contain /stream
          if (!req.url?.startsWith('/api')) {
            return next();
          }

          const targetUrl = new URL(req.url, API_TARGET);
          console.log(`[SSE Proxy] ${req.method} ${req.url} -> ${targetUrl.href}`);

          const proxyReq = http.request(
            {
              hostname: targetUrl.hostname,
              port: Number(targetUrl.port) || 8000,
              path: targetUrl.pathname + targetUrl.search,
              method: req.method || 'GET',
              headers: {
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Accept-Encoding': 'identity',
              },
            },
            (proxyRes) => {
            res.writeHead(proxyRes.statusCode || 200, {
              'Content-Type': 'text/event-stream; charset=utf-8',
              'Cache-Control': 'no-cache',
              'Connection': 'keep-alive',
              'X-Accel-Buffering': 'no',
              'Access-Control-Allow-Origin': '*',
            });
            // Pipe response directly — no buffering
            proxyRes.on('data', (chunk: Buffer) => {
              res.write(chunk);
            });
            proxyRes.on('end', () => {
              res.end();
            });
          });

          proxyReq.on('error', (err: Error) => {
            console.error('[SSE Proxy] Error:', err.message);
            if (!res.headersSent) {
              res.writeHead(502);
              res.end('SSE proxy error');
            }
          });

          // If client disconnects, abort the proxy request
          req.on('close', () => {
            proxyReq.destroy();
          });

          // GET requests: just end the request. POST: pipe the body.
          if (req.method === 'GET' || req.method === 'HEAD') {
            proxyReq.end();
          } else {
            req.pipe(proxyReq);
          }
        });
      },
    },
  ],
  server: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
    hmr: {
      clientPort: 3000,
      host: 'localhost',
      protocol: 'ws',
      timeout: 120000
    },
    watch: {
      usePolling: true,
      interval: 100
    },
    headers: {
      // Disable caching in development
      'Cache-Control': 'no-store, no-cache, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    },
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 120000,
        proxyTimeout: 120000,
        // Skip SSE streams — handled by the sse-proxy plugin above
        bypass(req) {
          if (req.url?.includes('/stream')) {
            return req.url;
          }
        },
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('proxy error', err);
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
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // Core Vue ecosystem
            if (/\/(vue|vue-router|pinia|@vue)\//.test(id)) return 'vue-vendor';
            // UI primitives (Radix/Reka)
            if (/\/(reka-ui|@floating-ui|@internationalized)\//.test(id)) return 'ui-primitives';
            // Icons
            if (id.includes('lucide-vue-next')) return 'icons';
            // Auth (loaded after paint)
            if (id.includes('@clerk')) return 'clerk';
            // KaTeX (only used on definition pages)
            if (id.includes('katex')) return 'katex';
            // Utilities
            if (/\/(axios|@vueuse)\//.test(id)) return 'utils-vendor';
          }
        },
      },
    },
  },
  optimizeDeps: {
    // Pre-bundle dependencies for faster cold starts
    include: ['vue', 'vue-router', 'pinia'],
  },
});
