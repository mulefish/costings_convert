// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: ".",
  testMatch: "*.spec.js",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:8501",
    headless: false,
    viewport: { width: 1400, height: 900 },
    screenshot: "only-on-failure",
    launchOptions: {
      executablePath: "C:\\Program Files\\Island\\Island\\Application\\Island.exe",
    },
  },
  projects: [
    { name: "island", use: { browserName: "chromium" } },
  ],
});
