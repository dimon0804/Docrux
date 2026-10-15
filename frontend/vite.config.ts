import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "DOCRUX_");
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": new URL("./src", import.meta.url).pathname } },
    server: {
      port: 5173,
      proxy: {
        "/api": { target: env.DOCRUX_API ?? "http://localhost:8000", changeOrigin: true },
      },
    },
    build: { target: "es2022", sourcemap: false },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: false,
    },
  };
});
