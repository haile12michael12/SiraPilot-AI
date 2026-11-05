import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  CircleCheck,
  CircleDashed,
  FileText,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { fetchHealth } from "@/lib/api";

const summary = [
  {
    label: "Applications",
    detail: "Your opportunities in one place",
    icon: BriefcaseBusiness,
    href: "/applications",
  },
  {
    label: "Career profile",
    detail: "A foundation tailored to you",
    icon: FileText,
    href: "/career-profile",
  },
  {
    label: "Upcoming",
    detail: "Your plans and important dates",
    icon: CalendarDays,
    href: "/calendar",
  },
];

function ConnectionStatus() {
  const health = useQuery({
    queryKey: ["api-health"],
    queryFn: ({ signal }) => fetchHealth(signal),
    refetchInterval: 30_000,
  });

  const isReady = health.data?.status === "ok";
  const message = health.isPending
    ? "Checking service"
    : isReady
      ? "All systems ready"
      : "Service unavailable";

  return (
    <div
      className="flex items-center gap-2 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
    >
      {health.isPending ? (
        <RefreshCw size={14} className="animate-spin" aria-hidden="true" />
      ) : isReady ? (
        <CircleCheck size={14} className="text-emerald-600" aria-hidden="true" />
      ) : (
        <Activity size={14} className="text-amber-600" aria-hidden="true" />
      )}
      <span>{message}</span>
      {health.isError && (
        <button
          type="button"
          className="font-semibold text-primary hover:underline"
          onClick={() => void health.refetch()}
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function DashboardPage() {
  const today = new Intl.DateTimeFormat("en", {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date());

  return (
    <div className="space-y-8">
      <section className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            {today}
          </p>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-[38px]">
            Make room for what&apos;s next.
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
            A calmer place to understand your strengths, explore opportunities,
            and move your career forward.
          </p>
        </div>
        <ConnectionStatus />
      </section>

      <section
        aria-label="Workspace sections"
        className="grid gap-4 md:grid-cols-3"
      >
        {summary.map(({ label, detail, icon: Icon, href }) => (
          <Link
            key={label}
            to={href}
            className="group rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Card className="h-full transition-all group-hover:-translate-y-0.5 group-hover:border-primary/30">
              <CardContent className="flex items-start justify-between gap-4 p-5 sm:p-6">
                <div>
                  <p className="text-sm font-semibold">{label}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    {detail}
                  </p>
                </div>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-primary">
                  <Icon size={19} strokeWidth={1.8} aria-hidden="true" />
                </span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.55fr_1fr]">
        <Card className="overflow-hidden">
          <CardContent className="p-6 sm:p-8">
            <div className="flex items-start gap-4">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Sparkles size={20} aria-hidden="true" />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                  A good place to begin
                </p>
                <h2 className="mt-2 text-xl font-semibold tracking-tight">
                  Start with your career story
                </h2>
                <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                  Your experience, strengths, and goals make every next step
                  more personal. Build that foundation at your own pace.
                </p>
                <Button asChild className="mt-5">
                  <Link to="/career-profile">
                    Explore your profile <ArrowRight size={16} />
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 sm:p-7">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold">Your starting points</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Choose what feels useful today.
                </p>
              </div>
              <CircleDashed
                size={18}
                className="text-muted-foreground"
                aria-hidden="true"
              />
            </div>
            <div className="space-y-1">
              {[
                { label: "Reflect on your strengths", to: "/career-profile" },
                { label: "Explore new opportunities", to: "/job-discovery" },
                { label: "Keep track of your next steps", to: "/applications" },
              ].map(({ label, to }, index) => (
                <Link
                  key={label}
                  to={to}
                  className="flex items-center gap-3 rounded-xl px-2 py-3 text-sm transition-colors hover:bg-accent"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-[11px] font-medium text-muted-foreground">
                    {index + 1}
                  </span>
                  <span className="flex-1">{label}</span>
                  <ArrowRight
                    size={15}
                    className="text-muted-foreground"
                    aria-hidden="true"
                  />
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="rounded-2xl border border-dashed border-border bg-card/60 px-6 py-5 sm:flex sm:items-center sm:justify-between sm:px-7">
        <div>
          <p className="text-sm font-semibold">A workspace that grows with you</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Career insights and planning tools will take shape here as your
            journey unfolds.
          </p>
        </div>
        <Link
          to="/job-discovery"
          className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-primary hover:underline sm:mt-0"
        >
          See what&apos;s ahead <ArrowRight size={14} />
        </Link>
      </section>
    </div>
  );
}
