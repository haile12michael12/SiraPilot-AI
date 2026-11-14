import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { authUserKey, useCurrentUser, useLogin, useLogout } from "./queries";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("refreshes the session query after login without storing the cookie token", async () => {
  const user = {
    account_id: "00000000-0000-4000-8000-000000000001",
    email: "person@example.com",
    email_verified: true,
  };
  const login = {
    account_id: user.account_id,
    email: user.email,
    expires_in: 3600,
  };
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: {
            status: 401,
            code: "unauthorized",
            message: "Authentication required.",
            request_id: "request-1",
          },
        }),
        { status: 401 },
      ),
    )
    .mockResolvedValueOnce(new Response(JSON.stringify(login)))
    .mockResolvedValueOnce(new Response(JSON.stringify(user)));
  vi.stubGlobal("fetch", fetcher);
  const setItem = vi.spyOn(Storage.prototype, "setItem");

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  const { result } = renderHook(() => ({ currentUser: useCurrentUser(), login: useLogin() }), {
    wrapper: Wrapper,
  });

  await waitFor(() => expect(result.current.currentUser.isError).toBe(true));
  await act(async () => {
    await result.current.login.mutateAsync({
      email: user.email,
      password: "example-password-long",
    });
  });
  await waitFor(() => expect(result.current.currentUser.data).toEqual(user));

  expect(fetcher).toHaveBeenNthCalledWith(
    2,
    "/api/v1/auth/sessions",
    expect.objectContaining({ credentials: "same-origin", method: "POST" }),
  );
  expect(setItem).not.toHaveBeenCalled();
});

it("removes the cached session after logout succeeds", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", fetcher);

  const queryClient = new QueryClient();
  queryClient.setQueryData(authUserKey, {
    account_id: "00000000-0000-4000-8000-000000000001",
    email: "person@example.com",
    email_verified: true,
  });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  const { result } = renderHook(() => useLogout(), { wrapper: Wrapper });

  await act(async () => {
    await result.current.mutateAsync();
  });

  expect(queryClient.getQueryData(authUserKey)).toBeUndefined();
  expect(fetcher).toHaveBeenCalledWith(
    "/api/v1/auth/logout",
    expect.objectContaining({ credentials: "same-origin", method: "POST" }),
  );
});
