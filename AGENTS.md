# AGENTS.md

## Cursor Cloud specific instructions

This repository is a single, fully static personal portfolio website (Aanchal Save). There is no build system, package manager, backend, database, or environment variables.

- Source files: `index.html` (page markup/content), `styles.css` (styling), `script.js` (vanilla-JS interactivity: mobile menu, skill tabs, case-study modals, scroll-reveal, card tilt, starfield canvas). Media/PDF assets live at the repo root.
- There are no dependencies to install and nothing to compile. Do not look for `package.json`, lockfiles, or a dev script — none exist.

### Run (development)

Serve the repo root with any static HTTP server, then open the page in a browser:

```bash
python3 -m http.server 8000   # from repo root; then open http://localhost:8000/
```

- Editing HTML/CSS/JS requires only a browser refresh (no hot-reload/watcher). `python3 -m http.server` does not cache, so a normal reload picks up changes.
- Opening `index.html` via `file://` mostly works, but serving over HTTP is the correct way to test (matches how relative asset paths and the PDF/video assets load).

### Lint / test / build

- No linters, no automated test suite, and no build step are configured in this repo. "Testing" means manually loading the served page and exercising the interactive elements (skill tabs, project case-study modals, scroll animations).

### Notes / gotchas

- Fonts load from the Google Fonts CDN (`fonts.googleapis.com`); without internet the page falls back to system fonts but is otherwise fully functional.
