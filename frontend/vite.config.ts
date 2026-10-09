import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, Vite serves the React app on :5173 and forwards
// /api and /auth calls to the Express server on :3001,
// which in turn forwards them to San's FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:3001",
      "/auth": "http://localhost:3001",
    },
  },
});
