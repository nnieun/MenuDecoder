import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 45000, fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:5179', ...devices['iPhone 13'], browserName: 'chromium', channel: 'chrome', trace: 'retain-on-failure' },
  reporter: 'list',
  webServer: [
    {
      command: 'uv run uvicorn backend.main:app --port 8000',
      url: 'http://127.0.0.1:8000/docs',
      cwd: '..',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: 'npm run dev -- --port 5179 --strictPort',
      url: 'http://127.0.0.1:5179',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
