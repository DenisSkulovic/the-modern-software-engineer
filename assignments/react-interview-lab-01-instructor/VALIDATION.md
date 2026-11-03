# Confidential validation record

Executed on 2026-11-03, Windows, Node v24.19.0, npm 11.17.0. Candidate baseline commit: `0730826d8ee05b468a4ae70501b13eb9d0adce2d` (single initial commit, no revealing history).

## Executed checks

- `npm ci`: passed using the committed lockfile; 255 packages installed, zero reported vulnerabilities. Stop running development processes before reinstalling on Windows; an initial attempt with the server still running hit the normal locked-binary error. After stopping it, clean install passed. npm printed its esbuild script-approval notice; build worked with the packaged platform binary.
- `npm run typecheck`: passed after fresh install.
- `npm run build`: passed after fresh install, producing the Vite client and bundled Express entrypoint.
- `npm run test -- --reporter=json`: 27 total, 26 passing, exactly one expected failure in the App's later-page narrowing regression. No failed suites from setup. A previous full run also produced 26/1. The failure is ordinary `findByRole` unable to find the matching request because the real App retains page 3.
- `npm run dev`: frontend and API started on the documented ports. Live Edge automation used real HTTP and the React StrictMode entrypoint.
- Browser: queue and summary loaded, normal search and pagination worked, ticket detail opened, note saved, status mutation succeeded, team refresh retrieved the selected dataset, local reset restored data. No uncaught page exceptions.
- A, B, C and D were each reproduced via live browser actions and assertions. D additionally checked the backend GET retained the confirmed mutation after the UI reverted. `browser-validation.json` records the assertions.
- Responsive snapshots at 1440, 768 and 390 pixels: rendered; no document-level horizontal overflow. Desktop detail screenshot visually inspected. No custom fonts, external network services or credentials required.
- `NODE_ENV=production npm start`: compiled backend served the compiled client on 4173; queue and API loaded in Edge. `npm run reset` also executed successfully.

## Optional future performance overlay

Installed only on an isolated copy with the confidential installer. Its typecheck passed. Ran Vite on 5174 with the existing API proxy. Live browser confirmed 12,000 overview DOM rows, then 1,500 rows for `Northstar`, each with the correct customer total. This provides an actually observed slowdown: initial navigation plus render approximately 26.3 s, search plus render approximately 11.9 s on this Windows host, without CPU throttling. These are illustrative single-run wall-clock observations, not controlled benchmarks or candidate targets. Require repeated before/after profiling on the candidate's machine. No overlay code enters the baseline or ZIP. Production smoke was checked before loading this overlay.

## Packaging and confidentiality

Candidate package has 24 source/config/documentation files with a real lockfile. The ZIP is generated from the same files, checked with ZIP CRC validation and extracted into an isolated directory. One root `react-interview-lab-01/`; no node_modules, dist, .git, instructor files, answers, future tasks or scratch artifacts. A case-insensitive candidate-text audit checks for construction spoilers and future task identifiers. Source copied into the study repository is byte-identical to ZIP entries. The independent candidate Git working tree is clean. The study delivery commit contains only explicit assignment paths; the user's original untracked handoff is left untouched and uncommitted.

Use the source and ZIP checksum in `package-validation.json` for review. When extracting the ZIP, initialize a local Git baseline before the session. The stored source in the study repository intentionally has no nested Git metadata, avoiding a broken embedded-repository/submodule delivery.

## Reproducing the private browser checks

Start the candidate app on 5173/4173. In this instructor directory install Playwright separately (`npm install --no-save playwright`), then run `node verify-browser.cjs`. It launches installed Microsoft Edge headlessly, restores fictional fixtures, reproduces all four cases, and writes confidential evidence under `evidence/`. Install Playwright Chromium and adjust the channel if Edge is unavailable. Do not put these checks or their outputs in the candidate workspace. The original executed browser checks used the same assertions with a temporary Playwright installation outside the candidate repository.
