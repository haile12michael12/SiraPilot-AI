import { Link } from "react-router-dom";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";

export function LoginPage() {
  return (
    <AuthPageShell title="Welcome back" description="Sign in to your account.">
      <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
        <label className="block space-y-1.5 text-sm font-medium">
          Email
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" required />
        </label>
        <label className="block space-y-1.5 text-sm font-medium">
          Password
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="current-password" required />
        </label>
        <div className="text-right text-sm">
          <Link className="text-primary hover:underline" to="/forgot-password">Forgot password?</Link>
        </div>
        <button className="h-10 w-full rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" type="submit">Sign in</button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        New to SiraPilot? <Link className="font-medium text-primary hover:underline" to="/register">Create an account</Link>
      </p>
    </AuthPageShell>
  );
}