import type { AuthenticatedUser } from "@job-tracker/shared/api";

const AUTH_SESSION_KEY = "accountAuthSession";

export interface AuthSession {
  serverUrl: string;
  accessToken: string;
  expiresAt: number;
  user: AuthenticatedUser;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isAuthenticatedUser(value: unknown): value is AuthenticatedUser {
  return (
    isRecord(value) &&
    typeof value.account_id === "string" &&
    typeof value.email === "string" &&
    typeof value.email_verified === "boolean"
  );
}

function isAuthSession(value: unknown): value is AuthSession {
  return (
    isRecord(value) &&
    typeof value.serverUrl === "string" &&
    typeof value.accessToken === "string" &&
    value.accessToken.length > 0 &&
    typeof value.expiresAt === "number" &&
    isAuthenticatedUser(value.user)
  );
}

let storageAccess: Promise<void> | undefined;

async function restrictAuthStorage(): Promise<void> {
  storageAccess ??= chrome.storage.session.setAccessLevel({
    accessLevel: "TRUSTED_CONTEXTS",
  });
  await storageAccess;
}

export function isSecureAuthServer(serverUrl: string): boolean {
  const url = new URL(serverUrl);
  const loopback = ["localhost", "127.0.0.1", "::1", "[::1]"].includes(url.hostname);
  return url.protocol === "https:" || loopback;
}

export async function readAuthSession(serverUrl: string): Promise<AuthSession | null> {
  await restrictAuthStorage();
  const stored = await chrome.storage.session.get(AUTH_SESSION_KEY);
  const session: unknown = stored[AUTH_SESSION_KEY];
  if (session === undefined) return null;
  if (
    !isAuthSession(session) ||
    session.serverUrl !== serverUrl ||
    session.expiresAt <= Date.now()
  ) {
    await chrome.storage.session.remove(AUTH_SESSION_KEY);
    return null;
  }
  return session;
}

export async function saveAuthSession(session: AuthSession): Promise<void> {
  await restrictAuthStorage();
  await chrome.storage.session.set({ [AUTH_SESSION_KEY]: session });
}

export async function clearAuthSession(serverUrl?: string): Promise<void> {
  await restrictAuthStorage();
  if (serverUrl !== undefined) {
    const stored = await chrome.storage.session.get(AUTH_SESSION_KEY);
    const session: unknown = stored[AUTH_SESSION_KEY];
    if (isAuthSession(session) && session.serverUrl !== serverUrl) return;
  }
  await chrome.storage.session.remove(AUTH_SESSION_KEY);
}

export async function withAuth(
  serverUrl: string,
  init?: RequestInit,
): Promise<RequestInit | undefined> {
  const session = await readAuthSession(serverUrl);
  if (!session || !isSecureAuthServer(serverUrl)) return init;

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${session.accessToken}`);
  return { ...init, headers, redirect: "error" };
}
