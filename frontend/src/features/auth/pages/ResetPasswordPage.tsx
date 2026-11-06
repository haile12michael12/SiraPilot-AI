import { Link } from "react-router-dom";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";

export function ResetPasswordPage() {
  return (
    <AuthPageShell title="Choose a new password" description="Use at least eight characters for your new password.">
      <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
        <label className="block space-y-1.5 text-sm font-medium">
          New password
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <label className="block space-y-1.5 text-sm font-medium">
          Confirm password
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <button className="h-10 w-full rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" type="submit">Update password</button>
      </form>
      <Link className="mt-6 inline-block text-sm font-medium text-primary hover:underline" to="/login">Back to sign in</Link>
    </AuthPageShell>
  );
}