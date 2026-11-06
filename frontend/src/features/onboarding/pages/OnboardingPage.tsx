import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ApiError, apiRequest } from "@/features/auth/services/auth-api";

type Entry = {
  id: string;
  name?: string;
  title?: string;
  company?: string;
  institution?: string;
  field_of_study?: string | null;
  proficiency_level?: string;
  kind?: string;
  value?: string;
};

type OnboardingData = {
  profile: {
    first_name: string | null;
    last_name: string | null;
    headline: string | null;
    summary: string | null;
    city: string | null;
    country: string | null;
    current_status: string | null;
    onboarding_step: number;
  };
  skills: Entry[];
  experiences: Entry[];
  education: Entry[];
  preference_options: Entry[];
};

const steps = [
  "Welcome",
  "Personal information",
  "Current situation",
  "Work experience",
  "Education",
  "Skills",
  "Career goals",
  "What you’re looking for",
  "Review and finish",
];

function parseList(value: string) {
  return [...new Set(value.split(",").map((item) => item.trim()).filter(Boolean))];
}

export function OnboardingPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<OnboardingData | null>(null);
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState({
    firstName: "",
    lastName: "",
    headline: "",
    summary: "",
    city: "",
    country: "",
    currentStatus: "",
    role: "",
    company: "",
    institution: "",
    degree: "",
    skills: "",
    careerGoal: "",
    jobTitles: "",
    industries: "",
    locations: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void apiRequest<OnboardingData>("/career-profile")
      .then((result) => {
        if (!active) return;
        setData(result);
        setStep(Math.min(result.profile.onboarding_step, 8));
        setDraft((current) => ({
          ...current,
          firstName: result.profile.first_name ?? "",
          lastName: result.profile.last_name ?? "",
          headline: result.profile.headline ?? "",
          summary: result.profile.summary ?? "",
          city: result.profile.city ?? "",
          country: result.profile.country ?? "",
          currentStatus: result.profile.current_status ?? "",
          role: result.experiences[0]?.title ?? "",
          company: result.experiences[0]?.company ?? "",
          institution: result.education[0]?.institution ?? "",
          degree: result.education[0]?.field_of_study ?? result.education[0]?.title ?? "",
          skills: result.skills.map((skill) => skill.name).filter(Boolean).join(", "),
          jobTitles: result.preference_options.filter((item) => item.kind === "job_title").map((item) => item.value).join(", "),
          industries: result.preference_options.filter((item) => item.kind === "industry").map((item) => item.value).join(", "),
          locations: result.preference_options.filter((item) => item.kind === "location").map((item) => item.value).join(", "),
        }));
      })
      .catch(() => setError("Your profile could not be loaded. Please try again."))
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function setValue(field: keyof typeof draft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  async function saveStep() {
    if (step === 1) {
      await apiRequest("/career-profile", {
        method: "PATCH",
        body: JSON.stringify({
          first_name: draft.firstName,
          last_name: draft.lastName,
          headline: draft.headline,
          summary: draft.summary,
          city: draft.city,
          country: draft.country,
        }),
      });
    } else if (step === 2) {
      await apiRequest("/career-profile", {
        method: "PATCH",
        body: JSON.stringify({ current_status: draft.currentStatus }),
      });
    } else if (step === 3 && (draft.role.trim() || draft.company.trim())) {
      const current = data?.experiences[0];
      const body = JSON.stringify({ title: draft.role, company: draft.company });
      if (current) {
        await apiRequest(`/career-profile/entries/experience/${current.id}`, { method: "PATCH", body });
      } else {
        const created = await apiRequest<Entry>("/career-profile/entries/experience", { method: "POST", body });
        setData((value) => value ? { ...value, experiences: [created, ...value.experiences] } : value);
      }
    } else if (step === 4 && (draft.institution.trim() || draft.degree.trim())) {
      const current = data?.education[0];
      const body = JSON.stringify({ institution: draft.institution, field_of_study: draft.degree });
      if (current) {
        await apiRequest(`/career-profile/entries/education/${current.id}`, { method: "PATCH", body });
      } else {
        const created = await apiRequest<Entry>("/career-profile/entries/education", { method: "POST", body });
        setData((value) => value ? { ...value, education: [created, ...value.education] } : value);
      }
    } else if (step === 5) {
      const desired = parseList(draft.skills);
      const existing = data?.skills ?? [];
      for (const skill of existing) {
        if (skill.name && !desired.some((name) => name.toLowerCase() === skill.name?.toLowerCase())) {
          await apiRequest(`/career-profile/entries/skills/${skill.id}`, { method: "DELETE" });
        }
      }
      for (const name of desired) {
        if (!existing.some((skill) => skill.name?.toLowerCase() === name.toLowerCase())) {
          await apiRequest("/career-profile/entries/skills", {
            method: "POST",
            body: JSON.stringify({ name, proficiency_level: "intermediate" }),
          });
        }
      }
    } else if (step === 6) {
      await apiRequest("/career-profile/preferences", {
        method: "PATCH",
        body: JSON.stringify({ career_goal: draft.careerGoal }),
      });
    } else if (step === 7) {
      const options = [
        ...parseList(draft.jobTitles).map((value) => ({ kind: "job_title", value })),
        ...parseList(draft.industries).map((value) => ({ kind: "industry", value })),
        ...parseList(draft.locations).map((value) => ({ kind: "location", value })),
      ];
      await apiRequest("/career-profile/preference-options", {
        method: "PUT",
        body: JSON.stringify({ items: options }),
      });
    }
    if (step < 8) {
      await apiRequest("/career-profile", {
        method: "PATCH",
        body: JSON.stringify({ onboarding_step: step + 1 }),
      });
    }
  }

  async function next() {
    if (step === 8) {
      setIsSaving(true);
      setError("");
      try {
        await apiRequest("/career-profile/onboarding/complete", { method: "POST" });
        navigate("/career-profile", { replace: true });
      } catch {
        setError("Your profile could not be saved. Please try again.");
      } finally {
        setIsSaving(false);
      }
      return;
    }
    setIsSaving(true);
    setError("");
    try {
      await saveStep();
      setStep((current) => Math.min(current + 1, 8));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Your progress could not be saved. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  function textField(field: keyof typeof draft, label: string, type = "text") {
    return (
      <label className="block space-y-1.5 text-sm font-medium">
        {label}
        <input className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" type={type} value={draft[field]} onChange={(event) => setValue(field, event.target.value)} />
      </label>
    );
  }

  if (isLoading) {
    return <main className="flex min-h-screen items-center justify-center text-sm text-muted-foreground" role="status">Loading your profile…</main>;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-5 py-10 sm:px-8">
      <header className="flex items-center justify-between gap-4">
        <Link to="/" className="text-sm font-semibold text-primary">SiraPilot</Link>
        <span className="text-xs text-muted-foreground">Step {step + 1} of {steps.length}</span>
      </header>
      <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-muted" aria-label="Onboarding progress">
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${((step + 1) / steps.length) * 100}%` }} />
      </div>
      <section className="my-auto py-10">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{steps[step]}</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight">
          {step === 0 ? "Let’s start with your career story." : steps[step]}
        </h1>
        <div className="mt-7 max-w-xl space-y-4">
          {step === 0 && <p className="text-sm leading-relaxed text-muted-foreground">Build your profile one step at a time. Your progress is saved as you go, and you can return to make changes later.</p>}
          {step === 1 && <div className="grid gap-4 sm:grid-cols-2">{textField("firstName", "First name")}{textField("lastName", "Last name")}{textField("headline", "Professional headline")}{textField("city", "City")}{textField("country", "Country")}<label className="block space-y-1.5 text-sm font-medium sm:col-span-2">About<textarea className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 font-normal" value={draft.summary} onChange={(event) => setValue("summary", event.target.value)} /></label></div>}
          {step === 2 && <label className="block space-y-1.5 text-sm font-medium">Which best describes you right now?<select className="h-10 w-full rounded-md border border-input bg-background px-3 font-normal" value={draft.currentStatus} onChange={(event) => setValue("currentStatus", event.target.value)}><option value="">Choose a status</option><option value="employed">Employed</option><option value="seeking">Looking for work</option><option value="student">Student</option><option value="career_change">Considering a career change</option><option value="other">Other</option></select></label>}
          {step === 3 && <div className="grid gap-4 sm:grid-cols-2">{textField("role", "Most recent job title")}{textField("company", "Company")}</div>}
          {step === 4 && <div className="grid gap-4 sm:grid-cols-2">{textField("institution", "School or institution")}{textField("degree", "Degree or field of study")}</div>}
          {step === 5 && <label className="block space-y-1.5 text-sm font-medium">Skills, separated by commas<textarea className="min-h-28 w-full rounded-md border border-input bg-background px-3 py-2 font-normal" value={draft.skills} onChange={(event) => setValue("skills", event.target.value)} /></label>}
          {step === 6 && <label className="block space-y-1.5 text-sm font-medium">What would you like to work toward?<textarea className="min-h-32 w-full rounded-md border border-input bg-background px-3 py-2 font-normal" value={draft.careerGoal} onChange={(event) => setValue("careerGoal", event.target.value)} /></label>}
          {step === 7 && <div className="space-y-4">{textField("jobTitles", "Preferred job titles, separated by commas")}{textField("industries", "Industries, separated by commas")}{textField("locations", "Preferred locations, separated by commas")}</div>}
          {step === 8 && <div className="space-y-3 text-sm text-muted-foreground"><p>{draft.firstName || "Your name"} {draft.lastName} · {draft.headline || "No headline yet"}</p><p>{data?.experiences.length ?? 0} experience entries · {data?.education.length ?? 0} education entries · {parseList(draft.skills).length} skills</p><p>{draft.careerGoal || "No career goal added yet"}</p><p>You can keep editing these details from your career profile.</p></div>}
        </div>
        {error && <p className="mt-5 text-sm text-destructive" role="alert">{error}</p>}
        <div className="mt-8 flex flex-wrap items-center gap-3">
          {step > 0 && <Button variant="outline" onClick={() => setStep((current) => current - 1)} disabled={isSaving}>Back</Button>}
          <Button onClick={() => void next()} disabled={isSaving}>
            {isSaving ? "Saving…" : step === 8 ? "Finish setup" : step === 0 ? "Get started" : "Save and continue"}
          </Button>
          <Link className="ml-auto text-sm text-muted-foreground hover:text-foreground" to="/career-profile">Exit onboarding</Link>
        </div>
      </section>
    </main>
  );
}