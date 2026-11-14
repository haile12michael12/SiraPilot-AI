import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AccountSettings } from "./AccountSettings";
import { currentAccount, signIn, signOut } from "./api";

vi.mock("./api", () => ({
  currentAccount: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
}));

const user = {
  account_id: "00000000-0000-4000-8000-000000000001",
  email: "person@example.com",
  email_verified: true,
};
let container: HTMLDivElement;
let root: Root;

beforeEach(async () => {
  vi.stubGlobal("IS_REACT_ACT_ENVIRONMENT", true);
  vi.mocked(currentAccount).mockResolvedValue(null);
  vi.mocked(signIn).mockResolvedValue(user);
  vi.mocked(signOut).mockResolvedValue();
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
  await act(async () => root.render(<AccountSettings />));
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

async function change(selector: string, value: string) {
  const input = container.querySelector<HTMLInputElement>(selector)!;
  const valueDescriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
  if (!valueDescriptor?.set) throw new Error("The input value setter is unavailable.");
  const setValue = valueDescriptor.set.bind(input);
  await act(async () => {
    setValue(value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

async function click(label: string) {
  const button = [...container.querySelectorAll("button")].find(
    (candidate) => candidate.textContent?.trim() === label,
  );
  expect(button).toBeDefined();
  await act(async () => button!.click());
}

it("signs in and out without displaying or retaining the bearer token", async () => {
  await vi.waitFor(() => expect(container.querySelector("#account-email")).not.toBeNull());
  await change("#account-email", user.email);
  await change("#account-password", "example-password-long");
  await click("Sign in");

  await vi.waitFor(() =>
    expect(container.textContent).toContain("Signed in as person@example.com"),
  );
  expect(signIn).toHaveBeenCalledWith({
    email: user.email,
    password: "example-password-long",
  });
  expect(container.textContent).not.toContain("extension-session-secret");
  expect(container.querySelector("#account-password")).toBeNull();

  await click("Sign out");
  await vi.waitFor(() => expect(container.querySelector("#account-email")).not.toBeNull());
  expect(signOut).toHaveBeenCalledOnce();
});
