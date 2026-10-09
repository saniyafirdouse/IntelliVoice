/**
 * IntelliVoice — Node.js / Express server
 *
 *  • In production it serves the built React app (the dist/ folder).
 *  • It forwards /api and /auth requests to the FastAPI backend (San's Python code),
 *    so the browser only ever talks to one address — no CORS setup needed.
 *  • `--demo` (or DEMO_MODE=true) answers with clearly-labelled sample replies instead,
 *    for showing the frontend when the backend isn't running.
 *
 * Settings come from a .env file (see .env.example).
 */
import "dotenv/config";
import express, { type NextFunction, type Request, type Response } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import fs from "node:fs";
import type { ServerResponse } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { demoRouter } from "./demo";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT) || 3001;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const DEMO = process.argv.includes("--demo") || process.env.DEMO_MODE === "true";
const DIST = path.resolve(__dirname, "../dist");

const app = express();
app.disable("x-powered-by");

// tiny request log
app.use((req: Request, res: Response, next: NextFunction) => {
  const started = Date.now();
  res.on("finish", () => {
    if (req.path.startsWith("/api") || req.path.startsWith("/auth")) {
      console.log(`${req.method} ${req.path} → ${res.statusCode} (${Date.now() - started} ms)`);
    }
  });
  next();
});

app.get("/health", (_req, res) => {
  res.json({ ok: true, mode: DEMO ? "demo" : "proxy", backend: DEMO ? null : BACKEND_URL });
});

if (DEMO) {
  app.use(express.json({ limit: "100kb" }));
  app.use(demoRouter());
} else {
  // Body is streamed straight through (no parsing here), so audio uploads pass untouched.
  app.use(
    createProxyMiddleware({
      target: BACKEND_URL,
      changeOrigin: true,
      pathFilter: ["/api", "/auth"],
      proxyTimeout: 60_000,
      on: {
        error: (_err, _req, res) => {
          const out = res as ServerResponse;
          if (out.headersSent) return;
          out.writeHead(502, { "Content-Type": "application/json" });
          out.end(JSON.stringify({
            detail: `Couldn't reach the IntelliVoice backend at ${BACKEND_URL}. Please check that the FastAPI server is running.`,
          }));
        },
      },
    }),
  );
}

// Serve the built React app (after `npm run build`). Unknown paths fall back to index.html
// so that links like /chat or /about work when opened directly.
if (fs.existsSync(path.join(DIST, "index.html"))) {
  app.use(express.static(DIST, { maxAge: "1h", index: false }));
  app.get("*", (req, res, next) => {
    if (req.path.startsWith("/api") || req.path.startsWith("/auth")) return next();
    res.sendFile(path.join(DIST, "index.html"));
  });
}

app.use((req, res) => {
  res.status(404).json({ detail: `Not found: ${req.method} ${req.path}` });
});

app.listen(PORT, () => {
  console.log(`\n  IntelliVoice server running on http://localhost:${PORT}`);
  console.log(DEMO
    ? "  Mode: DEMO — sample replies, no backend needed"
    : `  Mode: forwarding /api and /auth to ${BACKEND_URL}`);
  if (!fs.existsSync(path.join(DIST, "index.html"))) {
    console.log("  (React app not built yet — during development open http://localhost:5173)");
  }
  console.log("");
});
