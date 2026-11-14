import { afterEach, expect, it, vi } from "vitest";
import { api } from "./client";

afterEach(() => vi.unstubAllGlobals());

it("uses the OpenAPI auth routes and JSON request bodies", async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response("{}")));
  vi.stubGlobal("fetch", fetcher);

  await api.register({ email: "person@example.com", password: "example-password-long" });
  await api.requestVerification({ email: "person@example.com" });
  await api.verifyEmail({ token: "verification-token" });
  await api.requestPasswordReset({ email: "person@example.com" });
  await api.resetPassword({ token: "reset-token", password: "new-example-password" });

  expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
    "/api/v1/auth/register",
    "/api/v1/auth/verification-requests",
    "/api/v1/auth/verify-email",
    "/api/v1/auth/password-reset-requests",
    "/api/v1/auth/password-resets",
  ]);
  expect(fetcher).toHaveBeenNthCalledWith(
    1,
    "/api/v1/auth/register",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ email: "person@example.com", password: "example-password-long" }),
    }),
  );
});
