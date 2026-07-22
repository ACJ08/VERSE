/**
 * VERSE API Client
 * Typed fetch wrapper around the FastAPI backend.
 * All components import from here — never fetch() directly from pages.
 *
 * Base URL is set via VITE_API_URL in .env.local
 * Falls back to "" (same-origin) so the app still works without a backend.
 */

const BASE = (import.meta.env.VITE_API_URL as string) ?? "";

// ─── Token storage ─────────────────────────────────────────────────────────────

export const TokenStore = {
  get: (): string | null => localStorage.getItem("verse_token"),
  set: (t: string): void => { localStorage.setItem("verse_token", t); },
  clear: (): void => { localStorage.removeItem("verse_token"); localStorage.removeItem("verse_user"); },
};

export const UserStore = {
  get: (): VERSEUser | null => {
    try { return JSON.parse(localStorage.getItem("verse_user") ?? "null"); } catch { return null; }
  },
  set: (u: VERSEUser): void => { localStorage.setItem("verse_user", JSON.stringify(u)); },
};

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface VERSEUser {
  id: string;
  email: string;
  name: string;
  role: string;
  verified: number;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: VERSEUser;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  workspace_name: string;
  production_type: string;
  status: string;
  description: string;
  start_date: string;
  end_date: string;
  team_size: number;
  created_at: string;
  scenes_total: number;
  facts_count: number;
  entities_count: number;
}

export interface TeamMember {
  id: number;
  project_id: string;
  user_id: string | null;
  email: string;
  role: string;
  status: string;
  joined_at: string;
}

export interface ContinuityIssue {
  issue_id: string;
  category: string;
  type: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence: number;
  entity: { type: string; name: string; key: string };
  attribute: string;
  scene_id: string | null;
  expected: { value: unknown; source: string | null; source_reference: string; confidence: number };
  observed: { value: unknown; source: string | null; source_reference: string; confidence: number };
  explanation: string;
  suggested_fix: string;
  status: "pending_review" | "confirmed" | "dismissed" | "resolved";
  occurrences: number;
  related_scene_ids: string[];
  mitigated_by: string[];
  score_impact: number;
}

export interface ContinuityReport {
  project_id: string;
  scene_id: string | null;
  overall_score: number;
  category_scores: Record<string, number>;
  issues: ContinuityIssue[];
  score_summary: { main_reason: string; penalties_applied: number; issues_mitigated: number };
  generated_at: string;
  engine_version: string;
}

export interface UploadResult {
  project_id: string;
  filename: string;
  scenes_detected: number;
  facts_ingested: number;
  graph_stats: Record<string, number>;
}

// ─── Core fetch ────────────────────────────────────────────────────────────────

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { params, ...init } = opts;
  let url = `${BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(params).toString();
    if (qs) url += `?${qs}`;
  }

  const token = TokenStore.get();
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, { ...init, headers });

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      msg = body?.detail ?? body?.message ?? msg;
    } catch { /* ignore */ }
    throw new APIError(res.status, msg);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  register: (data: { email: string; password: string; name: string; organization?: string }) =>
    apiFetch<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (email: string, password: string) =>
    apiFetch<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  /** Request a 6-digit OTP be sent to the current user's email. */
  requestEmailVerification: () =>
    apiFetch<{ message: string; dev_token?: string }>("/auth/verify-email/request", { method: "POST" }),

  /** Submit the OTP received by email to mark the account as verified. */
  verifyEmail: (token: string) =>
    apiFetch<{ verified: boolean; email: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),

  /** Request a password-reset OTP. Returns dev_token when SMTP is not configured. */
  forgotPassword: (email: string) =>
    apiFetch<{ message: string; dev_token?: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  /** Submit the OTP and a new password to complete the reset. */
  resetPassword: (email: string, token: string, new_password: string) =>
    apiFetch<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ email, token, new_password }),
    }),

  me: () => apiFetch<VERSEUser>("/auth/me"),
};

// ─── Projects ─────────────────────────────────────────────────────────────────

export const projects = {
  list: () => apiFetch<Project[]>("/projects"),

  get: (id: string) => apiFetch<Project>(`/projects/${id}`),

  create: (data: {
    name: string; workspace_name?: string; production_type?: string;
    description?: string; start_date?: string; end_date?: string; team_size?: number;
  }) => apiFetch<Project>("/projects", { method: "POST", body: JSON.stringify(data) }),

  update: (id: string, data: Partial<Project>) =>
    apiFetch<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  delete: (id: string) =>
    apiFetch<void>(`/projects/${id}`, { method: "DELETE" }),

  getTeam: (id: string) => apiFetch<TeamMember[]>(`/projects/${id}/team`),

  inviteMember: (id: string, email: string, role?: string) =>
    apiFetch(`/projects/${id}/team/invite`, { method: "POST", body: JSON.stringify({ email, role }) }),
};

// ─── Continuity Engine ────────────────────────────────────────────────────────

export const continuity = {
  analyse: (project_id: string, scene_id?: string) =>
    apiFetch<ContinuityReport>("/continuity/analyse", {
      method: "POST",
      body: JSON.stringify({ project_id, scene_id }),
    }),

  issues: (project_id: string) =>
    apiFetch<ContinuityIssue[]>(`/continuity/issues/${project_id}`),

  ingestScript: (project_id: string, payload: unknown) =>
    apiFetch("/continuity/ingest/script", {
      method: "POST",
      body: JSON.stringify({ project_id, payload }),
    }),

  feedback: (project_id: string, issue_id: string, action: "confirm" | "dismiss" | "resolve" | "reopen", note?: string) =>
    apiFetch<ContinuityIssue>("/continuity/feedback", {
      method: "POST",
      body: JSON.stringify({ project_id, action: { issue_id, action, note } }),
    }),

  overrideFact: (project_id: string, entity_key: string, attribute: string, value: unknown) =>
    apiFetch("/continuity/facts/override", {
      method: "POST",
      body: JSON.stringify({ project_id, override: { entity_key, attribute, value } }),
    }),

  health: () => apiFetch<{ status: string }>("/continuity/health"),
};

// ─── Upload ───────────────────────────────────────────────────────────────────

export const upload = {
  screenplay: (project_id: string, file: File) => {
    const form = new FormData();
    form.append("project_id", project_id);
    form.append("file", file);
    return apiFetch<UploadResult>("/upload/screenplay", { method: "POST", body: form });
  },
};

// ─── Health ───────────────────────────────────────────────────────────────────

export const system = {
  health: () => apiFetch<{ status: string; version: string; watsonx_connected: boolean }>("/health"),
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Map engine severity (low/medium/high/critical) → dashboard severity (info/warning/critical) */
export function toDisplaySeverity(s: string): "info" | "warning" | "critical" {
  if (s === "critical" || s === "high") return s === "critical" ? "critical" : "warning";
  if (s === "medium") return "warning";
  return "info";
}

/** Convert engine category_scores dict → Recharts-ready radar array */
export function categoryScoresToRadar(scores: Record<string, number>) {
  return Object.entries(scores).map(([subject, score]) => ({
    subject: subject.charAt(0).toUpperCase() + subject.slice(1),
    score: Math.round(score),
    fullMark: 100,
  }));
}
