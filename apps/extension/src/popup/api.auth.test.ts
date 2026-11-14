import { afterEach, beforeEach, expect, it, vi } from "vitest";

const user = {
  account_id: "00000000-0000-4000-8000-000000000001",
  email: "person@example.com",
  email_verified: true,
};
let storedSession: unknown;
const setAccessLevel = vi.fn(async () => {});
const localSet = vi.fn(async () => {});
const sendMessage = vi.fn(async () => {});

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("VITE_SERVER_URL", "https://tracker.example.test");
  storedSession = undefined;
  setAccessLevel.mockClear();
  localSet.mockClear();
  sendMessage.mockClear();
  vi.stubGlobal("chrome", {
    storage: {
      local: {
        get: (_key: string, callback: (data: object) => void) => callback({}),
        set: localSet,
      },
      onChanged: { addListener: vi.fn() },
      session: {
        setAccessLevel,
        get: vi.fn(async (key: string) => ({ [key]: storedSession })),
        set: vi.fn(async (value: Record<string, unknown>) => {
          storedSession = value.accountAuthSession;
        }),
        remove: vi.fn(async () => {
          storedSession = undefined;
        }),
      },
    },
    runtime: { sendMessage, lastError: undefined },
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

it("signs in with an extension bearer, uses it for API requests, then revokes it on sign-out", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          account_id: user.account_id,
          email: user.email,
          expires_in: 3600,
          access_token: "extension-session-secret",
          token_type: "Bearer",
        }),
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify(user)))
    .mockResolvedValueOnce(new Response("[]"))
    .mockResolvedValueOnce(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);

  const { searchJobs, signIn, signOut } = await import("./api");
  await expect(signIn({ email: user.email, password: "example-password-long" })).resolves.toEqual(
    user,
  );

  expect(fetcher).toHaveBeenNthCalledWith(
    1,
    "https://tracker.example.test/api/v1/auth/sessions",
    expect.objectContaining({
      method: "POST",
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
    }),
  );
  expect(fetcher).toHaveBeenNthCalledWith(
    2,
    "https://tracker.example.test/api/v1/auth/me",
    expect.objectContaining({
      credentials: "omit",
      headers: expect.objectContaining({ Authorization: "Bearer extension-session-secret" }),
    }),
  );
  expect(storedSession).toMatchObject({
    accessToken: "extension-session-secret",
    serverUrl: "https://tracker.example.test",
  });
  expect(setAccessLevel).toHaveBeenCalledWith({ accessLevel: "TRUSTED_CONTEXTS" });
  expect(localSet).not.toHaveBeenCalled();

  await searchJobs("engineer");
  expect(fetcher.mock.calls[2][0]).toBe("https://tracker.example.test/api/jobs?q=engineer&limit=8");
  expect(fetcher.mock.calls[2][1]?.credentials).toBe("omit");
  expect(new Headers(fetcher.mock.calls[2][1]?.headers).get("Authorization")).toBe(
    "Bearer extension-session-secret",
  );

  await signOut();
  expect(fetcher).toHaveBeenNthCalledWith(
    4,
    "https://tracker.example.test/api/v1/auth/logout",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({ Authorization: "Bearer extension-session-secret" }),
    }),
  );
  expect(storedSession).toBeUndefined();
  expect(JSON.stringify(sendMessage.mock.calls)).not.toContain("extension-session-secret");
});

it("requires HTTPS for account sign-in on non-loopback servers", async () => {
  vi.stubEnv("VITE_SERVER_URL", "http://tracker.example.test");
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  const { signIn } = await import("./api");

  await expect(signIn({ email: user.email, password: "example-password-long" })).rejects.toThrow(
    "Sign-in requires HTTPS",
  );
  expect(fetcher).not.toHaveBeenCalled();
  expect(storedSession).toBeUndefined();
});
