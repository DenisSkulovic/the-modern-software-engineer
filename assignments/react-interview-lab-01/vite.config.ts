import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  root: "client",
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:4173" },
  },
  build: { outDir: "../dist/client", emptyOutDir: true },
  test: {
    root: ".",
    environment: "jsdom",
    setupFiles: ["./client/test/setup.ts"],
    include: ["client/**/*.test.ts*", "server/**/*.test.ts"],
    restoreMocks: true,
  },
});
