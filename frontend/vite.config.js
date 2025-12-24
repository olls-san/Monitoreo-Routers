import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const API_TARGET = env.VITE_API_TARGET || "http://127.0.0.1:8000";

  const proxy = {
    "/hosts": { target: API_TARGET, changeOrigin: true },
    "/action-runs": { target: API_TARGET, changeOrigin: true },
    "/automation-rules": { target: API_TARGET, changeOrigin: true },
    "/config": { target: API_TARGET, changeOrigin: true },
    "/health": { target: API_TARGET, changeOrigin: true },
    "/docs": { target: API_TARGET, changeOrigin: true },
    "/openapi.json": { target: API_TARGET, changeOrigin: true },
  };

  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      proxy,
    },
    // Importante si usas `npm run preview`
    preview: {
      host: true,
      port: 5173,
      proxy,
    },
  };
});
