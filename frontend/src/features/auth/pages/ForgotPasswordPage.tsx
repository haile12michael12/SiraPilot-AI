import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/shared/ui/button";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";
import { authApi } from "@/features/auth/services/auth-api";

const schema = z.object({ email: z.string().email("Enter a valid email address") });
type Values = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [message, setMessage] = useState("");
  const [serverError, setServerError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setServerError("");
    try {
      setMessage((await authApi.forgotPassword(values.email)).message);
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to process request");
    }
  }

  return (
    <AuthPageShell title="Reset your password" description="Enter your email and we’ll send instructions to reset your password.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="forgot-email">
          Email
          <input id="forgot-email" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="email" autoComplete="email" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "forgot-email-error" : undefined} {...register("email")} />
          {errors.email && <span id="forgot-email-error" className="text-xs font-normal text-destructive">{errors.email.message}</span>}
        </label>
        {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
        {message && <p className="text-sm text-muted-foreground" role="status">{message}</p>}
        <Button className="w-full" type="submit" disabled={isSubmitting}>Send reset instructions</Button>
      </form>
      <Link className="mt-6 inline-block text-sm font-medium text-primary hover:underline" to="/login">Back to sign in</Link>
    </AuthPageShell>
  );
}