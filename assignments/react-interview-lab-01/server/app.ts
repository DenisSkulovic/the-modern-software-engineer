import express from "express";
import { priorities, statuses, type Query } from "../shared/models";
import { Store, teams, operators } from "./store";
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));
export function createApp(store = new Store(), latency = true) {
  const app = express();
  app.use(express.json({ limit: "32kb" }));
  app.use("/api", (_req, res, next) => {
    res.setHeader("Cache-Control", "no-store");
    next();
  });
  app.get("/api/teams", (_req, res) => res.json(teams));
  app.get("/api/operators", (_req, res) => res.json(operators));
  app.get("/api/summary", (req, res) => {
    const teamId = String(req.query.teamId ?? "");
    if (teamId && !teams.some((t) => t.id === teamId))
      return res.status(400).json({ message: "Unknown team" });
    res.json(store.summary(teamId));
  });
  app.get("/api/tickets", async (req, res) => {
    const value = (key: string, fallback = "") =>
      String(req.query[key] ?? fallback);
    const q: Query = {
      teamId: value("teamId"),
      q: value("q"),
      status: value("status"),
      priority: value("priority"),
      sort: value("sort", "updated"),
      page: Number(value("page", "1")),
      pageSize: Number(value("pageSize", "10")),
    };
    if (
      (q.teamId && !teams.some((t) => t.id === q.teamId)) ||
      (q.status && !statuses.includes(q.status as never)) ||
      (q.priority && !priorities.includes(q.priority as never)) ||
      !["updated", "created", "priority"].includes(q.sort) ||
      !Number.isInteger(q.page) ||
      q.page < 1 ||
      !Number.isInteger(q.pageSize) ||
      q.pageSize < 1 ||
      q.pageSize > 100 ||
      q.q.length > 200
    )
      return res.status(400).json({ message: "Invalid queue parameters" });
    const snapshot = store.list(q);
    if (latency)
      await pause(
        req.query.refresh === "1" ? 1800 : 250 + (q.q.length % 3) * 100,
      );
    res.json(snapshot);
  });
  app.get("/api/tickets/:id/activity", (req, res) => {
    const t = store.get(req.params.id);
    if (!t) return res.status(404).json({ message: "Ticket not found" });
    res.json(
      store.activity.get(t.id) ?? [
        {
          id: `${t.id}-created`,
          at: t.createdAt,
          text: `Request received from ${t.customer}.`,
        },
      ],
    );
  });
  app.get("/api/tickets/:id", (req, res) => {
    const t = store.get(req.params.id);
    if (!t) return res.status(404).json({ message: "Ticket not found" });
    res.json(t);
  });
  app.patch("/api/tickets/:id", async (req, res) => {
    const t = store.get(req.params.id);
    if (!t) return res.status(404).json({ message: "Ticket not found" });
    const b = req.body;
    if (
      !b ||
      Array.isArray(b) ||
      typeof b !== "object" ||
      !Object.keys(b).length ||
      Object.keys(b).some(
        (k) => !["status", "priority", "assigneeId", "note"].includes(k),
      ) ||
      ("status" in b && !statuses.includes(b.status)) ||
      ("priority" in b && !priorities.includes(b.priority)) ||
      ("note" in b && (typeof b.note !== "string" || b.note.length > 4000)) ||
      ("assigneeId" in b &&
        b.assigneeId !== null &&
        !operators.some((o) => o.id === b.assigneeId && o.teamId === t.teamId))
    )
      return res
        .status(400)
        .json({
          message:
            "Invalid ticket update. Operators must belong to the ticket team; notes are limited to 4000 characters.",
        });
    if (latency) await pause(100);
    res.json(store.update(t.id, b));
  });
  app.post("/api/__dev/reset", (req, res) => {
    if (
      !["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(
        req.socket.remoteAddress ?? "",
      ) ||
      (req.headers.origin &&
        !/^http:\/\/(localhost|127\.0\.0\.1):(5173|4173)$/.test(
          req.headers.origin,
        ))
    )
      return res.status(403).json({ message: "Local access only" });
    store.reset();
    res.json({ message: "Fixtures restored" });
  });
  app.use("/api", (_req, res) =>
    res.status(404).json({ message: "Endpoint not found" }),
  );
  app.use(
    (
      error: unknown,
      _req: express.Request,
      res: express.Response,
      _next: express.NextFunction,
    ) => {
      res
        .status(400)
        .json({
          message:
            error instanceof SyntaxError
              ? "Malformed JSON"
              : "Request could not be processed",
        });
    },
  );
  return app;
}
