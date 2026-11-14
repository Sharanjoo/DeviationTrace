import { createContext, useCallback, useContext, useEffect, useState, type PropsWithChildren } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";

export interface OnboardingStatus {
  completed: boolean;
  onboarded_at: string | null;
  org_name: string;
  industry: string;
  scope_category: string | null;
  scope_label: string | null;
}

interface OnboardingContextValue {
  /** null while loading (or when logged out). */
  status: OnboardingStatus | null;
  refresh: () => Promise<OnboardingStatus>;
  /** Record that onboarding just finished. The route gate then leaves
   * /onboarding by itself, and the Checklist page shows a one-time welcome. */
  complete: (status: OnboardingStatus, itemsAdded: number) => void;
  /** Non-null only right after finishing onboarding in this session. */
  justCompleted: { itemsAdded: number } | null;
  clearJustCompleted: () => void;
}

const OnboardingContext = createContext<OnboardingContextValue | null>(null);

/** The org's onboarding status, loaded from the server whenever the
 * logged-in org changes. Stored server-side so it's remembered for every
 * user and device of the org, not just this browser. */
export function OnboardingProvider({ children }: PropsWithChildren) {
  const { token, logout } = useAuth();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [justCompleted, setJustCompleted] = useState<{ itemsAdded: number } | null>(null);

  const complete = useCallback((next: OnboardingStatus, itemsAdded: number) => {
    setJustCompleted({ itemsAdded });
    setStatus(next);
  }, []);
  const clearJustCompleted = useCallback(() => setJustCompleted(null), []);

  const refresh = useCallback(async () => {
    const next = await api.get<OnboardingStatus>("/onboarding/status");
    setStatus(next);
    return next;
  }, []);

  useEffect(() => {
    setStatus(null);
    setJustCompleted(null);
    if (!token) return;
    // An expired or invalid token can't load status; send the user back
    // to log in rather than leaving the app stuck on a loading screen.
    refresh().catch(() => logout());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <OnboardingContext.Provider value={{ status, refresh, complete, justCompleted, clearJustCompleted }}>{children}</OnboardingContext.Provider>
  );
}

export function useOnboarding(): OnboardingContextValue {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error("useOnboarding must be used within an OnboardingProvider");
  }
  return context;
}
