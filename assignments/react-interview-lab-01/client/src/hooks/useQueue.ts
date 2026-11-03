import { useCallback, useEffect, useRef, useState } from "react";
import type { Page, Query, Ticket } from "../../../shared/models";
import { api } from "../services/api";
const results = new Map<string, Page>();
export function clearQueueCache() {
  results.clear();
}
export function useQueue(query: Query) {
  const [data, setData] = useState<Page>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const load = useCallback(
    async (refresh = false) => {
      const current = ++generation.current;
      const key = JSON.stringify({
        q: query.q,
        status: query.status,
        priority: query.priority,
        sort: query.sort,
        page: query.page,
        pageSize: query.pageSize,
      });
      setError("");
      if (!refresh && results.has(key)) {
        setData(results.get(key));
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const page = await api.list(query, refresh);
        if (current === generation.current) {
          results.set(key, page);
          setData(page);
        }
      } catch (e) {
        if (current === generation.current) setError((e as Error).message);
      } finally {
        if (current === generation.current) setLoading(false);
      }
    },
    [query],
  );
  useEffect(() => {
    void load();
    return () => {
      generation.current++;
    };
  }, [load]);
  const replace = (ticket: Ticket) => {
    results.clear();
    setData((previous) =>
      previous
        ? {
            ...previous,
            items: previous.items.map((t) => (t.id === ticket.id ? ticket : t)),
          }
        : previous,
    );
  };
  return { data, loading, error, refresh: () => load(true), replace };
}
