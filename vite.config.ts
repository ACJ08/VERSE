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
      '/auth':        { target: 'http://localhost:8000', changeOrigin: true },  // POST /auth/login, /auth/register, …
      '/upload':      { target: 'http://localhost:8000', changeOrigin: true },  // POST /upload/screenplay, /upload/footage
      '/projects':    { target: 'http://localhost:8000', changeOrigin: true },  // CRUD /projects, /projects/{id}/team
      '/continuity':  { target: 'http://localhost:8000', changeOrigin: true },  // POST /continuity/analyse, /continuity/ingest/*
      '/health':      { target: 'http://localhost:8000', changeOrigin: true },  // GET  /health  (BackendStatusBadge)
    },
  },

  // ── Asset types ────────────────────────────────────────────────────────────
  // Binary file types that Vite serves as raw URLs (returned as strings when
  // imported). Never add .css, .tsx, or .ts — those are processed, not raw.
  assetsInclude: ['**/*.svg', '**/*.csv'],
})
