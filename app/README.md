# RainGuard web app

React + TypeScript + Vite + MapLibre GL. Reads the static files in `public/data/`, which are produced by `python analysis/run_pipeline.py` in the repo root.

```bash
npm ci
npm test          # unit and UI tests
npm run dev       # local dev server
npm run build     # production build in dist/
npm run preview   # serve the build at http://localhost:4173
```

Pushing to `main` deploys the site to GitHub Pages automatically (see `.github/workflows/deploy.yml`).
Live site: https://saiesh0007.github.io/rainguard/
