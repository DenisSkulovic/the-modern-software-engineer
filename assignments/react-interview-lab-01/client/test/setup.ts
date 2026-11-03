import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { Store, teams, operators } from "../../server/store";
import { defaultQuery, type Query } from "../../shared/models";
import { clearQueueCache } from "../src/hooks/useQueue";
export const store = new Store();
export const network = setupServer(
  http.get("/api/teams", () => HttpResponse.json(teams)),
  http.get("/api/operators", () => HttpResponse.json(operators)),
  http.get("/api/summary", ({ request }) =>
    HttpResponse.json(
      store.summary(new URL(request.url).searchParams.get("teamId") ?? ""),
    ),
  ),
  http.get("/api/tickets", ({ request }) => {
    const p = new URL(request.url).searchParams;
    const q = {
      ...defaultQuery,
      ...Object.fromEntries(p),
      page: Number(p.get("page") ?? 1),
      pageSize: Number(p.get("pageSize") ?? 10),
    } as Query;
    return HttpResponse.json(store.list(q));
  }),
  http.get("/api/tickets/:id/activity", ({ params }) =>
    HttpResponse.json(store.activity.get(String(params.id)) ?? []),
  ),
  http.get("/api/tickets/:id", ({ params }) => {
    const t = store.get(String(params.id));
    return t
      ? HttpResponse.json(t)
      : HttpResponse.json({ message: "Ticket not found" }, { status: 404 });
  }),
  http.patch("/api/tickets/:id", async ({ params, request }) =>
    HttpResponse.json(
      store.update(String(params.id), (await request.json()) as object),
    ),
  ),
);
beforeAll(() => {
  if (typeof document !== "undefined")
    network.listen({ onUnhandledFrame: "error" });
});
beforeEach(() => {
  store.reset();
  clearQueueCache();
});
afterEach(() => {
  cleanup();
  network.resetHandlers();
});
afterAll(() => {
  if (typeof document !== "undefined") network.close();
});
