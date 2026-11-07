import {defineConfig} from '@playwright/test'
export default defineConfig({testDir: './e2e', timeout: 180000, retries: 0, workers: 1,
  use: {baseURL: 'http://127.0.0.1:8000', viewport: {width: 1500, height: 1000}, trace: 'retain-on-failure'},
  reporter: 'list'})
