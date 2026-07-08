import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// En desarrollo (npm run dev) Vite corre en :5173 y proxea la API al backend
// FastAPI en :9000. En producción se compila a dist/ y FastAPI sirve los
// estáticos directamente — no corre ningún proceso Node.
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        player: resolve(__dirname, "player.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:9000",
      "/video": "http://localhost:9000",
      "/audio": "http://localhost:9000",
      "/health": "http://localhost:9000",
      "/ws": { target: "ws://localhost:9000", ws: true },
    },
  },
});
