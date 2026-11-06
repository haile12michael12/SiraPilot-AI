import { Link } from "react-router-dom";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";

export function ForgotPasswordPage() {
  return (
    <AuthPageShell title="Reset your password" description="Enter your email and we’ll send instructions to reset your password.">
      <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
        <label className="block space-y-1.5 text-sm font-medium">
          Email
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" required />
        </label>
        <button className="h-10 w-full rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" type="submit">Send reset instructions</button>
      </form>
      <Link className="mt-6 inline-block text-sm font-medium text-primary hover:underline" to="/login">Back to sign in</Link>
    </AuthPageShell>
  );
}