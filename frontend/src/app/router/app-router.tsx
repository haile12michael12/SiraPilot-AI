import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/app/layouts/app-layout";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { PlaceholderPage } from "@/features/shared/placeholder-page";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route
            path="career-profile"
            element={<PlaceholderPage title="Career profile" />}
          />
          <Route
            path="job-discovery"
            element={<PlaceholderPage title="Job discovery" />}
          />
          <Route
            path="applications"
            element={<PlaceholderPage title="Applications" />}
          />
          <Route
            path="calendar"
            element={<PlaceholderPage title="Calendar" />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
