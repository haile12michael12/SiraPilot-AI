import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";
import { useAuth } from "@/features/auth/components/AuthProvider";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password").max(128),
});

type Values = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setServerError("");
    try {
      await login(values.email, values.password);
      const destination = (location.state as { from?: string } | null)?.from;
      navigate(destination ?? "/", { replace: true });
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to sign in");
    }
  }

  return (
    <AuthPageShell title="Welcome back" description="Sign in to your account.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="login-email">
          Email
          <input id="login-email" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "login-email-error" : undefined} {...register("email")} />
          {errors.email && <span id="login-email-error" className="text-xs font-normal text-destructive">{errors.email.message}</span>}
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="login-password">
          Password
          <input id="login-password" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="current-password" aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "login-password-error" : undefined} {...register("password")} />
          {errors.password && <span id="login-password-error" className="text-xs font-normal text-destructive">{errors.password.message}</span>}
        </label>
        <div className="text-right text-sm">
          <Link className="text-primary hover:underline" to="/forgot-password">Forgot password?</Link>
        </div>
        {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
        <Button className="w-full" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        New to SiraPilot? <Link className="font-medium text-primary hover:underline" to="/register">Create an account</Link>
      </p>
    </AuthPageShell>
  );
}