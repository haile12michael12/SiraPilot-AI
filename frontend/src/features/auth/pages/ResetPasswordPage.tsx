import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";
import { Button } from "@/shared/ui/button";
import { AuthPageShell } from "@/features/auth/components/AuthPageShell";
import { authApi } from "@/features/auth/services/auth-api";

const schema = z
  .object({
    password: z.string().min(8, "Use at least eight characters").max(128),
    confirmPassword: z.string().min(8, "Confirm your new password").max(128),
  })
  .refine((value) => value.password === value.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });
type Values = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [message, setMessage] = useState("");
  const [serverError, setServerError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setServerError("");
    if (!token) {
      setServerError("This reset link is invalid or expired.");
      return;
    }
    try {
      setMessage((await authApi.resetPassword(token, values.password)).message);
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to reset password");
    }
  }

  return (
    <AuthPageShell title="Choose a new password" description="Use at least eight characters for your new password.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="reset-password">
          New password
          <input id="reset-password" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "reset-password-error" : undefined} {...register("password")} />
          {errors.password && <span id="reset-password-error" className="text-xs font-normal text-destructive">{errors.password.message}</span>}
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="reset-confirm-password">
          Confirm password
          <input id="reset-confirm-password" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.confirmPassword)} aria-describedby={errors.confirmPassword ? "reset-confirm-password-error" : undefined} {...register("confirmPassword")} />
          {errors.confirmPassword && <span id="reset-confirm-password-error" className="text-xs font-normal text-destructive">{errors.confirmPassword.message}</span>}
        </label>
        {serverError && <p className="text-sm text-destructive" role="alert">{serverError}</p>}
        {message && <p className="text-sm text-muted-foreground" role="status">{message}</p>}
        <Button className="w-full" type="submit" disabled={isSubmitting}>Update password</Button>
      </form>
      <Link className="mt-6 inline-block text-sm font-medium text-primary hover:underline" to="/login">Back to sign in</Link>
    </AuthPageShell>
  );
}