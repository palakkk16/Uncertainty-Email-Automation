import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const api = "http://127.0.0.1:8741";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 43123,
    strictPort: true,
    proxy: {
      "/chat": { target: api, changeOrigin: true },
      "/health": { target: api, changeOrigin: true },
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 43123,
    strictPort: true,
  },
});
