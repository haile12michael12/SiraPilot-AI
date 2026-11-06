import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";
import { authApi } from "@/features/auth/services/auth-api";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [message, setMessage] = useState("Verifying your email…");
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    if (!token) {
      setMessage("This verification link is invalid or expired.");
      setError(true);
      return;
    }
    void authApi.verifyEmail(token).then(
      (result) => {
        if (active) setMessage(result.message);
      },
    ).catch(() => {
      if (active) {
        setMessage("This verification link is invalid or expired.");
        setError(true);
      }
    });
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <AuthPageShell title="Email verification" description="Confirm your address to finish setting up your account.">
      <p className={`text-sm ${error ? "text-destructive" : "text-muted-foreground"}`} role="status">{message}</p>
      <Link className="mt-6 inline-block text-sm font-medium text-primary hover:underline" to="/login">Continue to sign in</Link>
    </AuthPageShell>
  );
}