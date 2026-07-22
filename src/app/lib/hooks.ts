/**
 * VERSE API Hooks
 * React hooks that wrap the API client with loading/error/data state.
 * Keeps all async logic out of page components.
 */

import { useEffect, useState, useCallback, useRef } from "react";
import {
  auth, projects, continuity, upload, system,
  TokenStore, UserStore,
  type VERSEUser, type Project, type TeamMember,
  type ContinuityReport, type ContinuityIssue, type AuthResponse,
  type UploadResult, APIError,
} from "./api";

// ─── Generic async state ──────────────────────────────────────────────────────

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

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

// ─── Upload hook ──────────────────────────────────────────────────────────────

export function useScreenplayUpload(projectId: string) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = useCallback(async (file: File): Promise<UploadResult | null> => {
    setLoading(true); setError(null);
    try {
      const r = await upload.screenplay(projectId, file);
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
