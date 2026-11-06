export type AuthUser = {
  id: string;
  email: string;
  is_email_verified: boolean;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
};

export type ApiMessage = { message: string };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const apiPrefix = "/api/v1";
let accessToken: string | null = null;

export function setAccessToken(value: string | null) {
  accessToken = value;
}

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const entry = document.cookie
    .split(";")
    .map((cookie) => cookie.trim())
    .find((cookie) => cookie.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

async function ensureCsrfCookie() {
  if (readCookie("csrf_token")) return;
  await fetch(`${apiPrefix}/auth/csrf`, { credentials: "include" });
}

async function rawRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${apiPrefix}${path}`, {
    ...init,
    credentials: "include",
  });
  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Use the generic message when the server does not return JSON.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function refreshSession(): Promise<AuthResponse | null> {
  try {
    await ensureCsrfCookie();
    const csrf = readCookie("csrf_token");
    const result = await rawRequest<AuthResponse>("/auth/refresh", {
      method: "POST",
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
    });
    accessToken = result.access_token;
    return result;
  } catch {
    accessToken = null;
    return null;
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? "GET").toUpperCase();
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (!new Set(["GET", "HEAD", "OPTIONS"]).has(method)) {
    await ensureCsrfCookie();
    const csrf = readCookie("csrf_token");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  try {
    return await rawRequest<T>(path, { ...init, headers });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401 && retry && accessToken) {
      const refreshed = await refreshSession();
      if (refreshed) return apiRequest<T>(path, init, false);
    }
    throw error;
  }
}

export const authApi = {
  login: (email: string, password: string) =>
    apiRequest<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    apiRequest<ApiMessage>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => apiRequest<AuthUser>("/auth/me"),
  logout: () => apiRequest<void>("/auth/logout", { method: "POST" }),
  forgotPassword: (email: string) =>
    apiRequest<ApiMessage>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, password: string) =>
    apiRequest<ApiMessage>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),
  verifyEmail: (token: string) =>
    apiRequest<ApiMessage>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email: string) =>
    apiRequest<ApiMessage>("/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
};