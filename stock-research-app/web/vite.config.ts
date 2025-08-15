import { defineConfig } from "vite";

// Vite dev server with proxy to local Azure Functions host on :7071
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:7071",
        changeOrigin: true,
        secure: false
      }
    }
  }
});
