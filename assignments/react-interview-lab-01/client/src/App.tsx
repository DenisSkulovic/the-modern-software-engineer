import { useEffect, useState } from "react";
import {
  defaultQuery,
  priorities,
  statuses,
  type Operator,
  type Query,
  type Summary,
  type Team,
  type Ticket,
} from "../../shared/models";
import { useQueue } from "./hooks/useQueue";
import { api } from "./services/api";
import { TicketDetail } from "./components/TicketDetail";
export default function App() {
  const [query, setQuery] = useState<Query>(defaultQuery);
  const queue = useQueue(query);
  const [teams, setTeams] = useState<Team[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [summary, setSummary] = useState<Summary>();
  const [selected, setSelected] = useState<Ticket>();
  const [error, setError] = useState("");
  const [pending, setPending] = useState<string>();
  const [summaryVersion, setSummaryVersion] = useState(0);
  useEffect(() => {
    Promise.all([api.teams(), api.operators()])
      .then(([ts, os]) => {
        setTeams(ts);
        setOperators(os);
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    let live = true;
    api
      .summary(query.teamId)
      .then((s) => {
        if (live) setSummary(s);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [query.teamId, summaryVersion]);
  function filter(patch: Partial<Query>) {
    setQuery((q) => ({ ...q, ...patch }));
  }
  function updated(ticket: Ticket) {
    queue.replace(ticket);
    setSelected((t) => (t?.id === ticket.id ? ticket : t));
    setSummaryVersion((v) => v + 1);
  }
  async function mutate(ticket: Ticket, patch: Partial<Ticket>) {
    setPending(ticket.id);
    setError("");
    try {
      updated(await api.update(ticket.id, patch));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(undefined);
    }
  }
  async function select(id: string) {
    setPending("detail");
    setError("");
    try {
      setSelected(await api.ticket(id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(undefined);
    }
  }
  return (
    <div className="shell">
      <nav className="sidebar" aria-label="Main navigation">
        <div className="brand">
          <span className="brand-mark">R</span>RelayOps
        </div>
        <span className="workspace">OPERATIONS WORKSPACE</span>
        <a href="#queue" aria-current="page">
          ▤ <span>Work queue</span>
          <span className="nav-dot" />
        </a>
        <div className="sidebar-bottom">
          <div className="avatar">MC</div>
          <div>
            Maya Chen<small>Operations specialist</small>
          </div>
        </div>
      </nav>
      <main id="queue">
        <header>
          <div>
            <p className="eyebrow">OPERATIONS / SERVICE DESK</p>
            <h1>Work queue</h1>
            <p className="subtitle">Keep customer requests moving.</p>
          </div>
          <div className="team-control">
            <span className="live-dot" />
            Local workspace
            <label>
              Team
              <select
                aria-label="Team"
                value={query.teamId}
                onChange={(e) => {
                  filter({ teamId: e.target.value });
                  setSelected(undefined);
                }}
              >
                {teams.length ? (
                  teams.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))
                ) : (
                  <option value="platform">Platform support</option>
                )}
              </select>
            </label>
          </div>
        </header>
        <section className="summary" aria-label="Queue summary">
          {[
            ["Open tickets", summary?.open],
            ["Urgent & open", summary?.urgent],
            ["Assigned to me", summary?.mine],
            ["Resolved", summary?.resolved],
          ].map(([label, value], i) => (
            <div key={label} className={`metric metric-${i}`}>
              <span>{label}</span>
              <strong>{value ?? "—"}</strong>
              <small>{i === 2 ? "Maya Chen" : "Current team"}</small>
            </div>
          ))}
        </section>
        <div className="content">
          <section className="queue-panel" aria-label="Work queue">
            <div className="panel-title">
              <h2>
                Incoming requests <span>{queue.data?.total ?? "—"}</span>
              </h2>
              <button onClick={() => void queue.refresh()}>↻ Refresh</button>
            </div>
            <div className="filters">
              <label className="search">
                Search tickets
                <input
                  type="search"
                  placeholder="Search title, customer or ID"
                  maxLength={200}
                  value={query.q}
                  onChange={(e) => filter({ q: e.target.value })}
                />
              </label>
              <label>
                Status
                <select
                  aria-label="Status"
                  value={query.status}
                  onChange={(e) => filter({ status: e.target.value })}
                >
                  <option value="">All statuses</option>
                  {statuses.map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </label>
              <label>
                Priority
                <select
                  aria-label="Filter priority"
                  value={query.priority}
                  onChange={(e) => filter({ priority: e.target.value })}
                >
                  <option value="">All priorities</option>
                  {priorities.map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </label>
              <label>
                Sort
                <select
                  aria-label="Sort"
                  value={query.sort}
                  onChange={(e) => filter({ sort: e.target.value })}
                >
                  <option value="updated">Recently updated</option>
                  <option value="created">Newest first</option>
                  <option value="priority">Priority</option>
                </select>
              </label>
            </div>
            {(error || queue.error) && (
              <div role="alert" className="error">
                {error || queue.error}
                <button
                  onClick={() => {
                    setError("");
                    void queue.refresh();
                  }}
                >
                  Retry queue
                </button>
              </div>
            )}
            <div className="queue-status" role="status">
              {queue.loading
                ? queue.data
                  ? "Refreshing requests…"
                  : "Loading requests…"
                : pending === "detail"
                  ? "Opening ticket…"
                  : "Queue ready"}
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Request</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Assignee</th>
                  </tr>
                </thead>
                <tbody>
                  {queue.data?.items.map((t) => (
                    <tr
                      key={t.id}
                      className={selected?.id === t.id ? "selected" : ""}
                    >
                      <td>
                        <small>
                          {t.id} ·{" "}
                          {teams.find((team) => team.id === t.teamId)?.name}
                        </small>
                        <button
                          className="ticket-link"
                          onClick={() => void select(t.id)}
                        >
                          {t.title}
                        </button>
                        <span className="customer-name">{t.customer}</span>
                      </td>
                      <td>
                        <select
                          className={`status status-${t.status.replaceAll(" ", "").toLowerCase()}`}
                          aria-label={`Status for ${t.id}`}
                          value={t.status}
                          disabled={pending === t.id}
                          onChange={(e) =>
                            void mutate(t, {
                              status: e.target.value as Ticket["status"],
                            })
                          }
                        >
                          {statuses.map((s) => (
                            <option key={s}>{s}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <span
                          className={`priority priority-${t.priority.toLowerCase()}`}
                        >
                          ● {t.priority}
                        </span>
                      </td>
                      <td>
                        <select
                          aria-label={`Assignee for ${t.id}`}
                          value={t.assigneeId ?? ""}
                          disabled={pending === t.id}
                          onChange={(e) =>
                            void mutate(t, {
                              assigneeId: e.target.value || null,
                            })
                          }
                        >
                          <option value="">Unassigned</option>
                          {operators
                            .filter((o) => o.teamId === t.teamId)
                            .map((o) => (
                              <option value={o.id} key={o.id}>
                                {o.name}
                              </option>
                            ))}
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!queue.loading && queue.data?.items.length === 0 && (
              <div className="empty">
                <h3>No requests to show</h3>
                <p>Try another search or filter.</p>
              </div>
            )}
            <footer>
              <span>
                {queue.data?.total ?? 0} requests · Page {query.page} of{" "}
                {queue.data?.totalPages ?? 1}
              </span>
              <div>
                <button
                  aria-label="Previous page"
                  disabled={query.page === 1 || queue.loading}
                  onClick={() => filter({ page: query.page - 1 })}
                >
                  ← Previous
                </button>
                <button
                  aria-label="Next page"
                  disabled={
                    !queue.data ||
                    query.page >= queue.data.totalPages ||
                    queue.loading
                  }
                  onClick={() => filter({ page: query.page + 1 })}
                >
                  Next →
                </button>
              </div>
            </footer>
          </section>
          {selected && (
            <TicketDetail
              key={selected.id}
              ticket={selected}
              operators={operators}
              onUpdate={updated}
              onClose={() => setSelected(undefined)}
            />
          )}
        </div>
        <p className="workspace-note">
          RelayOps / Internal operations · All customer records in this
          workspace are fictional.
        </p>
      </main>
    </div>
  );
}
