import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "@/app/App";
import { setAccessToken } from "@/features/auth/services/auth-api";

describe("application shell", () => {
  afterEach(() => {
    cleanup();
    setAccessToken(null);
    document.cookie = "csrf_token=; Max-Age=0; path=/";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders the dashboard, service status, and theme control", async () => {
    document.cookie = "csrf_token=test-token.signature; path=/";
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      const body = url.includes("/auth/refresh")
        ? {
            access_token: "test-access-token",
            token_type: "bearer",
            expires_in: 900,
            user: { id: "user-1", email: "member@example.com", is_email_verified: true },
          }
        : url.includes("/auth/me")
          ? { id: "user-1", email: "member@example.com", is_email_verified: true }
          : { status: "ok", database: "connected" };
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }));

    const user = userEvent.setup();
    render(<App />);

    expect(
      await screen.findByRole("heading", { name: /make room for what's next/i }),
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
