import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";
import { api } from "../api/client";

const TOKEN_KEY = "deviationtrace_token";
const ORG_ID_KEY = "deviationtrace_org_id";

interface AuthResponse {
  access_token: string;
  token_type: string;
  org_id: string;
}

interface AuthContextValue {
  token: string | null;
  orgId: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (orgName: string, industry: string, email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [orgId, setOrgId] = useState<string | null>(() => localStorage.getItem(ORG_ID_KEY));

  const applyAuth = (auth: AuthResponse) => {
    localStorage.setItem(TOKEN_KEY, auth.access_token);
    localStorage.setItem(ORG_ID_KEY, auth.org_id);
    setToken(auth.access_token);
    setOrgId(auth.org_id);
  };

  const login = async (email: string, password: string) => {
    const auth = await api.post<AuthResponse>("/auth/login", { email, password });
    applyAuth(auth);
  };

  const register = async (orgName: string, industry: string, email: string, password: string, fullName?: string) => {
    const auth = await api.post<AuthResponse>("/auth/register", {
      org_name: orgName,
      industry,
      email,
      password,
      full_name: fullName || null,
    });
    applyAuth(auth);
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ORG_ID_KEY);
    setToken(null);
    setOrgId(null);
  };

  const value = useMemo(
    () => ({ token, orgId, isAuthenticated: token !== null, login, register, logout }),
    [token, orgId],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
