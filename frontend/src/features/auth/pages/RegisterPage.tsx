import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/shared/ui/button";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";
import { useAuth } from "@/features/auth/components/AuthProvider";

const schema = z.object({
  email: z.string().email("Enter a valid email address"),
  password: z.string().min(8, "Use at least eight characters").max(128),
});
type Values = z.infer<typeof schema>;

export function RegisterPage() {
  const { register: createAccount } = useAuth();
  const [message, setMessage] = useState("");
  const [serverError, setServerError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setMessage("");
    setServerError("");
    try {
      setMessage(await createAccount(values.email, values.password));
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to register");
    }
  }

  return (
    <AuthPageShell title="Create your account" description="Start building a clearer picture of your next career move.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="register-email">
          Email
          <input id="register-email" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "register-email-error" : undefined} {...register("email")} />
          {errors.email && <span id="register-email-error" className="text-xs font-normal text-destructive">{errors.email.message}</span>}
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="register-password">
          Password
          <input id="register-password" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "register-password-error" : undefined} {...register("password")} />
          {errors.password && <span id="register-password-error" className="text-xs font-normal text-destructive">{errors.password.message}</span>}
        </label>
        {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
        {message && <p className="text-sm text-emerald-700" role="status">{message}</p>}
        <Button className="w-full" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-muted-foreground">
        Already have an account? <Link className="font-medium text-primary hover:underline" to="/login">Sign in</Link>
      </p>
    </AuthPageShell>
  );
}