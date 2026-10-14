---
name: fetch-frontend-resources
description: Snapshot a web application's JavaScript and statically referenced JSON assets into a dated local folder with hashes and a record of unresolved references. Use when asked to collect or refresh frontend resources.
---

# Fetch Frontend Resources

Save a traceable local snapshot of the application's frontend bundles and discoverable JSON assets.

## Gather inputs

- Use the application name and hosted main-page URL if already provided in the conversation. If either is missing, ask for the missing details together.
- Use explicitly supplied bundle URLs when available. Otherwise fetch the main page and discover script and module-preload URLs. If none are exposed, ask for an entry bundle URL or asset manifest.
- Use the requested destination if the user specifies one (`--output-dir`). Otherwise use `.scratch/<application-slug>-frontend-<YYYY-MM-DD>/` in the current workspace. Use the current client date and pass it explicitly with `--date`.

## Capture

- Run `scripts/fetch_frontend_resources.py` for ordinary HTTP-accessible applications. It requires Python 3.10+ and only the Python standard library. Example:

  ```powershell
  python .agents/skills/fetch-frontend-resources/scripts/fetch_frontend_resources.py `
    --app-name "ZMP" `
    --base-url "https://app.example.com/" `
    --entry-url "https://app.example.com/assets/app.js" `
    --date 2026-10-14
  ```

- If the user supplies multiple bundles, pass each as a separate `--entry-url`. The script also discovers entry scripts and module preloads from the page if no entry URL is supplied.
- Follow literal static imports, side-effect imports, dynamic imports with literal paths, `.js`/`.mjs` references, absolute JavaScript URLs, and statically identifiable JSON asset references recursively. Resolve bundle imports against the bundle's final URL after redirects, page scripts against the page's `<base href>` when present, and relative `fetch`/XHR JSON paths against the page URL.
- Do not crawl arbitrary page links, enumerate guessed filenames, execute downloaded code, invent runtime parameter values, or enumerate user/tenant data. Record computed imports, ambiguous relative strings, likely API routes, failed requests, and other unresolved references instead of guessing.
- Save response bodies unchanged. Keep JavaScript under `javascript/` and JSON under `json/`. Preserve host/path context while encoding unsafe path segments; use collision-resistant filenames and ensure outputs remain inside the snapshot folder.
- Do not overwrite an existing snapshot. Stop and report the existing path so the user can choose another date or destination.
- Keep `manifest.csv`, `snapshot-references.csv`, and `README.md`. The manifest records source and final URLs, status, content type, byte count, and SHA-256. The reference log records each referring URL, original reference text, resolution/result, and HTTP status. The README summarizes the inputs, date, counts, byte totals, capture status, and limitations.
- Never put request cookies or authorization headers in snapshot metadata. If the application requires authentication, use an already available authenticated browser/session workflow only when appropriate and authorized; do not ask the user to paste secrets.

## Completion criteria

- **Complete:** at least one JavaScript file was saved and no discovered references remain failed or unresolved. Report the folder and file counts.
- **Partial:** files were saved, but some discovered references were computed, ambiguous, inaccessible, likely API responses, or otherwise unresolved. Report the saved counts and point to `snapshot-references.csv`.
- **Failed:** no JavaScript entry could be discovered or saved, or the snapshot could not be created. State the specific blocker and the input needed to continue.

Never describe the snapshot as exhaustive when static analysis cannot resolve runtime-generated chunks or authenticated/stateful resources. For authenticated bootstrapping or nonstandard manifests, inspect the browser-loaded page or adapt the collection method while retaining the same dated folder, README, manifest, and unresolved-reference record.
