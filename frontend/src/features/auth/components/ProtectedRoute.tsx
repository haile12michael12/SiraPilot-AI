import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/features/auth/components/AuthProvider";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center" role="status">
        <span className="text-sm text-muted-foreground">Checking your session…</span>
      </main>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
}