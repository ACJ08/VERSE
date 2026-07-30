/**
 * VERSE API Hooks
 * React hooks that wrap the API client with loading/error/data state.
 * Keeps all async logic out of page components.
 */
import { useEffect, useState, useCallback, useRef } from "react";
import {
  auth,
  projects,
  continuity,
  upload,
  system,
  scriptIntelligence,
  TokenStore,
  UserStore,
  type VERSEUser,
  type Project,
  type TeamMember,
  type ContinuityReport,
  type ContinuityIssue,
  type AuthResponse,
  type UploadResult,
  type AnalyseScriptResult,
  type SceneAnalysis,
  type FootageUploadResult,
  type ProjectScenes,
  type EntityView,
  type SceneView,
  APIError,
} from "./api";

function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null });
  const mounted = useRef(true);

  const run = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fn();
      if (mounted.current) setState({ data, loading: false, error: null });
    } catch (e) {
      if (mounted.current) setState({ data: null, loading: false, error: e instanceof Error ? e.message : String(e) });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    mounted.current = true;
    run();
    return () => { mounted.current = false; };
  }, [run]);

  return { ...state, refetch: run };
}

// ─── Auth hooks ───────────────────────────────────────────────────────────────

export function useCurrentUser() {
  const [user, setUser] = useState<VERSEUser | null>(UserStore.get());
  const [token, setToken] = useState<string | null>(TokenStore.get());

  const handleAuthResponse = useCallback((res: AuthResponse) => {
    TokenStore.set(res.access_token);
    UserStore.set(res.user);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const signOut = useCallback(() => {
    TokenStore.clear();
    setToken(null);
    setUser(null);
  }, []);

  return { user, token, isAuthenticated: !!token, handleAuthResponse, signOut };
}

export function useLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (email: string, password: string): Promise<AuthResponse | null> => {
    setLoading(true); setError(null);
    try {
      const res = await auth.login(email, password);
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { login, loading, error };
}

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const register = useCallback(async (
    email: string, password: string, name: string, organization?: string
  ): Promise<AuthResponse | null> => {
    setLoading(true); setError(null);
    try {
      return await auth.register({ email, password, name, organization });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { register, loading, error };
}

// ─── Projects hooks ───────────────────────────────────────────────────────────

export function useProjects() {
  return useAsync(() => projects.list(), [TokenStore.get()]);
}

export function useProject(id: string | null) {
  return useAsync(() => (id ? projects.get(id) : Promise.resolve(null)), [id]);
}

export function useProjectTeam(projectId: string | null) {
  return useAsync(() => (projectId ? projects.getTeam(projectId) : Promise.resolve(null)), [projectId]);
}

export function useCreateProject() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(async (data: {
    name: string; workspace_name?: string; production_type?: string;
    description?: string; start_date?: string; end_date?: string; team_size?: number;
  }): Promise<Project | null> => {
    setLoading(true); setError(null);
    try {
      return await projects.create(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create project.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { create, loading, error };
}

// ─── Continuity hooks ─────────────────────────────────────────────────────────

export function useContinuityReport(projectId: string | null, autoFetch = true) {
  const [report, setReport] = useState<ContinuityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyse = useCallback(async (sceneId?: string) => {
    if (!projectId) return;
    setLoading(true); setError(null);
    try {
      const r = await continuity.analyse(projectId, sceneId);
      setReport(r);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (autoFetch && projectId) analyse();
  }, [projectId, autoFetch, analyse]);

  return { report, loading, error, analyse };
}

export function useContinuityIssues(projectId: string | null) {
  return useAsync(() => (projectId ? continuity.issues(projectId) : Promise.resolve(null)), [projectId]);
}

export function useFeedback(projectId: string) {
  const [loading, setLoading] = useState(false);

  const submit = useCallback(async (
    issueId: string,
    action: "confirm" | "dismiss" | "resolve" | "reopen",
    note?: string,
  ): Promise<ContinuityIssue | null> => {
    setLoading(true);
    try {
      return await continuity.feedback(projectId, issueId, action, note);
    } catch {
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { submit, loading };
}

// ─── Scene & entity views ─────────────────────────────────────────────────────

/**
 * Per-scene rollup from the engine (score, issues, whether it has been shot).
 * `fallback` is returned while the backend is unreachable so demo pages keep
 * rendering their design-time content.
 */
export function useSceneViews(projectId: string | null, analyse = false) {
  const [data, setData] = useState<ProjectScenes | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectId) return null;
    setLoading(true); setError(null);
    try {
      const r = await continuity.scenes(projectId, analyse);
      setData(r);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load scenes.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId, analyse]);

  useEffect(() => { void load(); }, [load]);

  const scenes: SceneView[] = data?.scenes ?? [];
  return { data, scenes, overview: data?.overview ?? null, loading, error, refetch: load };
}

/**
 * Per-entity tracking state (expected vs observed per attribute, per scene).
 * Filter by `entityType` ("character" / "prop") and `attribute` ("wears") to
 * drive the costume and prop tracking screens off the same endpoint.
 */
export function useEntityViews(
  projectId: string | null,
  filters: { entityType?: string; attribute?: string } = {},
) {
  const { entityType, attribute } = filters;
  const [data, setData] = useState<EntityView[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!projectId) return null;
    setLoading(true); setError(null);
    try {
      const r = await continuity.entities(projectId, {
        entity_type: entityType,
        attribute,
      });
      setData(r);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load entities.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId, entityType, attribute]);

  useEffect(() => { void load(); }, [load]);

  return { entities: data, loading, error, refetch: load };
}

// ─── Upload hooks ─────────────────────────────────────────────────────────────

export function useScreenplayUpload(projectId: string) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = useCallback(async (file: File, analyse = false): Promise<UploadResult | null> => {
    setLoading(true); setError(null);
    try {
      const r = await upload.screenplay(projectId, file, analyse);
      setResult(r);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { uploadFile, loading, result, error };
}

/**
 * Footage upload: the vision pipeline's scene JSON, or a video clip when the
 * backend has a vision service configured. Analysis runs by default, so the
 * result already carries the refreshed report and scene rollup.
 */
export function useFootageUpload(projectId: string) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FootageUploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadFootage = useCallback(async (
    file: File,
    opts: { sceneId?: string; entityAliases?: Record<string, string> } = {},
  ): Promise<FootageUploadResult | null> => {
    setLoading(true); setError(null);
    try {
      const r = await upload.footage(projectId, file, { ...opts, analyse: true });
      setResult(r);
      return r;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Footage upload failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { uploadFootage, loading, result, error };
}

// ─── Backend health hook ──────────────────────────────────────────────────────

export function useBackendHealth() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    system.health()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  return online;
}

// ─── Script Intelligence hooks ────────────────────────────────────────────────

/** Health state of the script-intelligence microservice. */
export function useScriptIntelligenceHealth() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [graniteConfigured, setGraniteConfigured] = useState(false);

  useEffect(() => {
    scriptIntelligence.health()
      .then((res) => {
        setOnline(res.status === "ok");
        setGraniteConfigured(res.granite_configured);
      })
      .catch(() => setOnline(false));
  }, []);

  return { online, graniteConfigured };
}

/** Upload a screenplay to the script-intelligence service for AI analysis,
 *  then automatically forward the structured scene results to the
 *  continuity engine via /analyse-and-ingest. */
export function useScriptAnalyseAndIngest(projectId: string) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyseScriptResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (file: File): Promise<AnalyseScriptResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await scriptIntelligence.analyseAndIngest(file, projectId);
      setResult(res);
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  return { run, loading, result, error };
}

/** Analyse a single scene text block using the local Granite model. */
export function useSceneAnalysis() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SceneAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyse = useCallback(async (sceneText: string, sceneId?: string): Promise<SceneAnalysis | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await scriptIntelligence.analyseScene(sceneText, sceneId);
      setResult(res);
      return res;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scene analysis failed.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { analyse, loading, result, error };
}
