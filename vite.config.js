import { defineConfig } from "vite";
import path from "path";
import litestar from "litestar-vite-plugin";

const ASSET_URL = process.env.ASSET_URL || "/static/";
const VITE_PORT = process.env.VITE_PORT || "5173";
const VITE_HOST = process.env.VITE_HOST || "0.0.0.0";

export default defineConfig({
  base: ASSET_URL,
  clearScreen: false,
  server: {
    host: VITE_HOST,
    port: +VITE_PORT,
    cors: true,
    hmr: {
      host: "localhost",
    },
  },
  plugins: [
    litestar({
      input: ["resources/main.css", "resources/main.js"],
      assetUrl: ASSET_URL,
      bundleDirectory: "src/lychd/public",
      resourceDirectory: "resources",
      hotFile: "src/lychd/public/hot",
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "resources"),
    },
  },
  build: {
    emptyOutDir: true,
    outDir: "src/lychd/public",
    rollupOptions: {
    }
  }
});
