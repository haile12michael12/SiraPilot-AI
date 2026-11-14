import { useEffect, useState } from "react";
import type { AuthenticatedUser } from "@job-tracker/shared/api";
import { copy } from "./copy";
import { BUTTON, INPUT, PRIMARY_BUTTON } from "./ui";
import { currentAccount, signIn, signOut } from "./api";

export function AccountSettings() {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void currentAccount()
      .then((account) => {
        if (active) setUser(account);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : copy.account.signInFailed);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    const submittedPassword = password;
    setPassword("");
    try {
      setUser(await signIn({ email, password: submittedPassword }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.account.signInFailed);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await signOut();
      setUser(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : copy.account.signOutFailed);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-2 border-b border-popup-border-subtle py-2.5">
      <h3 className="text-[13px] text-popup-fg">{copy.account.title}</h3>
      {loading ? (
        <p role="status" className="text-xs text-popup-muted">
          {copy.account.checkingSession}
        </p>
      ) : user ? (
        <div className="flex items-center justify-between gap-2">
          <span className="min-w-0 flex-1 truncate text-xs text-popup-muted" title={user.email}>
            {copy.account.signedInAs(user.email)}
          </span>
          <button type="button" className={BUTTON} disabled={busy} onClick={() => void logout()}>
            {busy ? copy.account.signingOut : copy.account.signOut}
          </button>
        </div>
      ) : (
        <form className="flex flex-col gap-2" onSubmit={(event) => void submit(event)}>
          <label htmlFor="account-email" className="sr-only">
            {copy.account.email}
          </label>
          <input
            id="account-email"
            className={INPUT}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={copy.account.email}
            disabled={busy}
          />
          <label htmlFor="account-password" className="sr-only">
            {copy.account.password}
          </label>
          <input
            id="account-password"
            className={INPUT}
            type="password"
            autoComplete="current-password"
            minLength={12}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={copy.account.password}
            disabled={busy}
          />
          <div className="flex justify-end">
            <button type="submit" className={PRIMARY_BUTTON} disabled={busy}>
              {busy ? copy.account.signingIn : copy.account.signIn}
            </button>
          </div>
        </form>
      )}
      {error && (
        <p role="alert" className="text-xs text-popup-danger">
          {error}
        </p>
      )}
    </section>
  );
}
