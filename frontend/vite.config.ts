import { defineConfig } from 'vite';
import path from 'path';
import vue from '@vitejs/plugin-vue';
import type { IncomingMessage, ServerResponse } from 'http';
import http from 'http';

import tailwindcss from '@tailwindcss/vite';
import autoprefixer from 'autoprefixer';

const API_TARGET = process.env.VITE_API_URL || 'http://127.0.0.1:8003';
const SEARCH_TARGET = process.env.VITE_SEARCH_URL || API_TARGET; // Separate search service when split
const VITE_PORT = Number(process.env.VITE_PORT) || 3004;

// https://vitejs.dev/config/
export default defineConfig(({ command }) => ({
  base: process.env.VITE_BASE_PATH || '/',
  resolve: {
    // Cross-repo dev-resolution contract (glass-ui Q invariant 30, consumer half):
    // dev/serve resolves workspace-linked `@mkbabb/*` siblings through their
    // `development` export condition → live `src/`. The production build omits
    // `development` so siblings resolve via `import` → their published `dist/`.
    // No hard `dist/` alias for any `@mkbabb/*` sibling — the bare specifier
    // resolves through each sibling's `exports` map via the `file:` symlink.
    conditions:
      command === 'serve'
        ? ['development', 'module', 'browser', 'default']
        : ['module', 'browser', 'default'],
    alias: {
      '@': path.resolve(__dirname, './src'),
      // Resolve latex-paper sub-exports directly (symlink in dev, copy in Docker).
      // Tailwind CSS v4 doesn't resolve package.json exports maps, so each
      // sub-path needs an explicit alias. More specific paths must come first.
      '@mkbabb/latex-paper/theme': path.resolve(__dirname, './latex-paper/src/vue/theme.css'),
      '@mkbabb/latex-paper/vue': path.resolve(__dirname, './latex-paper/src/vue/index.ts'),
      '@mkbabb/latex-paper': path.resolve(__dirname, './latex-paper/src/index.ts'),
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
              port: Number(targetUrl.port) || 8003,
              path: targetUrl.pathname + targetUrl.search,
              method: req.method || 'GET',
              headers: {
                ...req.headers,
                host: targetUrl.host,
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Accept-Encoding': 'identity',
              },
            },
            (proxyRes) => {
              res.writeHead(proxyRes.statusCode || 200, {
                ...proxyRes.headers,
                'Content-Type': 'text/event-stream; charset=utf-8',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
              });

              proxyRes.pipe(res);
            });

          proxyReq.on('error', (err: Error) => {
            console.error('[SSE Proxy] Error:', err.message);
            if (!res.headersSent) {
              res.writeHead(502);
              res.end('SSE proxy error');
            }
          });

          // Abort only on a real disconnect, not when the POST body finishes streaming.
          req.on('aborted', () => {
            proxyReq.destroy();
          });

          res.on('close', () => {
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
    port: VITE_PORT,
    host: '0.0.0.0',
    strictPort: true,
    fs: {
      // The `development` export condition resolves workspace-linked `@mkbabb/*`
      // siblings to their `src/`; Vite serves those src-relative assets over the
      // `/@fs/` channel, which requires the sibling roots inside `fs.allow`.
      // `../..` covers the `words/` repo root and its `@mkbabb/*` siblings one
      // level up (glass-ui, keyframes.js, ...).
      allow: ['..', '../..'],
    },
    hmr: {
      clientPort: VITE_PORT,
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
      // Search routes go to the dedicated search service (when split)
      '/api/v1/search': {
        target: SEARCH_TARGET,
        changeOrigin: true,
        secure: false,
        timeout: 30000,
      },
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
            // Core Vue ecosystem + UI primitives + utilities in one chunk
            // (avoids circular deps between reka-ui ↔ @vueuse ↔ vue)
            if (/\/(vue|vue-router|pinia|@vue|reka-ui|@floating-ui|@internationalized|axios|@vueuse)\//.test(id)) return 'vendor';
            // Icons (tree-shaken, small)
            if (id.includes('lucide-vue-next')) return 'icons';
            // Auth (loaded after paint)
            if (id.includes('@clerk')) return 'clerk';
            // KaTeX (lazy-loaded via DefinitionDisplay)
            if (id.includes('katex')) return 'katex';
            // highlight.js (lazy-loaded via latex-paper CodeBlock)
            if (id.includes('highlight.js')) return 'hljs';
            // Virtual scrolling (lazy-loaded via WordListView)
            if (id.includes('@tanstack')) return 'virtual';
            // Carousel (lazy-loaded via DefinitionDisplay)
            if (id.includes('embla-carousel')) return 'carousel';
          }
        },
      },
    },
  },
  optimizeDeps: {
    // Pre-bundle dependencies for faster cold starts
    include: ['vue', 'vue-router', 'pinia'],
  },
}));
