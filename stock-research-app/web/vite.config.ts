import { defineConfig } from "vite";

export default defineConfig({
  // Keep TSX without introducing React runtime
  esbuild: {
    jsx: "preserve"
  },
  // Prevent Vite from trying to prebundle/react optimize
  optimizeDeps: {
    exclude: ["react", "react-dom"]
  },
  // Proxy API calls to Azure Functions (avoids CORS and backend URL mismatches)
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:7071",
        changeOrigin: true,
        secure: false
      },
      // Dev proxy for Azurite blob to bypass CORS during in-app preview fetches
      "/blob": {
        target: "http://127.0.0.1:10000",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/blob/, "")
      }
    }
  }
});
