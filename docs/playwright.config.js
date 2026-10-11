import { defineConfig } from "@playwright/test";

const baseURL = "http://127.0.0.1:8767";

export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  use: {
    baseURL,
    viewport: { width: 1568, height: 1088 },
    trace: "retain-on-failure",
  },
  projects: ["chromium", "firefox", "webkit"].map((browserName) => ({
    name: browserName,
    use: { browserName },
  })),
  webServer: {
    command:
      "uv run --frozen --no-sync python -m http.server 8767 --bind 127.0.0.1 --directory site",
    url: `${baseURL}/reference/mobjects/`,
    stderr: "ignore",
  },
});
