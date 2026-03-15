import { defineConfig, devices } from '@playwright/test';

const FRONTEND_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000';
const BACKEND_URL = process.env.VITE_API_URL || 'http://127.0.0.1:8000';

// When PLAYWRIGHT_BASE_URL is set, assume servers are managed externally (e.g. Docker).
const useExternalServers = !!process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['json', { outputFile: 'playwright-results/results.json' }]],
  use: {
    baseURL: FRONTEND_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    extraHTTPHeaders: {
      'X-Dev-Admin': 'true',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // Only auto-start servers when running against local dev (not Docker).
  ...(useExternalServers
    ? {}
    : {
        webServer: [
          {
            command: `cd ${process.cwd()}/../backend && uv run scripts/run_api.py`,
            url: `${BACKEND_URL}/health`,
            timeout: 60_000,
            reuseExistingServer: true,
            env: {
              FLORIDIFY_DB_TARGET: 'test',
              KMP_DUPLICATE_LIB_OK: 'TRUE',
              OMP_NUM_THREADS: '1',
              TOKENIZERS_PARALLELISM: 'false',
              LOKY_MAX_CPU_COUNT: '1',
            },
          },
          {
            command: 'npm run dev',
            url: FRONTEND_URL,
            timeout: 30_000,
            reuseExistingServer: true,
            env: {
              VITE_API_URL: BACKEND_URL,
              VITE_DEV_ADMIN: 'true',
            },
          },
        ],
      }),
});
