import { Link } from "react-router-dom";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";

export function RegisterPage() {
  return (
    <AuthPageShell title="Create your account" description="Start building a clearer picture of your next career move.">
      <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
        <label className="block space-y-1.5 text-sm font-medium">
          Name
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="text" autoComplete="name" required />
        </label>
        <label className="block space-y-1.5 text-sm font-medium">
          Email
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" required />
        </label>
        <label className="block space-y-1.5 text-sm font-medium">
          Password
          <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <button className="h-10 w-full rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" type="submit">Create account</button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        Already have an account? <Link className="font-medium text-primary hover:underline" to="/login">Sign in</Link>
      </p>
    </AuthPageShell>
  );
}