import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 3000,
    open: true,
    cors: true,
    proxy: {
      // Optional: if you want to proxy requests to the TiTiler server
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
