import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

const versionName =
  process.env.LYCHD_ALTAR_VERSION?.trim() || process.env.GITHUB_SHA?.trim() || "source";

export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      fallback: "index.html",
      pages: "../src/lychd/public",
      assets: "../src/lychd/public",
      strict: true
    }),
    version: {
      name: versionName
    }
  }
};
