import { useEffect, useState } from "react";
import {
  priorities,
  statuses,
  type Activity,
  type Operator,
  type Ticket,
} from "../../../shared/models";
import { api } from "../services/api";
export function TicketDetail({
  ticket,
  operators,
  onUpdate,
  onClose,
}: {
  ticket: Ticket;
  operators: Operator[];
  onUpdate: (t: Ticket) => void;
  onClose: () => void;
}) {
  const [note, setNote] = useState(ticket.note);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [activity, setActivity] = useState<Activity[]>([]);
  useEffect(() => {
    setNote(ticket.note);
    setMessage("");
  }, [ticket]);
  useEffect(() => {
    let live = true;
    api
      .activity(ticket.id)
      .then((a) => {
        if (live) setActivity(a);
      })
      .catch(() => {
        if (live) setActivity([]);
      });
    return () => {
      live = false;
    };
  }, [ticket]);
  async function update(patch: Partial<Ticket>) {
    setBusy(true);
    setError("");
    try {
      onUpdate(await api.update(ticket.id, patch));
      if ("note" in patch) setMessage("Note saved");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className="detail" aria-label="Ticket detail">
      <div className="detail-heading">
        <span className="eyebrow">TICKET / {ticket.id}</span>
        <button onClick={onClose} aria-label="Close ticket">
          ×
        </button>
      </div>
      <h2>{ticket.title}</h2>
      <p className="customer">{ticket.customer}</p>
      <div className="tags">
        {ticket.tags.map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
      <p className="description">{ticket.description}</p>
      <div className="detail-fields">
        <label>
          Status
          <select
            aria-label="Detail status"
            disabled={busy}
            value={ticket.status}
            onChange={(e) =>
              void update({ status: e.target.value as Ticket["status"] })
            }
          >
            {statuses.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select
            aria-label="Detail priority"
            disabled={busy}
            value={ticket.priority}
            onChange={(e) =>
              void update({ priority: e.target.value as Ticket["priority"] })
            }
          >
            {priorities.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </label>
        <label>
          Assignee
          <select
            aria-label="Detail assignee"
            disabled={busy}
            value={ticket.assigneeId ?? ""}
            onChange={(e) =>
              void update({ assigneeId: e.target.value || null })
            }
          >
            <option value="">Unassigned</option>
            {operators
              .filter((o) => o.teamId === ticket.teamId)
              .map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
          </select>
        </label>
      </div>
      <div className="section-heading">
        <h3>Internal note</h3>
        <span>{note !== ticket.note ? "Unsaved changes" : "Up to date"}</span>
      </div>
      <label className="sr-only" htmlFor="note">
        Internal note
      </label>
      <textarea
        id="note"
        rows={6}
        maxLength={4000}
        value={note}
        onChange={(e) => {
          setNote(e.target.value);
          setMessage("");
        }}
      />
      <button
        className="primary"
        disabled={busy || note === ticket.note}
        onClick={() => void update({ note })}
      >
        {busy ? "Saving…" : "Save note"}
      </button>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <h3>Recent activity</h3>
      <ol className="activity">
        {activity.map((a) => (
          <li key={a.id}>
            <span>{a.text}</span>
            <time>{new Date(a.at).toLocaleString()}</time>
          </li>
        ))}
      </ol>
      <p className="muted">
        Created {new Date(ticket.createdAt).toLocaleString()}
        <br />
        Updated {new Date(ticket.updatedAt).toLocaleString()}
      </p>
    </aside>
  );
}
