import { defineConfig } from '@playwright/test';

// BASE_URL points at the running app (default: local; in docker-compose.test.yml: http://app:8000).
export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1, // tests share one SQLite-backed app instance
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
});
