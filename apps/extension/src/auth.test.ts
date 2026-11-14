import { afterEach, beforeEach, expect, it, vi } from "vitest";

let stored: Record<string, unknown>;
const setAccessLevel = vi.fn(async () => {});
const localSet = vi.fn(async () => {});

beforeEach(() => {
  vi.resetModules();
  stored = {};
  setAccessLevel.mockClear();
  localSet.mockClear();
  vi.stubGlobal("chrome", {
    storage: {
      local: { set: localSet },
      session: {
        setAccessLevel,
        get: vi.fn(async (key: string) => ({ [key]: stored[key] })),
        set: vi.fn(async (value: Record<string, unknown>) => Object.assign(stored, value)),
        remove: vi.fn(async (key: string) => {
          delete stored[key];
        }),
      },
    },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("stores the bearer only in trusted session storage and scopes it to its server", async () => {
  const { saveAuthSession, withAuth } = await import("./auth");
  await saveAuthSession({
    serverUrl: "https://tracker.example.test",
    accessToken: "session-secret",
    expiresAt: Date.now() + 60_000,
    user: {
      account_id: "00000000-0000-4000-8000-000000000001",
      email: "person@example.com",
      email_verified: true,
    },
  });

  const authorized = await withAuth("https://tracker.example.test", { method: "GET" });
  const otherServer = await withAuth("https://other.example.test", { method: "GET" });

  expect(setAccessLevel).toHaveBeenCalledWith({ accessLevel: "TRUSTED_CONTEXTS" });
  expect(new Headers(authorized?.headers).get("Authorization")).toBe("Bearer session-secret");
  expect(otherServer).toEqual({ method: "GET" });
  expect(localSet).not.toHaveBeenCalled();
});

it("discards expired tokens and allows insecure auth transport only on loopback", async () => {
  const { isSecureAuthServer, saveAuthSession, withAuth } = await import("./auth");
  await saveAuthSession({
    serverUrl: "https://tracker.example.test",
    accessToken: "expired-secret",
    expiresAt: Date.now() - 1,
    user: {
      account_id: "00000000-0000-4000-8000-000000000001",
      email: "person@example.com",
      email_verified: true,
    },
  });

  await expect(withAuth("https://tracker.example.test", { method: "GET" })).resolves.toEqual({
    method: "GET",
  });
  expect(stored).toEqual({});
  expect(isSecureAuthServer("https://tracker.example.test")).toBe(true);
  expect(isSecureAuthServer("http://localhost:3456")).toBe(true);
  expect(isSecureAuthServer("http://tracker.example.test")).toBe(false);
});
