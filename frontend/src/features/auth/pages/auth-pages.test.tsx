import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/features/auth/components/AuthProvider";
import { ProtectedRoute } from "@/features/auth/components/ProtectedRoute";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { setAccessToken } from "@/features/auth/services/auth-api";

const user = { id: "user-1", email: "member@example.com", is_email_verified: true };

function stubFetch(handler: (url: string, init?: RequestInit) => Response) {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
    Promise.resolve(handler(String(input), init)),
  ));
}

describe("authentication screens", () => {
  beforeEach(() => {
    document.cookie = "csrf_token=test-token.signature; path=/";
  });

  afterEach(() => {
    cleanup();
    setAccessToken(null);
    document.cookie = "csrf_token=; Max-Age=0; path=/";
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("validates registration fields before making an API request", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const viewer = userEvent.setup();
    render(
      <MemoryRouter>
        <AuthProvider><RegisterPage /></AuthProvider>
      </MemoryRouter>,
    );

    await viewer.type(screen.getByLabelText("Email"), "not-an-email");
    await viewer.type(screen.getByLabelText("Password"), "short");
    await viewer.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(screen.getByText("Use at least eight characters")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("/auth/register"), expect.anything());
  });

  it("logs in and redirects after a successful response", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) return Promise.resolve(new Response("", { status: 401 }));
      if (url.endsWith("/auth/login")) {
        expect(JSON.parse(String(init?.body))).toEqual({ email: user.email, password: "ValidPassword!42" });
        return Promise.resolve(new Response(JSON.stringify({ access_token: "access", token_type: "bearer", expires_in: 900, user }), { status: 200 }));
      }
      if (url.endsWith("/auth/csrf")) return Promise.resolve(new Response(JSON.stringify({ message: "ready" }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify(user), { status: 200 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const viewer = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<h1>Signed in</h1>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    await viewer.type(screen.getByLabelText("Email"), user.email);
    await viewer.type(screen.getByLabelText("Password"), "ValidPassword!42");
    await viewer.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "Signed in" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/auth/login"), expect.objectContaining({ method: "POST" }));
  });

  it("redirects anonymous visitors away from protected routes", async () => {
    stubFetch((url) => url.endsWith("/auth/refresh")
      ? new Response("", { status: 401 })
      : new Response(JSON.stringify({ message: "ready" }), { status: 200 }));
    render(
      <MemoryRouter initialEntries={["/private"]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<h1>Sign in</h1>} />
            <Route path="/private" element={<ProtectedRoute><h1>Private data</h1></ProtectedRoute>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Private data")).not.toBeInTheDocument());
  });
});