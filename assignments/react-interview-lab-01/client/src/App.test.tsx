import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse, delay } from "msw";
import { describe, expect, it } from "vitest";
import App from "./App";
import { network, store } from "../test/setup";
async function open() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("button", { name: "Payment reconciliation pending" });
  return user;
}
describe("Operations work queue", () => {
  it("loads API tickets and team summary", async () => {
    await open();
    expect(screen.getByRole("heading", { name: "Work queue" })).toBeVisible();
    expect(screen.getByText("90 requests · Page 1 of 9")).toBeVisible();
    expect(screen.getByLabelText("Queue summary")).toHaveTextContent(
      "Open tickets",
    );
  });
  it("searches by customer and ticket reference", async () => {
    const user = await open();
    await user.type(screen.getByRole("searchbox"), "ROP-1001");
    await waitFor(() => expect(screen.getAllByRole("row")).toHaveLength(2));
    expect(
      screen.getByRole("button", { name: "Webhook delivery delayed" }),
    ).toBeVisible();
  });
  it("filters status and priority together", async () => {
    const user = await open();
    await user.selectOptions(
      screen.getByLabelText("Status", { exact: true }),
      "New",
    );
    await user.selectOptions(
      screen.getByLabelText("Filter priority"),
      "Urgent",
    );
    await waitFor(() =>
      expect(screen.getAllByRole("row").length).toBeGreaterThan(1),
    );
    await waitFor(() =>
      expect(screen.getByText(/requests · Page/)).toHaveTextContent(
        "5 requests",
      ),
    );
    for (const select of screen.getAllByLabelText(/^Status for/))
      expect(select).toHaveValue("New");
  });
  it("navigates between pages", async () => {
    const user = await open();
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("90 requests · Page 2 of 9");
    await user.click(screen.getByRole("button", { name: "Previous page" }));
    await screen.findByText("90 requests · Page 1 of 9");
  });
  it("shows matching requests after narrowing a later queue page", async () => {
    const user = await open();
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("90 requests · Page 2 of 9");
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await screen.findByText("90 requests · Page 3 of 9");
    await user.type(screen.getByRole("searchbox"), "ROP-1001");
    await screen.findByText(/1 requests · Page/);
    expect(
      await screen.findByRole("button", { name: "Webhook delivery delayed" }),
    ).toBeVisible();
  });
  it("opens details and saves an internal note", async () => {
    const user = await open();
    await user.click(
      screen.getAllByRole("button", {
        name: "Payment reconciliation pending",
      })[0],
    );
    const detail = await screen.findByRole("complementary", {
      name: "Ticket detail",
    });
    const input = within(detail).getByLabelText("Internal note");
    await user.clear(input);
    await user.type(input, "Confirmed with the customer contact.");
    await user.click(within(detail).getByRole("button", { name: "Save note" }));
    await within(detail).findByText("Note saved");
    expect(
      store.tickets.some(
        (t) => t.note === "Confirmed with the customer contact.",
      ),
    ).toBe(true);
    await user.click(screen.getByLabelText("Close ticket"));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });
  it("updates a status through the queue", async () => {
    const user = await open();
    const status = screen.getAllByLabelText(/^Status for/)[0];
    await user.selectOptions(status, "Triaged");
    await waitFor(() => expect(status).toHaveValue("Triaged"));
    expect(
      store.get(status.getAttribute("aria-label")!.replace("Status for ", ""))
        ?.status,
    ).toBe("Triaged");
  });
  it("reports network errors and allows retry", async () => {
    network.use(
      http.get("/api/tickets", () =>
        HttpResponse.json(
          { message: "Queue temporarily unavailable" },
          { status: 503 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Queue temporarily unavailable",
    );
    network.resetHandlers();
    await user.click(screen.getByRole("button", { name: "Retry queue" }));
    await screen.findByRole("button", {
      name: "Payment reconciliation pending",
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("announces loading while a request is in progress", async () => {
    let release!: () => void;
    const gate = new Promise<void>((r) => {
      release = r;
    });
    network.use(
      http.get("/api/tickets", async () => {
        await gate;
        await delay(0);
        return HttpResponse.json(
          store.list({
            teamId: "platform",
            q: "",
            status: "",
            priority: "",
            sort: "updated",
            page: 1,
            pageSize: 10,
          }),
        );
      }),
    );
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading requests");
    release();
    await screen.findByRole("button", {
      name: "Payment reconciliation pending",
    });
  });
  it("shows an empty state for a search with no matches", async () => {
    const user = await open();
    await user.type(screen.getByRole("searchbox"), "no-such-customer");
    await screen.findByRole("heading", { name: "No requests to show" });
  });
});
