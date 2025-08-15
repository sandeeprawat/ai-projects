import { defineConfig } from "vite";

﻿// Vite dev server with proxy to local Azure Functions host on :7081
export default defineConfig({
  server: {
    port: 5174,
    proxy: {
      "/api": {
        target: "http://localhost:7071",
        changeOrigin: true,
        secure: false
      }
    }
  }
});
