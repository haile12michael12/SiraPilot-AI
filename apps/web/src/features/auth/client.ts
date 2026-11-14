import type {
  AuthAccepted,
  AuthenticatedUser,
  AuthLoginRequest,
  AuthLoginResponse,
  AuthPasswordResetRequest,
  AuthPasswordUpdated,
  AuthRegistrationRequest,
  AuthTokenRequest,
  AuthVerificationRequest,
  AuthVerified,
} from "@job-tracker/shared/api";
import { request } from "../../infra/http";

export const api = {
  getCurrentUser: (): Promise<AuthenticatedUser> => request("/v1/auth/me"),

  login: (body: AuthLoginRequest): Promise<AuthLoginResponse> =>
    request("/v1/auth/sessions", { method: "POST", body: JSON.stringify(body) }),

  logout: (): Promise<void> => request("/v1/auth/logout", { method: "POST" }),

  register: (body: AuthRegistrationRequest): Promise<AuthAccepted> =>
    request("/v1/auth/register", { method: "POST", body: JSON.stringify(body) }),

  requestVerification: (body: AuthVerificationRequest): Promise<AuthAccepted> =>
    request("/v1/auth/verification-requests", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  verifyEmail: (body: AuthTokenRequest): Promise<AuthVerified> =>
    request("/v1/auth/verify-email", { method: "POST", body: JSON.stringify(body) }),

  requestPasswordReset: (body: AuthVerificationRequest): Promise<AuthAccepted> =>
    request("/v1/auth/password-reset-requests", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  resetPassword: (body: AuthPasswordResetRequest): Promise<AuthPasswordUpdated> =>
    request("/v1/auth/password-resets", { method: "POST", body: JSON.stringify(body) }),
};
