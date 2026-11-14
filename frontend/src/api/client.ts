const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI error bodies are JSON ({"detail": "..."} or a list of
 * validation errors); turn them into one readable sentence. */
function errorMessage(body: string): string {
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed.detail === "string") return parsed.detail;
    if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) {
      const first = parsed.detail[0];
      const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1]).replace(/_/g, " ") : "";
      return field && field !== "body" ? `${field}: ${first.msg}` : first.msg;
    }
  } catch {
    // not JSON
  }
  return body;
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("deviationtrace_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...authHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, errorMessage(body) || response.statusText);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  upload: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  downloadBlob: async (path: string): Promise<Blob> => {
    const response = await fetch(`${API_BASE_URL}${path}`, { headers: authHeaders() });
    if (!response.ok) {
      const body = await response.text();
      throw new ApiError(response.status, body || response.statusText);
    }
    return response.blob();
  },
};
