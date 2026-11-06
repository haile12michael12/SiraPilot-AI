import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export function AuthPageShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-5 py-12">
      <section className="w-full max-w-md">
        <Link to="/" className="text-sm font-semibold text-primary">
          SiraPilot
        </Link>
        <h1 className="mt-8 text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
        <div className="mt-7">{children}</div>
      </section>
    </main>
  );
}