# RelayOps — Operations Work Queue

An internal console for triaging customer service requests across three operations teams. All records are fictional. Data persists in memory until the API restarts or is reset.

## Getting started

Use Node.js 24 LTS (minimum 22.12) and npm. No accounts, database or external services are required.

```sh
npm ci
npm run dev
```

Open http://localhost:5173. The API listens on http://127.0.0.1:4173; Vite proxies `/api` to it. Both ports must be free. The servers bind locally.

```sh
npm run test
npm run test:watch
npm run typecheck
npm run build
npm run reset
```

Reset requires the API to be running. Reload the browser afterward. Restarting the API also restores fixtures. Build emits the frontend and a compiled backend into `dist/`. To serve the built frontend with the backend, set `NODE_ENV=production` in your shell and run `npm start` (port 4173).

## Orientation

- `client/src/App.tsx`: queue workspace, filters and ticket selection.
- `client/src/components/`: ticket detail editor.
- `client/src/hooks/`: shared queue loading.
- `client/src/services/`: HTTP boundary.
- `server/`: Express routes and in-memory store with deterministic fixtures.
- `shared/`: TypeScript contracts.
- `client/test/`: MSW network fixtures; component tests live beside the application.

React, TypeScript and Vite power the client; Express and TypeScript power the API. Vitest, React Testing Library, user-event and MSW exercise the client, with Supertest covering real HTTP routes. Ordinary reads have a short simulated delay; explicit queue refreshes take longer to represent a more expensive synchronization. The reset endpoint accepts only local connections and local development browser origins.

Read `INTERVIEW_BRIEF.md` when ready to begin.
