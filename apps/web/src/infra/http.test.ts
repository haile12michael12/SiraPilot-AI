import { afterEach, expect, it, vi } from "vitest";
import { request } from "./http";

afterEach(() => vi.unstubAllGlobals());

it("sends same-origin credentials through the dashboard API transport", async () => {
  const fetcher = vi.fn().mockImplementation(() => Promise.resolve(new Response('{"ok":true}')));
  vi.stubGlobal("fetch", fetcher);

  await expect(request("/v1/auth/me")).resolves.toEqual({ ok: true });
  expect(fetcher).toHaveBeenCalledExactlyOnceWith(
    "/api/v1/auth/me",
    expect.objectContaining({ credentials: "same-origin" }),
  );

  await request("/v1/auth/me", { credentials: "omit" });
  expect(fetcher).toHaveBeenNthCalledWith(
    2,
    "/api/v1/auth/me",
    expect.objectContaining({ credentials: "omit" }),
  );
});
