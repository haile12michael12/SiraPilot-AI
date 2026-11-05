import { ArrowLeft, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <section className="mx-auto flex min-h-[55vh] max-w-lg flex-col items-center justify-center text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-primary">
        <Sparkles size={24} aria-hidden="true" />
      </span>
      <p className="mt-6 text-xs font-semibold uppercase tracking-[0.14em] text-primary">
        Coming in a later phase
      </p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        This area is part of the SiraPilot roadmap. The Phase 0 foundation is
        focused on a reliable, accessible workspace before feature workflows
        are introduced.
      </p>
      <Button asChild variant="outline" className="mt-6">
        <Link to="/">
          <ArrowLeft size={16} /> Back to overview
        </Link>
      </Button>
    </section>
  );
}
