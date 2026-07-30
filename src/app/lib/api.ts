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
  /** Which extraction path ran: script-intelligence/granite, watsonx/granite, heuristic. */
  extractor?: string;
  scene_ids?: string[];
  entities?: string[];
  /** Continuity notes the script service produced. Not engine issues — model opinions. */
  notes?: ScriptNote[];
  /** Non-fatal problems: an offline sibling service, an unusable scene, missing aliases. */
  warnings?: string[];
  duplicate?: boolean;
  report?: ContinuityReport;
}

export interface ScriptNote {
  scene_id: string;
  note: string;
  severity: string;
  category: string;
  affected_characters: string[];
}

/** Result of ingesting footage: aggregated vision observations for one scene. */
export interface FootageUploadResult extends UploadResult {
  frames_analysed: number;
  overview?: ProjectOverview;
  scenes?: SceneView[];
}

export interface ProjectOverview {
  scenes_total: number;
  scenes_shot: number;
  scenes_clean: number;
  issues_total: number;
  average_scene_score: number;
  facts: number;
  entities: number;
  categories_at_risk: string[];
}

export interface EntityRef {
  type: string;
  name: string;
  key: string;
  raw_type: string | null;
}

/** Per-scene rollup from GET /continuity/scenes/{project_id}. */
export interface SceneView {
  scene_id: string;
  sequence: number;
  location: string | null;
  time_of_day: string | null;
  slugline: string | null;
  score: number;
  category_scores: Record<string, number>;
  issue_count: number;
  issues_by_severity: Record<string, number>;
  categories: string[];
  entities: EntityRef[];
  sources: string[];
  has_footage: boolean;
  fact_count: number;
  headline: string;
}

export interface ProjectScenes {
  project_id: string;
  overview: ProjectOverview;
  scenes: SceneView[];
}

export type SlotState = "match" | "conflict" | "unverified" | "observed_only";

/** One tracked attribute of one entity in one scene, with both halves and sources. */
export interface SlotView {
  entity: EntityRef;
  attribute: string;
  scene_id: string | null;
  state: SlotState;
  expected: { value: unknown; source: string | null; source_reference: string; confidence: number } | null;
  observed: { value: unknown; source: string | null; source_reference: string; confidence: number } | null;
  issue_id: string | null;
  severity: string | null;
  human_confirmed: boolean;
  /** False on a `conflict` slot means "values differ but confidence was too low to flag". */
  flagged: boolean;
}

/** Per-entity tracking state from GET /continuity/entities/{project_id}. */
export interface EntityView {
  entity: EntityRef;
  scene_ids: string[];
  slots: SlotView[];
  attributes: string[];
  issue_count: number;
  conflict_count: number;
  fact_count: number;
  latest: Record<string, unknown>;
}

/** Result of POST /continuity/pipeline/run — ingest script + footage, then analyse. */
export interface PipelineResult {
  project_id: string;
  steps: Array<Partial<UploadResult> & { source: string; facts_ingested: number }>;
  report: ContinuityReport;
  overview: ProjectOverview;
  scenes: SceneView[];
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

  /**
   * Ingest a payload in a producing team's own shape — the script service's
   * AnalyseScriptResponse, or a vision scene document. The backend adapts it
   * before ingestion, so neither team has to reshape to the engine contract.
   *
   * `shape`: "script" | "footage" | "call_sheet" | "auto".
   */
  ingestAdapted: (
    shape: "script" | "footage" | "call_sheet" | "auto",
    project_id: string,
    payload: unknown,
    opts: { scene_id?: string; entity_aliases?: Record<string, string>; analyse?: boolean } = {},
  ) =>
    apiFetch<FootageUploadResult>(`/continuity/ingest-adapted/${shape}`, {
      method: "POST",
      body: JSON.stringify({ project_id, payload, ...opts }),
    }),

  /** Ingest script and footage together, then analyse — the full pipeline in one call. */
  runPipeline: (
    project_id: string,
    payloads: { script?: unknown; footage?: unknown; call_sheet?: unknown },
    opts: { scene_id?: string; entity_aliases?: Record<string, string> } = {},
  ) =>
    apiFetch<PipelineResult>("/continuity/pipeline/run", {
      method: "POST",
      body: JSON.stringify({ project_id, ...payloads, ...opts }),
    }),

  /** Per-scene rollup for scene tracking / timeline views. */
  scenes: (project_id: string, analyse = false) =>
    apiFetch<ProjectScenes>(`/continuity/scenes/${project_id}`, {
      params: analyse ? { analyse: "true" } : undefined,
    }),

  /**
   * Expected vs observed state per entity attribute, per scene.
   * `entity_type` and `attribute` accept comma-separated lists, e.g.
   * entities(id, { entity_type: "character", attribute: "wears" }) for costumes.
   */
  entities: (project_id: string, filters: { entity_type?: string; attribute?: string } = {}) =>
    apiFetch<EntityView[]>(`/continuity/entities/${project_id}`, {
      params: Object.fromEntries(
        Object.entries(filters).filter(([, v]) => !!v) as [string, string][],
      ),
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
  /** Screenplay → script service (or local Granite/heuristic fallback) → engine. */
  screenplay: (project_id: string, file: File, analyse = false) => {
    const form = new FormData();
    form.append("project_id", project_id);
    form.append("file", file);
    if (analyse) form.append("analyse", "true");
    return apiFetch<UploadResult>("/upload/screenplay", { method: "POST", body: form });
  },

  /**
   * Footage → engine. Accepts the vision pipeline's scene_<id>.json directly, or
   * a video clip when the backend has VISION_SERVICE_URL configured.
   *
   * `entityAliases` joins vision track ids to script names ({"PERSON_1": "Sarah"}).
   * Without it the footage cannot be compared against the screenplay.
   */
  footage: (
    project_id: string,
    file: File,
    opts: { sceneId?: string; entityAliases?: Record<string, string>; analyse?: boolean } = {},
  ) => {
    const form = new FormData();
    form.append("project_id", project_id);
    form.append("file", file);
    if (opts.sceneId) form.append("scene_id", opts.sceneId);
    if (opts.entityAliases && Object.keys(opts.entityAliases).length > 0) {
      form.append("entity_aliases", JSON.stringify(opts.entityAliases));
    }
    form.append("analyse", String(opts.analyse ?? true));
    return apiFetch<FootageUploadResult>("/upload/footage", { method: "POST", body: form });
  },

  /** Call sheet → script service parser → engine (call_sheet source trust). */
  callSheet: (project_id: string, file: File) => {
    const form = new FormData();
    form.append("project_id", project_id);
    form.append("file", file);
    return apiFetch<UploadResult>("/upload/call-sheet", { method: "POST", body: form });
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

/**
 * Map a SceneView onto the dashboard's scene status vocabulary.
 * A scene with no footage has not been shot; a shot scene is Flagged if the
 * engine raised issues, Review if something differs below the flag threshold,
 * and Logged when it is clean.
 */
export function sceneStatus(scene: SceneView): "Logged" | "Flagged" | "Review" | "Scheduled" {
  if (!scene.has_footage) return "Scheduled";
  if (scene.issue_count > 0) {
    const severe = (scene.issues_by_severity.critical ?? 0) + (scene.issues_by_severity.high ?? 0);
    return severe > 0 ? "Flagged" : "Review";
  }
  return "Logged";
}

/** Human-readable value for a slot half, tolerating nulls and non-strings. */
export function slotValue(half: SlotView["expected"]): string {
  if (!half || half.value === null || half.value === undefined) return "—";
  return String(half.value);
}

/** Label + colour token for a slot state, used by the tracking tables. */
export function slotStateLabel(slot: SlotView): { label: string; color: string } {
  switch (slot.state) {
    case "match":
      return { label: "Verified", color: "var(--verse-emerald)" };
    case "conflict":
      return slot.flagged
        ? { label: "Mismatch", color: "var(--verse-red)" }
        : { label: "Differs (low confidence)", color: "var(--verse-gold)" };
    case "unverified":
      return { label: "Awaiting footage", color: "#64748B" };
    case "observed_only":
      return { label: "Unscripted", color: "var(--verse-violet)" };
    default:
      return { label: slot.state, color: "#64748B" };
  }
}

/** Format a 0–1 confidence as a percentage string. */
export function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}
