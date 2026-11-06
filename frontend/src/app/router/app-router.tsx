import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/app/layouts/app-layout";
import { DashboardPage } from "@/features/dashboard/dashboard-page";
import { PlaceholderPage } from "@/features/shared/placeholder-page";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { ForgotPasswordPage } from "@/features/auth/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "@/features/auth/pages/ResetPasswordPage";
import { OnboardingPage } from "@/features/onboarding/pages/OnboardingPage";
import { CareerProfilePage } from "@/features/career-profile/pages/CareerProfilePage";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="career-profile" element={<CareerProfilePage />} />
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
