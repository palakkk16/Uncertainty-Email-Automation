import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const api = "http://127.0.0.1:8741";
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export default defineConfig({
  plugins: [react()],
  envDir: repoRoot,
  server: {
    host: "127.0.0.1",
    port: 43123,
    strictPort: true,
    proxy: {
      "/chat": { target: api, changeOrigin: true },
      "/health": { target: api, changeOrigin: true },
      "/auth": { target: api, changeOrigin: true },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 43123,
    strictPort: true,
  },
});
