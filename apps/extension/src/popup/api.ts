import { copy } from "./copy";
// The extension origin fetches the API directly; content scripts use the CSP-safe worker proxy.
import { API_BASE_URL, SERVER_URL, serverScope, initializeServerConfig } from "../config.js";
import type { BridgeRequest } from "../messages.js";
import type {
  AuthLoginRequest,
  AuthLoginResponse,
  AuthenticatedUser,
  NotificationItem,
  ReminderCreate,
} from "@job-tracker/shared/api";
import {
  clearAuthSession,
  isSecureAuthServer,
  readAuthSession,
  saveAuthSession,
  withAuth,
} from "../auth.js";

export { API_BASE_URL as BASE_URL } from "../config.js";

async function api(path: string, opts?: RequestInit) {
  await initializeServerConfig();
  const server = SERVER_URL;
  const requestInit = await withAuth(server, opts);
  if (server !== SERVER_URL) throw new Error(copy.api.serverChangedRetryThisAction);
  const res = await fetch(`${server}/api${path}`, {
    ...requestInit,
    credentials: "omit",
  });
  if (server !== SERVER_URL) throw new Error(copy.api.serverChangedRetryThisAction);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  const result = res.status === 204 ? null : await res.json();
  if (server !== SERVER_URL) throw new Error(copy.api.serverChangedRetryThisAction);
  if (opts?.method && opts.method !== "GET") notifyChange();
  return result;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

type ExtensionLoginResponse = AuthLoginResponse & {
  access_token: string;
  token_type: "Bearer";
};

function isLoginResponse(value: unknown): value is ExtensionLoginResponse {
  return (
    isRecord(value) &&
    typeof value.account_id === "string" &&
    typeof value.email === "string" &&
    typeof value.expires_in === "number" &&
    Number.isFinite(value.expires_in) &&
    value.expires_in > 0 &&
    typeof value.access_token === "string" &&
    value.access_token.trim().length > 0 &&
    value.token_type === "Bearer"
  );
}

function isAuthenticatedUser(value: unknown): value is AuthenticatedUser {
  return (
    isRecord(value) &&
    typeof value.account_id === "string" &&
    typeof value.email === "string" &&
    typeof value.email_verified === "boolean"
  );
}

function authError(status: number): Error {
  if (status === 401) return new Error(copy.account.invalidCredentials);
  if (status === 403) return new Error(copy.account.extensionNotAllowed);
  if (status === 503) return new Error(copy.account.signInNotConfigured);
  return new Error(copy.account.signInFailed);
}

async function authJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new Error(copy.account.invalidServerResponse);
  }
}

async function authFetch(server: string, path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${server}/api/v1/auth${path}`, {
    ...init,
    cache: "no-store",
    credentials: "omit",
    redirect: "error",
  });
  if (server !== SERVER_URL) throw new Error(copy.api.serverChangedRetryThisAction);
  return response;
}

export async function signIn(credentials: AuthLoginRequest): Promise<AuthenticatedUser> {
  await initializeServerConfig();
  const server = SERVER_URL;
  if (!isSecureAuthServer(server)) throw new Error(copy.account.httpsRequired);

  const response = await authFetch(server, "/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  if (!response.ok) throw authError(response.status);
  const login = await authJson(response);
  if (!isLoginResponse(login)) throw new Error(copy.account.extensionNotAllowed);

  const userResponse = await authFetch(server, "/me", {
    headers: { Authorization: `Bearer ${login.access_token}` },
  });
  if (!userResponse.ok) throw authError(userResponse.status);
  const user = await authJson(userResponse);
  if (!isAuthenticatedUser(user)) throw new Error(copy.account.invalidServerResponse);
  if (server !== SERVER_URL) throw new Error(copy.api.serverChangedRetryThisAction);

  await saveAuthSession({
    serverUrl: server,
    accessToken: login.access_token,
    expiresAt: Date.now() + login.expires_in * 1000,
    user,
  });
  if (server !== SERVER_URL) {
    await clearAuthSession(server);
    throw new Error(copy.api.serverChangedRetryThisAction);
  }
  return user;
}

export async function currentAccount(): Promise<AuthenticatedUser | null> {
  await initializeServerConfig();
  const server = SERVER_URL;
  const session = await readAuthSession(server);
  if (!session) return null;
  if (!isSecureAuthServer(server)) {
    await clearAuthSession(server);
    return null;
  }

  const response = await authFetch(server, "/me", {
    headers: { Authorization: `Bearer ${session.accessToken}` },
  });
  if (response.status === 401) {
    await clearAuthSession(server);
    return null;
  }
  if (!response.ok) throw authError(response.status);
  const user = await authJson(response);
  if (!isAuthenticatedUser(user)) throw new Error(copy.account.invalidServerResponse);

  await saveAuthSession({ ...session, user });
  return user;
}

export async function signOut(): Promise<void> {
  await initializeServerConfig();
  const server = SERVER_URL;
  const session = await readAuthSession(server);
  if (!session) return;
  if (!isSecureAuthServer(server)) {
    await clearAuthSession(server);
    return;
  }

  const response = await authFetch(server, "/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${session.accessToken}` },
  });
  if (response.ok || response.status === 401) {
    await clearAuthSession(server);
    return;
  }
  throw authError(response.status);
}

// Notify the worker after direct writes so other tabs invalidate their read models.
// A missed notification cannot turn a successful mutation into an error.
function notifyChange(): void {
  const msg: BridgeRequest = { type: "notify-change", ...serverScope() };
  chrome.runtime.sendMessage(msg).catch(() => {});
}

export const searchJobs = (q: string) => api(`/jobs?${new URLSearchParams({ q, limit: "8" })}`);

function markManualClosures(events: unknown[]): unknown[] {
  return events.map((item) => {
    if (typeof item !== "object" || item === null || !("event" in item) || item.event !== "closed")
      return item;
    const meta =
      "meta" in item && typeof item.meta === "object" && item.meta !== null ? item.meta : {};
    return { ...item, meta: { ...meta, source: "manual" } };
  });
}

// `ts` (UTC ISO) back-dates the events to when they really happened — e.g. the
// received date of the open Gmail rejection the user is recording by hand.
// Omitted → the server stamps now().
export const postEvents = (jobId: string, events: unknown[], ts?: string) =>
  api("/events", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_id: jobId,
      events: markManualClosures(events),
      ...(ts ? { ts } : {}),
    }),
  });

export const noteTitles = () => api("/meta/note-titles").catch(() => []);

// Manual listings mint a platform ID because no external natural key exists.
// via=manual preserves provenance; the server creates the owning job.
export const createListing = (body: unknown) =>
  api("/listings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// Full job record for attaching a comment to the latest status event.
export const getJob = (jobId: string) => api(`/jobs/${jobId}`);

export const createReminder = (body: ReminderCreate): Promise<NotificationItem> =>
  api("/notifications", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

// Enrich an already-logged event with meta after the fact. Replaces the whole meta
// bag, but the verb and timestamp are immutable, so this only adds or updates the
// note on a transition — never its status.
export const patchEventMeta = (eventId: number, meta: unknown) =>
  api(`/events/${eventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ meta }),
  });

// Only opted-in callers send diagnostics. keepalive lets pagehide requests finish
// after teardown; failure must not affect the popup.
export function logSearch(body: unknown, keepalive = false): void {
  try {
    void initializeServerConfig()
      .then(async () => {
        const server = SERVER_URL;
        const requestInit = await withAuth(server, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          keepalive,
        });
        if (server !== SERVER_URL) return;
        return fetch(`${API_BASE_URL}/search-log`, {
          ...requestInit,
          credentials: "omit",
        });
      })
      .catch(() => {});
  } catch {
    /* offline or teardown; diagnostics are best-effort */
  }
}
