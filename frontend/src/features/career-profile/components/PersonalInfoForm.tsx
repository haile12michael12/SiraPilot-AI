import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/shared/ui/button";
import { apiRequest } from "@/features/auth/services/auth-api";

const schema = z.object({
  first_name: z.string().max(100),
  last_name: z.string().max(100),
  headline: z.string().max(200),
  summary: z.string().max(10_000),
  phone: z.string().max(40),
  city: z.string().max(120),
  region: z.string().max(120),
  country: z.string().max(120),
});

type Values = z.infer<typeof schema>;
const emptyValues: Values = {
  first_name: "",
  last_name: "",
  headline: "",
  summary: "",
  phone: "",
  city: "",
  region: "",
  country: "",
};

export function PersonalInfoForm() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: emptyValues });

  useEffect(() => {
    let active = true;
    void apiRequest<Partial<Values>>("/career-profile")
      .then((profile) => {
        if (active) reset({ ...emptyValues, ...profile });
      })
      .catch(() => {
        if (active) setError("Personal information could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, [reset]);

  async function onSubmit(values: Values) {
    setError("");
    setMessage("");
    try {
      await apiRequest("/career-profile", {
        method: "PATCH",
        body: JSON.stringify(values),
      });
      setMessage("Personal information saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Personal information could not be saved.");
    }
  }

  return (
    <section className="space-y-4 border-b border-border pb-7">
      <div>
        <h2 className="text-lg font-semibold">Personal information</h2>
        <p className="mt-1 text-sm text-muted-foreground">The basics that help shape your career profile.</p>
      </div>
      <form className="grid gap-4 sm:grid-cols-2" noValidate onSubmit={handleSubmit(onSubmit)}>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-first-name">
          First name
          <input id="profile-first-name" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" autoComplete="given-name" {...register("first_name")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-last-name">
          Last name
          <input id="profile-last-name" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" autoComplete="family-name" {...register("last_name")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium sm:col-span-2" htmlFor="profile-headline">
          Professional headline
          <input id="profile-headline" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" {...register("headline")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-phone">
          Phone
          <input id="profile-phone" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type="tel" autoComplete="tel" {...register("phone")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-city">
          City
          <input id="profile-city" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" autoComplete="address-level2" {...register("city")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-region">
          Region
          <input id="profile-region" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" autoComplete="address-level1" {...register("region")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium" htmlFor="profile-country">
          Country
          <input id="profile-country" className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" autoComplete="country-name" {...register("country")} />
        </label>
        <label className="block space-y-1.5 text-sm font-medium sm:col-span-2" htmlFor="profile-summary">
          About
          <textarea id="profile-summary" className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 font-normal" rows={4} {...register("summary")} />
        </label>
        {error && <p className="text-sm text-destructive sm:col-span-2" role="alert">{error}</p>}
        {message && <p className="text-sm text-emerald-700 sm:col-span-2" role="status">{message}</p>}
        <div><Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving…" : "Save personal information"}</Button></div>
      </form>
    </section>
  );
}