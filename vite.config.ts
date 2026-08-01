/**
 * Vite build & dev-server configuration for the VERSE frontend.
 *
 * Key responsibilities:
 * - Register the Figma asset resolver, React, and Tailwind CSS plugins.
 * - Alias `@` to `./src` so all imports use `@/app/...` rather than `../../`.
 * - Proxy every backend API route to http://localhost:8000 in development so
 *   the browser never makes a cross-origin request (no CORS issues in dev).
 * - Declare which binary asset types are handled by Vite's asset pipeline.
 */
import { defineConfig } from 'vite'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


/**
 * figmaAssetResolver — handles `figma:asset/<filename>` import specifiers.
 * Figma Make tools use this prefix when referencing design assets; we remap
 * them to `src/assets/` so standard Vite bundling picks them up.
 */
function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig({
  plugins: [
    figmaAssetResolver(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // `@` resolves to the src/ directory.
      // Usage: import Foo from '@/app/components/Foo'
      '@': path.resolve(__dirname, './src'),
    },
  },

  // ── Dev-server proxy ───────────────────────────────────────────────────────
  // Rewrites matching paths to the FastAPI backend (http://localhost:8000).
  // The frontend sets VITE_API_URL="" (empty string = same-origin) so all
  // fetch() calls go to the Vite dev server, which then proxies them here.
  // This avoids CORS preflight entirely in development.
  //
  // To add a new backend route prefix: add an entry here AND ensure the
  // corresponding FastAPI router is mounted in continuity-engine/main.py.
  server: {
    proxy: {
      // ── Continuity Engine (port 8000) ───────────────────────────────────
      // Proxy all /auth/* API routes to the backend EXCEPT /auth/callback,
      // which is the frontend SPA landing page for the Google OAuth redirect.
      '^/auth/(?!callback)': { target: 'http://localhost:8000', changeOrigin: true },  // POST /auth/login, /auth/register, …
      '/upload':      { target: 'http://localhost:8000', changeOrigin: true },  // POST /upload/screenplay, /upload/footage
      '/projects':    { target: 'http://localhost:8000', changeOrigin: true },  // CRUD /projects, /projects/{id}/team
      '/continuity':  { target: 'http://localhost:8000', changeOrigin: true },  // POST /continuity/analyse, /continuity/ingest/*
      '/health':      { target: 'http://localhost:8000', changeOrigin: true },  // GET  /health  (BackendStatusBadge)
      // ── Script Intelligence (port 8100) ─────────────────────────────────
      // Proxied under /script-api so the browser avoids CORS pre-flight when
      // VITE_SCRIPT_API_URL is empty (same-origin dev mode).
      // api.ts reads VITE_SCRIPT_API_URL and falls back to empty string →
      // same-origin → hits this proxy entry.
      '/script-api':  { target: 'http://localhost:8100', changeOrigin: true, rewrite: (p) => p.replace(/^\/script-api/, '') },
      // ── Vision Pipeline (port 8200) ──────────────────────────────────────
      '/vision-api':  { target: 'http://localhost:8200', changeOrigin: true, rewrite: (p) => p.replace(/^\/vision-api/, '') },
    },
  },

  // ── Asset types ────────────────────────────────────────────────────────────
  // Binary file types that Vite serves as raw URLs (returned as strings when
  // imported). Never add .css, .tsx, or .ts — those are processed, not raw.
  assetsInclude: ['**/*.svg', '**/*.csv'],
})
