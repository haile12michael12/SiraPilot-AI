import { Link } from "react-router-dom";

export function OnboardingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-5 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Getting started</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Let’s start with your career story.</h1>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        Build a profile with your experience, skills, and goals. You can update it whenever your plans change.
      </p>
      <Link className="mt-7 inline-flex h-10 w-fit items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground" to="/career-profile">
        Set up your profile
      </Link>
    </main>
  );
}