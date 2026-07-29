import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vitest/config";

const exactSourceRevision =
  process.env.LYCHD_ALTAR_VERSION?.trim() || process.env.GITHUB_SHA?.trim();
const sourceRevision = exactSourceRevision || "source";
const sourceUrl = exactSourceRevision
  ? `https://github.com/hexanomicon/lychd/tree/${encodeURIComponent(exactSourceRevision)}/frontend`
  : "https://github.com/hexanomicon/lychd/tree/main/frontend";
const sourceLabel = exactSourceRevision
  ? "Corresponding source · MPL-2.0"
  : "Project source · MPL-2.0";

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  define: {
    __LYCHD_ALTAR_VERSION__: JSON.stringify(sourceRevision),
    __LYCHD_SOURCE_URL__: JSON.stringify(sourceUrl),
    __LYCHD_SOURCE_LABEL__: JSON.stringify(sourceLabel)
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/schema": "http://127.0.0.1:8000"
    }
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts"]
  }
});
