import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "@/app/App";

describe("application shell", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the dashboard, service status, and theme control", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok", database: "connected" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const user = userEvent.setup();
    render(<App />);

    expect(
      screen.getByRole("heading", { name: /make room for what's next/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Main navigation" }),
    ).toHaveTextContent("Career profile");
    expect(await screen.findByText("All systems ready")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Switch to dark mode" }));
    expect(
      screen.getByRole("button", { name: "Switch to light mode" }),
    ).toBeInTheDocument();
  });
});
