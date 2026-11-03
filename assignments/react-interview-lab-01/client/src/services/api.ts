import type {
  Activity,
  Operator,
  Page,
  Query,
  Summary,
  Team,
  Ticket,
} from "../../../shared/models";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.message ?? `Request failed (${response.status})`);
  }
  return response.json();
}
const params = (q: Query) =>
  new URLSearchParams(Object.entries(q).map(([k, v]) => [k, String(v)]));
export const api = {
  teams: () => request<Team[]>("/teams"),
  operators: () => request<Operator[]>("/operators"),
  list: (q: Query, refresh = false) =>
    request<Page>(`/tickets?${params(q)}${refresh ? "&refresh=1" : ""}`),
  ticket: (id: string) => request<Ticket>(`/tickets/${id}`),
  activity: (id: string) => request<Activity[]>(`/tickets/${id}/activity`),
  summary: (teamId: string) =>
    request<Summary>(`/summary?teamId=${encodeURIComponent(teamId)}`),
  update: (id: string, patch: Partial<Ticket>) =>
    request<Ticket>(`/tickets/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
};
