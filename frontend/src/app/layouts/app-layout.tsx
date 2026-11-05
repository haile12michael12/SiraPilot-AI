import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  BriefcaseBusiness,
  CalendarDays,
  LayoutDashboard,
  Menu,
  Moon,
  Sparkles,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";

const navigation = [
  { label: "Overview", to: "/", icon: LayoutDashboard, end: true },
  { label: "Career profile", to: "/career-profile", icon: UserRound },
  { label: "Job discovery", to: "/job-discovery", icon: BriefcaseBusiness },
  { label: "Applications", to: "/applications", icon: Sparkles },
  { label: "Calendar", to: "/calendar", icon: CalendarDays },
];

const pageTitles: Record<string, string> = {
  "/": "Overview",
  "/career-profile": "Career profile",
  "/job-discovery": "Job discovery",
  "/applications": "Applications",
  "/calendar": "Calendar",
};

function Sidebar({
  onNavigate,
}: {
  onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col px-4 py-5">
      <NavLink
        to="/"
        className="mb-9 flex items-center gap-3 px-2"
        onClick={onNavigate}
        aria-label="SiraPilot home"
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <Sparkles size={20} aria-hidden="true" />
        </span>
        <span>
          <span className="block text-[15px] font-bold tracking-tight">
            SiraPilot
          </span>
          <span className="block text-xs text-muted-foreground">
            Career workspace
          </span>
        </span>
      </NavLink>

      <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-muted-foreground">
        Workspace
      </p>
      <nav aria-label="Main navigation" className="space-y-1">
        {navigation.map(({ label, to, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )
            }
          >
            <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-2xl border border-border bg-card p-4">
        <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-primary">
          <Sparkles size={16} aria-hidden="true" />
        </div>
        <p className="text-sm font-semibold">Built around your next step</p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          Your career workspace starts with a clear picture of where you want
          to go.
        </p>
      </div>
      <p className="px-2 pt-4 text-[11px] text-muted-foreground">
        Phase 0 · Foundation
      </p>
    </div>
  );
}

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const theme = useUiStore((state) => state.theme);
  const toggleTheme = useUiStore((state) => state.toggleTheme);
  const pageTitle = pageTitles[location.pathname] ?? "Workspace";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] border-r border-border bg-sidebar lg:block">
        <Sidebar />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            className="absolute inset-0 h-full w-full bg-black/40"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          />
          <aside className="relative h-full w-[280px] border-r border-border bg-sidebar shadow-xl">
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-3 top-3"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X size={18} />
            </Button>
            <Sidebar onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-[248px]">
        <header className="sticky top-0 z-20 flex h-[68px] items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur-md sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={19} />
            </Button>
            <span className="text-sm font-semibold">{pageTitle}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden text-xs text-muted-foreground sm:block">
              Your next chapter, thoughtfully planned.
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
              title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              {theme === "light" ? (
                <Moon size={18} aria-hidden="true" />
              ) : (
                <Sun size={18} aria-hidden="true" />
              )}
            </Button>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1440px] px-4 py-8 sm:px-7 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
