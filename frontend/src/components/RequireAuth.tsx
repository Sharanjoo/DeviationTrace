import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useOnboarding } from "../context/OnboardingContext";

/** Requires login, then enforces onboarding order: an org that hasn't
 * onboarded yet is sent to /onboarding from every page, and an org that
 * has is never shown /onboarding again. */
export function RequireAuth({ children }: PropsWithChildren) {
  const { isAuthenticated } = useAuth();
  const { status } = useOnboarding();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (status === null) {
    return (
      <p className="py-20 text-center" style={{ color: "var(--text-muted)" }}>
        Loading your workspace...
      </p>
    );
  }

  const onOnboarding = location.pathname === "/onboarding";
  if (!status.completed && !onOnboarding) {
    return <Navigate to="/onboarding" replace />;
  }
  if (status.completed && onOnboarding) {
    return <Navigate to="/org-checklist" replace />;
  }
  return <>{children}</>;
}
