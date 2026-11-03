import {
  priorities,
  statuses,
  type Activity,
  type Operator,
  type Page,
  type Query,
  type Team,
  type Ticket,
} from "../shared/models";
export const teams: Team[] = [
  { id: "platform", name: "Platform support" },
  { id: "billing", name: "Billing operations" },
  { id: "accounts", name: "Customer success" },
];
export const operators: Operator[] = teams.flatMap((t, i) =>
  [
    "Maya Chen",
    "Jonas Berg",
    "Aisha Okafor",
    "Luca Rossi",
    "Sofia Marin",
    "Theo Clarke",
  ]
    .slice(i * 2, i * 2 + 2)
    .map((name, j) => ({ id: `op-${i * 2 + j + 1}`, name, teamId: t.id })),
);
const customers = [
  "Northstar Logistics",
  "Meridian Health",
  "Cedar Analytics",
  "Atlas Mobility",
  "Harbor Retail",
  "Juniper Energy",
  "Acorn Learning",
  "Solstice Media",
];
const subjects = [
  "Webhook delivery delayed",
  "Invoice export missing entries",
  "Workspace invitation expired",
  "SSO certificate renewal",
  "Usage report discrepancy",
  "Notification routing incorrect",
  "Customer import stalled",
  "Audit export unavailable",
  "Service account access review",
  "Scheduled sync paused",
  "Regional endpoint timeout",
  "Payment reconciliation pending",
];
export function fixtures(count = 270): Ticket[] {
  return Array.from({ length: count }, (_, i) => {
    const teamId = teams[i % 3].id;
    const createdAt = new Date(
      Date.UTC(2026, 9, 1) + i * 7200000,
    ).toISOString();
    return {
      id: `ROP-${1001 + i}`,
      title: subjects[Math.floor(i / 3) % subjects.length],
      customer: customers[(i * 5) % customers.length],
      teamId,
      status: statuses[Math.floor(i / 3) % 4],
      priority: priorities[Math.floor(i / 12) % 4],
      assigneeId:
        i % 5 === 0
          ? null
          : operators.filter((o) => o.teamId === teamId)[i % 2].id,
      createdAt,
      updatedAt: createdAt,
      description: `${customers[(i * 5) % customers.length]} reported ${subjects[Math.floor(i / 3) % subjects.length].toLowerCase()} in their production workspace. Check the latest account activity and coordinate the next update with the customer contact. Reference case CX-${7300 + i}.`,
      note: "Customer contacted. Awaiting the next operations review.",
      tags: [
        ["integration", "finance", "access"][i % 3],
        i % 2 ? "enterprise" : "standard",
      ],
    };
  });
}
export class Store {
  tickets = fixtures();
  activity = new Map<string, Activity[]>();
  reset() {
    this.tickets = fixtures();
    this.activity.clear();
  }
  get(id: string) {
    return this.tickets.find((t) => t.id === id);
  }
  list(q: Query): Page {
    const items = this.tickets.filter(
      (t) =>
        (!q.teamId || t.teamId === q.teamId) &&
        (!q.status || t.status === q.status) &&
        (!q.priority || t.priority === q.priority) &&
        `${t.id} ${t.title} ${t.customer}`
          .toLowerCase()
          .includes(q.q.toLowerCase()),
    );
    items.sort((a, b) =>
      q.sort === "priority"
        ? priorities.indexOf(b.priority) - priorities.indexOf(a.priority) ||
          a.id.localeCompare(b.id)
        : q.sort === "created"
          ? b.createdAt.localeCompare(a.createdAt)
          : b.updatedAt.localeCompare(a.updatedAt),
    );
    return structuredClone({
      items: items.slice((q.page - 1) * q.pageSize, q.page * q.pageSize),
      page: q.page,
      pageSize: q.pageSize,
      total: items.length,
      totalPages: Math.max(1, Math.ceil(items.length / q.pageSize)),
    });
  }
  update(
    id: string,
    patch: Partial<Pick<Ticket, "status" | "priority" | "assigneeId" | "note">>,
  ) {
    const t = this.get(id);
    if (!t) return undefined;
    Object.assign(t, patch, { updatedAt: new Date().toISOString() });
    const history = this.activity.get(id) ?? [];
    history.unshift({
      id: `${id}-${history.length + 1}`,
      at: t.updatedAt,
      text: `Maya Chen updated ${Object.keys(patch).join(", ")}.`,
    });
    this.activity.set(id, history);
    return structuredClone(t);
  }
  summary(teamId: string) {
    const ts = this.tickets.filter((t) => !teamId || t.teamId === teamId);
    return {
      open: ts.filter((t) => t.status !== "Resolved").length,
      urgent: ts.filter(
        (t) => t.priority === "Urgent" && t.status !== "Resolved",
      ).length,
      mine: ts.filter((t) => t.assigneeId === "op-1" && t.status !== "Resolved")
        .length,
      resolved: ts.filter((t) => t.status === "Resolved").length,
    };
  }
}
