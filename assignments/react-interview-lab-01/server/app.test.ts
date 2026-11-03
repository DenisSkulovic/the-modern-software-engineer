// @vitest-environment node
import { describe, expect, it } from "vitest";
import request from "supertest";
import { createApp } from "./app";
import { Store } from "./store";
describe("Ticket HTTP service", () => {
  it("returns deterministic paginated results with team isolation", async () => {
    const app = createApp(new Store(), false);
    const response = await request(app).get(
      "/api/tickets?teamId=billing&page=2&pageSize=10",
    );
    expect(response.status).toBe(200);
    expect(response.body.total).toBe(90);
    expect(response.body.items).toHaveLength(10);
    expect(
      response.body.items.every(
        (t: { teamId: string }) => t.teamId === "billing",
      ),
    ).toBe(true);
  });
  it("sorts by priority and allows empty out-of-range pages", async () => {
    const store = new Store();
    const app = createApp(store, false);
    const sorted = await request(app).get("/api/tickets?sort=priority");
    expect(sorted.body.items[0].priority).toBe("Urgent");
    const r = await request(app).get("/api/tickets?q=ROP-1001&page=3");
    expect(r.body.total).toBe(1);
    expect(r.body.items).toEqual([]);
  });
  it.each([
    "page=0",
    "pageSize=101",
    "page=1.5",
    "teamId=unknown",
    "status=invalid",
    "sort=wrong",
  ])("rejects invalid query %s", async (query) => {
    expect(
      (
        await request(createApp(new Store(), false)).get(
          `/api/tickets?${query}`,
        )
      ).status,
    ).toBe(400);
  });
  it("persists changes, adds activity and restores fixtures", async () => {
    const store = new Store();
    const app = createApp(store, false);
    const original = structuredClone(store.get("ROP-1001"));
    const changed = await request(app)
      .patch("/api/tickets/ROP-1001")
      .send({ note: "Verified", status: "Resolved" });
    expect(changed.status).toBe(200);
    expect(changed.body.updatedAt).not.toBe(original?.updatedAt);
    expect((await request(app).get("/api/tickets/ROP-1001")).body.note).toBe(
      "Verified",
    );
    expect(
      (await request(app).get("/api/tickets/ROP-1001/activity")).body[0].text,
    ).toContain("note, status");
    expect((await request(app).post("/api/__dev/reset")).status).toBe(200);
    expect(store.get("ROP-1001")).toEqual(original);
  });
  it.each([
    { status: "Missing" },
    { assigneeId: "op-3" },
    { note: "a".repeat(4001) },
    { note: 42 },
    { customer: "Changed" },
    {},
  ])("validates mutations %j", async (body) => {
    expect(
      (
        await request(createApp(new Store(), false))
          .patch("/api/tickets/ROP-1001")
          .send(body)
      ).status,
    ).toBe(400);
  });
  it("returns missing-ticket errors", async () => {
    expect(
      (await request(createApp(new Store(), false)).get("/api/tickets/missing"))
        .status,
    ).toBe(404);
  });
  it("rejects reset requests from foreign browser origins", async () => {
    expect(
      (
        await request(createApp(new Store(), false))
          .post("/api/__dev/reset")
          .set("Origin", "https://other.example")
      ).status,
    ).toBe(403);
  });
});
