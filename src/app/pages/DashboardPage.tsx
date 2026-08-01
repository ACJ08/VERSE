// Dashboard Page — Complete role-based workspace for VERSE.
// Every sidebar nav item renders a dedicated, fully interactive page.
// Roles: producer, director, script-supervisor, continuity-supervisor,
//        production-manager, department-member, film-student
//
// Changelog:
//   - Added "Timeline Tracking" to continuity-supervisor nav and wired up a new
//     TimelineTracking component — this feature was listed in the role config but
//     was missing from the sidebar and dashboard routing.
//   - Added "Development" status colour entries to both ProducerOverview and
//     ProducerProductions status maps — previously unhandled, now rendered in purple.
//   - Added "Development" filter button to ProducerProductions filter bar.
//   - Wired the script + footage ingestion pipeline through to the pages that
//     read its output: Scene Tracking, Scene Timeline, Timeline Tracking,
//     Costume/Prop Tracking, Continuity Verification, Continuity Tracking and
//     Production Memory now render live engine data (GET /continuity/scenes and
//     /continuity/entities) and fall back to the design-time mock content when
//     the backend is offline or the project has no data yet.
//   - Added FootageUploadPanel: uploads the vision pipeline's scene JSON (or a
//     clip, when the backend has a vision service) and maps anonymous track ids
//     to script character names, which is what makes footage comparable.

import React, { useState } from "react";
import { toast } from "sonner";
import {
  Film, Brain, BarChart3, Users, Settings, Bell, Search, ChevronDown,
  Menu, AlertTriangle, CheckCircle, Clock, TrendingUp, Layers,
  FileText, Zap, Eye, MessageSquare, Home, LogOut, ArrowRight,
  BookOpen, Sparkles, ChevronRight, MoreHorizontal, Star,
  Plus, Download, Upload, RefreshCw, X, Calendar,
  Hash, Target, Award, Filter, Edit3,
  Trash2, Send, Globe, Lock, GitBranch, Wifi, WifiOff,
} from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line,
} from "recharts";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import verseLogo from "@/imports/VERSE_LOGO_2.png";
import {
  userRoles, aiRecommendations, teamMembers, characters, type UserRole,
} from "@/app/data/mockData";
import {
  projects as apiProjects, continuity as apiContinuity, upload as apiUpload,
  scriptIntelligence as apiScript,
  sceneStatus, slotStateLabel, slotValue, pct, toDisplaySeverity,
  type SceneView, type EntityView, type SlotView, type FootageUploadResult,
  type UploadResult, type Project, type TeamMember, type AnalyseScriptResult,
} from "@/app/lib/api";
import {
  useBackendHealth, useSceneViews, useEntityViews, useFootageUpload,
  useScriptIntelligenceHealth,
} from "@/app/lib/hooks";

// ─── Types ─────────────────────────────────────────────────────────────────────

interface DashboardPageProps {
  userRole: UserRole;
  productionName: string;
  userName?: string;
  onSignOut: () => void;
}

// ─── Navigation Config ─────────────────────────────────────────────────────────

const navigationConfigByRole: Record<UserRole, Array<{ icon: React.ElementType; label: string; badge?: string }>> = {
  producer: [
    { icon: Home, label: "Overview" },
    { icon: Film, label: "Productions" },
    { icon: Users, label: "Team" },
    { icon: Brain, label: "Continuity Reports" },
    { icon: BarChart3, label: "Analytics" },
    { icon: Sparkles, label: "AI Insights", badge: "4" },
    { icon: Settings, label: "Workspace" },
  ],
  director: [
    { icon: Home, label: "Overview" },
    { icon: Film, label: "Scene Tracking" },
    { icon: Users, label: "Characters" },
    { icon: Clock, label: "Production Timeline" },
    { icon: Sparkles, label: "AI Recommendations", badge: "3" },
    { icon: Brain, label: "Semantic Memory" },
    { icon: Settings, label: "Settings" },
  ],
  "script-supervisor": [
    { icon: Home, label: "Overview" },
    { icon: FileText, label: "Continuity Tracking" },
    { icon: BookOpen, label: "Screenplay Analysis" },
    { icon: Clock, label: "Scene Timeline" },
    { icon: AlertTriangle, label: "AI Alerts", badge: "2" },
    { icon: TrendingUp, label: "Narrative Progression" },
    { icon: Settings, label: "Settings" },
  ],
  "continuity-supervisor": [
    { icon: Home, label: "Overview" },
    { icon: Eye, label: "Costume Tracking" },
    { icon: Layers, label: "Prop Tracking" },
    // "Timeline Tracking" was listed in the role's feature set in mockData but was
    // missing from this nav config — added here to complete the feature surface.
    { icon: Clock, label: "Timeline Tracking" },
    { icon: CheckCircle, label: "Continuity Verification" },
    { icon: Brain, label: "Production Memory" },
    { icon: Settings, label: "Settings" },
  ],
  "production-manager": [
    { icon: Home, label: "Overview" },
    { icon: Users, label: "Team Collaboration" },
    { icon: Calendar, label: "Scheduling" },
    { icon: Settings, label: "Workspace Management" },
    { icon: BarChart3, label: "Reports" },
  ],
  "department-member": [
    { icon: Home, label: "Overview" },
    { icon: CheckCircle, label: "My Tasks" },
    { icon: FileText, label: "Notes" },
    { icon: Brain, label: "Continuity Updates" },
    { icon: MessageSquare, label: "Discussions" },
  ],
  "film-student": [
    { icon: Home, label: "Overview" },
    { icon: Film, label: "Demo Workspace" },
    { icon: BookOpen, label: "Tutorials" },
    { icon: Eye, label: "Sample Productions" },
    { icon: Star, label: "Interactive Learning" },
  ],
};

// ─── Shared Page Utilities ─────────────────────────────────────────────────────

function PageHeader({ title, subtitle, actions }: {
  title: React.ReactNode; subtitle?: React.ReactNode; actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 flex-wrap mb-6">
      <div>
        <h1 className="text-2xl font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{title}</h1>
        {subtitle && <p className="text-sm mt-1" style={{ color: "var(--muted-foreground)" }}>{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}

function Btn({ onClick, variant = "primary", icon: Icon, children }: {
  onClick?: () => void; variant?: "primary" | "secondary" | "ghost"; icon?: React.ElementType; children: React.ReactNode;
}) {
  const styles = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm",
    secondary: "border text-foreground hover:bg-muted transition-colors",
    ghost: "text-primary font-semibold text-xs hover:underline",
  };
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 h-9 text-sm font-medium px-3 rounded-lg transition-all ${styles[variant]}`}
      style={variant === "secondary" ? { borderColor: "var(--border)" } : {}}
    >
      {Icon && <Icon size={14} />}
      {children}
    </button>
  );
}

type CardVariant = "default" | "ai" | "analytics" | "continuity" | "production" | "workspace" | "dark";

const CARD_GRADIENTS: Record<CardVariant, { bg: string; border: string }> = {
  default:    { bg: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)",  border: "rgba(209,205,242,0.8)" },
  ai:         { bg: "linear-gradient(135deg, #F3F0FF 0%, #E9E3FF 100%)",  border: "rgba(124,58,237,0.18)" },
  analytics:  { bg: "linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)",  border: "rgba(59,130,246,0.18)" },
  continuity: { bg: "linear-gradient(135deg, #FFFDF0 0%, #FEF3C7 100%)",  border: "rgba(196,149,18,0.22)" },
  production: { bg: "linear-gradient(135deg, #EEF0FB 0%, #E4EAFF 100%)",  border: "rgba(29,52,97,0.14)"  },
  workspace:  { bg: "linear-gradient(135deg, #F0EFF8 0%, #E8E4FF 100%)",  border: "rgba(99,91,169,0.18)" },
  dark:       { bg: "linear-gradient(135deg, #1D3461 0%, #2D1B69 100%)",  border: "rgba(255,255,255,0.08)" },
};

function Card({ children, className = "", variant = "default" }: {
  children: React.ReactNode; className?: string; variant?: CardVariant;
}) {
  const { bg, border } = CARD_GRADIENTS[variant];
  return (
    <div
      className={`rounded-2xl p-6 border ${className}`}
      style={{ background: bg, borderColor: border }}
    >
      {children}
    </div>
  );
}

function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-bold text-foreground text-sm" style={{ fontFamily: "var(--font-display)" }}>{children}</h3>
      {action}
    </div>
  );
}

function SearchBox({ placeholder = "Search…", value, onChange }: { placeholder?: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 h-9 rounded-lg px-3 border" style={{ background: "white", borderColor: "var(--border)", minWidth: 200 }}>
      <Search size={13} style={{ color: "var(--muted-foreground)" }} />
      <input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none min-w-0"
      />
    </div>
  );
}

function StatusBadge({ label, color, bg }: { label: string; color: string; bg: string }) {
  return <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color, backgroundColor: bg }}>{label}</span>;
}

function VioletBadge({ children }: { children: React.ReactNode }) {
  return <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: "var(--verse-violet)", backgroundColor: "var(--verse-violet-light)" }}>{children}</span>;
}

function GoldBadge({ children }: { children: React.ReactNode }) {
  return <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: "var(--verse-gold)", backgroundColor: "var(--verse-gold-light)" }}>{children}</span>;
}

function ScorePill({ value }: { value: number }) {
  const color = value >= 90 ? "var(--verse-emerald)" : value >= 75 ? "var(--verse-gold)" : "var(--verse-red)";
  return <span className="text-xs font-bold" style={{ fontFamily: "var(--font-mono)", color }}>{value}%</span>;
}

function EmptyState({ icon: Icon, title, description, action }: {
  icon: React.ElementType; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ backgroundColor: "var(--verse-midnight-light)" }}>
        <Icon size={24} style={{ color: "var(--verse-midnight)" }} />
      </div>
      <h3 className="font-bold text-foreground mb-1" style={{ fontFamily: "var(--font-display)" }}>{title}</h3>
      <p className="text-sm mb-4" style={{ color: "var(--muted-foreground)" }}>{description}</p>
      {action}
    </div>
  );
}

function ActivityItem({ icon: Icon, color, text, time }: { icon: React.ElementType; color: string; text: string; time: string }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{ backgroundColor: `color-mix(in srgb, ${color} 12%, white)` }}>
        <Icon size={13} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-foreground leading-tight">{text}</p>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>{time}</p>
      </div>
    </div>
  );
}

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 rounded-full overflow-hidden" style={{ backgroundColor: "var(--muted)" }}>
      <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, backgroundColor: color }} />
    </div>
  );
}

// Shows a small pill indicating whether the backend API is reachable.
// Uses useBackendHealth() which pings /health on mount.
function BackendStatusBadge() {
  const online = useBackendHealth();
  if (online === null) return null; // still checking
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium mb-1"
      style={{
        backgroundColor: online ? "#ECFDF5" : "#FEF2F2",
        color: online ? "var(--verse-emerald)" : "var(--verse-red)",
      }}
    >
      {online ? <Wifi size={11} /> : <WifiOff size={11} />}
      {online ? "API connected" : "Demo mode"}
    </div>
  );
}

// ─── AI Analysis Modal ─────────────────────────────────────────────────────────

// ─── Live pipeline data ────────────────────────────────────────────────────────

/** Banner listing warnings the ingestion pipeline reported (missing aliases, offline services). */
function PipelineWarnings({ warnings }: { warnings?: string[] }) {
  if (!warnings || warnings.length === 0) return null;
  return (
    <div className="rounded-2xl border p-4 flex flex-col gap-1" style={{ borderColor: "rgba(196,149,18,0.3)", background: "var(--verse-gold-light)" }}>
      {warnings.map((w, i) => (
        <p key={i} className="text-xs" style={{ color: "#7C5E0B" }}>{w}</p>
      ))}
    </div>
  );
}

/** Small "live data" / "demo data" marker so evaluators know which they're seeing. */
function DataSourceBadge({ live, label = "engine" }: { live: boolean; label?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 h-5 px-2 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{
        color: live ? "var(--verse-emerald)" : "#64748B",
        background: live ? "#ECFDF5" : "#F1F3F7",
      }}
    >
      {live ? `Live · ${label}` : "Demo data"}
    </span>
  );
}

/**
 * Footage ingestion panel.
 *
 * Accepts the `scene_<id>.json` the vision pipeline writes, or a video clip when
 * the backend has VISION_SERVICE_URL configured. The alias field is the part that
 * makes the footage useful: the vision tracker emits PERSON_1/PERSON_2, and
 * without a mapping to script character names nothing can be compared.
 */
function FootageUploadPanel({
  projectId, onIngested,
}: { projectId?: string; onIngested?: (result: FootageUploadResult) => void }) {
  const { uploadFootage, loading, result, error } = useFootageUpload(projectId ?? "VERSE_DEMO");
  const [sceneId, setSceneId] = useState("");
  const [aliasText, setAliasText] = useState("");

  // "PERSON_1=Sarah, PERSON_2=Marcus" → {PERSON_1: "Sarah", PERSON_2: "Marcus"}
  const parseAliases = (): Record<string, string> => {
    const map: Record<string, string> = {};
    for (const pair of aliasText.split(/[,\n]/)) {
      const [from, to] = pair.split(/[=:]/);
      if (from?.trim() && to?.trim()) map[from.trim()] = to.trim();
    }
    return map;
  };

  const pickFile = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,.mp4,.mov,.mkv,.avi";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const res = await uploadFootage(file, {
        sceneId: sceneId.trim() || undefined,
        entityAliases: parseAliases(),
      });
      if (res) {
        toast.success(
          res.duplicate
            ? "This footage was already ingested — skipped."
            : `${res.frames_analysed} frames aggregated · ${res.facts_ingested} facts ingested.`,
        );
        onIngested?.(res);
      } else {
        toast.error("Footage ingestion failed.");
      }
    };
    input.click();
  };

  return (
    <Card variant="ai">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[140px]">
          <label className="text-xs font-bold text-muted-foreground">Scene ID</label>
          <input
            placeholder="SCENE_001"
            value={sceneId}
            onChange={(e) => setSceneId(e.target.value)}
            className="mt-1 w-full h-9 border rounded-lg px-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/25"
            style={{ borderColor: "var(--border)", background: "white" }}
          />
        </div>
        <div className="flex-[2] min-w-[220px]">
          <label className="text-xs font-bold text-muted-foreground">
            Identity mapping <span className="font-normal">— vision track id to script name</span>
          </label>
          <input
            placeholder="PERSON_1=Sarah, PERSON_2=Marcus"
            value={aliasText}
            onChange={(e) => setAliasText(e.target.value)}
            className="mt-1 w-full h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25"
            style={{ borderColor: "var(--border)", background: "white" }}
          />
        </div>
        <Btn variant="primary" icon={Upload} onClick={pickFile}>
          {loading ? "Ingesting…" : "Upload Footage"}
        </Btn>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Accepts the vision pipeline's <span className="font-mono">scene_&lt;id&gt;.json</span>, or a
        video clip when a vision service is configured. Frames are aggregated to one
        observation per attribute before comparison.
      </p>

      {error && <p className="text-xs mt-2" style={{ color: "var(--verse-red)" }}>{error}</p>}

      {result && !loading && (
        <div className="mt-3 flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <StatusBadge label={`${result.frames_analysed} frames`} color="var(--verse-violet)" bg="var(--verse-violet-light)" />
            <StatusBadge label={`${result.facts_ingested} facts`} color="var(--verse-midnight)" bg="var(--verse-midnight-light)" />
            {result.report && <ScorePill value={Math.round(result.report.overall_score)} />}
            {result.entities && result.entities.length > 0 && (
              <span className="text-muted-foreground">Detected: {result.entities.join(", ")}</span>
            )}
          </div>
          <PipelineWarnings warnings={result.warnings} />
        </div>
      )}
    </Card>
  );
}

function AIAnalysisModal({ isOpen, onClose, projectId }: { isOpen: boolean; onClose: () => void; projectId?: string }) {
  const [phase, setPhase] = useState<"loading" | "done">("loading");
  const [stepIndex, setStepIndex] = useState(0);
  const [liveIssues, setLiveIssues] = useState<Array<{ severity: "critical"|"warning"|"info"; scene: string; issue: string; confidence: number }>>([]);
  const [scriptStats, setScriptStats] = useState<{ scenes: number; characters: number; props: number; extractor: string } | null>(null);
  // hasStarted prevents the analysis from being re-triggered on every render
  const hasStarted = React.useRef(false);

  const processingSteps = [
    { label: "Parsing screenplay semantic structure…", duration: 700 },
    { label: "Extracting scenes via IBM Granite…", duration: 800 },
    { label: "Cross-referencing character states…", duration: 900 },
    { label: "Comparing wardrobe consistency logs…", duration: 700 },
    { label: "Detecting continuity discrepancies…", duration: 800 },
    { label: "Building production knowledge graph…", duration: 900 },
    { label: "Generating explainable AI recommendations…", duration: 700 },
  ];

  const runAnalysis = React.useCallback(async () => {
    setPhase("loading");
    setStepIndex(0);
    setLiveIssues([]);
    setScriptStats(null);

    // Animate steps while the real API call runs in parallel
    let currentStep = 0;
    const animateSteps = () => {
      if (currentStep >= processingSteps.length) return;
      setStepIndex(currentStep);
      setTimeout(() => { currentStep++; animateSteps(); }, processingSteps[currentStep]?.duration ?? 700);
    };
    animateSteps();

    const pid = projectId ?? "VERSE_DEMO";

    // Parallel: fetch continuity issues + engine scene stats
    await Promise.allSettled([
      // Primary: ask continuity engine for the analysis report
      apiContinuity.analyse(pid).then((report) => {
        const sev = (s: string): "critical"|"warning"|"info" =>
          s === "critical" ? "critical" : s === "high" || s === "medium" ? "warning" : "info";
        setLiveIssues(
          report.issues.slice(0, 5).map((i) => ({
            severity: sev(i.severity),
            scene: i.scene_id ?? "—",
            issue: i.explanation || i.attribute,
            confidence: Math.round(i.confidence * 100),
          }))
        );
      }).catch(() => {}),

      // Secondary: get scene + entity stats from the engine graph
      apiContinuity.scenes(pid, false).then((scenesData) => {
        if (scenesData.scenes?.length) {
          const allEntities = scenesData.scenes.flatMap((sv) => sv.entities ?? []);
          const chars = allEntities.filter((e) => e.type === "character" || e.key?.startsWith("character:")).length;
          const props = allEntities.filter((e) => e.type === "prop"      || e.key?.startsWith("prop:")).length;
          setScriptStats({
            scenes: scenesData.scenes.length,
            characters: chars,
            props: props,
            extractor: "Granite / VERSE Engine",
          });
        }
      }).catch(() => {}),
    ]);

    // Wait for animation to finish before showing results
    const totalDuration = processingSteps.reduce((s, p) => s + p.duration, 0);
    setTimeout(() => setPhase("done"), totalDuration);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Kick off analysis exactly once when the modal opens
  React.useEffect(() => {
    if (isOpen && !hasStarted.current) {
      hasStarted.current = true;
      runAnalysis();
    }
    if (!isOpen) {
      hasStarted.current = false;
      setPhase("loading");
      setStepIndex(0);
      setLiveIssues([]);
      setScriptStats(null);
    }
  }, [isOpen, runAnalysis]);

  if (!isOpen) return null;

  const displayResults = liveIssues;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6">
      <div className="absolute inset-0 bg-foreground/30 backdrop-blur-sm" onClick={phase === "done" ? onClose : undefined} />
      <div className="relative rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden" style={{ background: "linear-gradient(160deg, #F5F3FF 0%, #EDE9FE 100%)" }}>
        <div className="px-6 py-5 border-b flex items-center justify-between" style={{ backgroundColor: "var(--verse-midnight)", borderColor: "rgba(255,255,255,0.1)" }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ backgroundColor: "var(--verse-violet-light)" }}>
              <Brain size={18} style={{ color: "var(--verse-violet)" }} />
            </div>
            <div>
              <p className="text-sm font-bold text-white">VERSE AI Analysis</p>
              <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
                {scriptStats ? `${scriptStats.extractor}` : "IBM Granite · VERSE Engine"}
              </p>
            </div>
          </div>
          {phase === "done" && <button onClick={onClose} className="text-white/50 hover:text-white transition-colors"><X size={18} /></button>}
        </div>
        <div className="p-6">
          {phase === "loading" ? (
            <div className="flex flex-col gap-4">
              <div className="text-center mb-2">
                <div className="w-16 h-16 rounded-2xl mx-auto mb-3 flex items-center justify-center relative" style={{ backgroundColor: "var(--verse-midnight-light)" }}>
                  <Brain size={28} style={{ color: "var(--verse-midnight)" }} />
                  <div className="absolute inset-0 rounded-2xl border-2 border-primary/30 animate-ping" />
                </div>
                <p className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>Analyzing Your Production</p>
                <p className="text-xs text-muted-foreground mt-1">IBM Granite · extracting scenes, characters, props…</p>
              </div>
              <div className="flex flex-col gap-2">
                {processingSteps.map((step, index) => (
                  <div key={step.label} className="flex items-center gap-3 py-2">
                    <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                      {index < stepIndex ? <CheckCircle size={16} className="text-primary" /> :
                       index === stepIndex ? <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" /> :
                       <div className="w-3 h-3 rounded-full bg-border" />}
                    </div>
                    <p className={`text-sm transition-colors ${index < stepIndex ? "text-muted-foreground line-through" : index === stepIndex ? "text-foreground font-medium" : "text-muted-foreground/50"}`}>{step.label}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle size={18} className="text-primary" />
                <p className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>Analysis Complete</p>
                <GoldBadge>{displayResults.length} issue{displayResults.length !== 1 ? "s" : ""} found</GoldBadge>
              </div>

              {/* Live script intelligence stats banner */}
              {scriptStats && (
                <div className="grid grid-cols-3 gap-2 rounded-xl p-3 border"
                  style={{ borderColor: "rgba(124,58,237,0.2)", background: "var(--verse-violet-light)" }}>
                  <div className="text-center">
                    <p className="text-lg font-bold" style={{ color: "var(--verse-violet)" }}>{scriptStats.scenes}</p>
                    <p className="text-[10px] text-muted-foreground">Scenes</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold" style={{ color: "var(--verse-midnight)" }}>{scriptStats.characters}</p>
                    <p className="text-[10px] text-muted-foreground">Characters</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-bold" style={{ color: "var(--verse-gold)" }}>{scriptStats.props}</p>
                    <p className="text-[10px] text-muted-foreground">Props</p>
                  </div>
                </div>
              )}

              {displayResults.length === 0 ? (
                <div className="py-6 text-center">
                  <CheckCircle size={32} className="mx-auto mb-2 text-emerald-500" />
                  <p className="text-sm font-semibold text-foreground">No continuity issues detected</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {scriptStats ? "Your screenplay looks clean — no conflicts found." : "Upload a screenplay first to run continuity analysis."}
                  </p>
                </div>
              ) : displayResults.map((result, idx) => {
                const colors = {
                  critical: { color: "var(--verse-red)", bg: "#FEF2F2", label: "Critical" },
                  warning: { color: "var(--verse-gold)", bg: "var(--verse-gold-light)", label: "Warning" },
                  info: { color: "#0F62FE", bg: "#EFF6FF", label: "Info" },
                };
                const c = colors[result.severity];
                return (
                  <div key={idx} className="p-4 rounded-xl border" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <StatusBadge label={c.label} color={c.color} bg={c.bg} />
                      <span className="text-xs font-mono text-muted-foreground">{result.scene}</span>
                      <span className="ml-auto text-xs font-bold text-primary">{result.confidence}%</span>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">{result.issue}</p>
                  </div>
                );
              })}
              {displayResults.length > 0 && (
                <button
                  onClick={() => { onClose(); toast.success("Analysis report saved to Continuity Reports."); }}
                  className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
                >
                  Save Report <Download size={15} />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

function DashboardSidebar({
  userRole, productionName, userName, isOpen, activeNav, onNavSelect, onSignOut,
}: {
  userRole: UserRole; productionName: string; userName: string;
  isOpen: boolean; activeNav: string;
  onNavSelect: (label: string) => void; onSignOut: () => void;
}) {
  const roleLabel = userRoles.find((r) => r.id === userRole)?.title ?? "Member";
  const navItems = navigationConfigByRole[userRole];

  return (
    <aside className={`fixed top-0 left-0 h-full z-40 border-r flex flex-col transition-all duration-300 ${isOpen ? "w-64" : "w-0 overflow-hidden"} lg:relative lg:w-64 lg:flex lg:overflow-visible`} style={{ background: "linear-gradient(180deg, #F5F3FF 0%, #EDE9FE 60%, #F0EFF8 100%)", borderColor: "rgba(209,205,242,0.9)" }}>
      <div className="p-5 border-b flex-shrink-0" style={{ borderColor: "var(--border)" }}>
        <ImageWithFallback src={verseLogo} alt="VERSE" style={{ width: "188px", height: "auto", objectFit: "contain", marginBottom: "16px" }} />
        <div className="rounded-xl p-3 border" style={{ backgroundColor: "var(--verse-midnight-light)", borderColor: "rgba(29,52,97,0.12)" }}>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: "var(--verse-emerald)" }} />
            <span className="text-xs font-bold" style={{ color: "var(--verse-emerald)" }}>In Production</span>
          </div>
          <p className="text-sm font-bold text-foreground leading-tight" style={{ fontFamily: "var(--font-display)" }}>{productionName}</p>
          <p className="text-xs text-muted-foreground mt-0.5">Feature Film · 2024</p>
        </div>
      </div>

      <nav className="flex-1 p-4 flex flex-col gap-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeNav === item.label;
          return (
            <button
              key={item.label}
              onClick={() => onNavSelect(item.label)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${isActive ? "bg-primary text-primary-foreground" : "text-foreground/70 hover:text-foreground hover:bg-muted"}`}
            >
              <Icon size={15} className="flex-shrink-0" />
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${isActive ? "bg-white/20 text-white" : "text-primary"}`} style={!isActive ? { backgroundColor: "var(--verse-violet-light)" } : {}}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t flex-shrink-0" style={{ borderColor: "var(--border)" }}>
        <BackendStatusBadge />
        <div className="flex items-center gap-3 mb-3 mt-3">
          <div className="w-9 h-9 rounded-full bg-primary text-primary-foreground text-sm font-bold flex items-center justify-center flex-shrink-0">
            {userName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">{userName}</p>
            <p className="text-xs text-muted-foreground">{roleLabel}</p>
          </div>
          <button className="text-muted-foreground hover:text-foreground transition-colors" onClick={() => toast.info("Profile settings coming soon.")}>
            <MoreHorizontal size={15} />
          </button>
        </div>
        <button onClick={onSignOut} className="w-full flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground px-3 py-2 rounded-lg hover:bg-muted transition-colors">
          <LogOut size={13} /> Sign Out
        </button>
      </div>
    </aside>
  );
}

// ─── Top Navigation Bar ────────────────────────────────────────────────────────

function DashboardTopNav({
  productionName, onMobileMenuToggle, activeRole, onRoleChange, onRunAIAnalysis,
  projects: projectList, activeProjectId, onProjectChange,
}: {
  productionName: string; onMobileMenuToggle: () => void;
  activeRole: UserRole; onRoleChange: (r: UserRole) => void;
  onRunAIAnalysis: () => void;
  projects: Project[]; activeProjectId: string | undefined;
  onProjectChange: (id: string) => void;
}) {
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [showProjectDropdown, setShowProjectDropdown] = useState(false);
  const [notifCount, setNotifCount] = useState(4);
  const [searchVal, setSearchVal] = useState("");
  const currentRoleLabel = userRoles.find((r) => r.id === activeRole)?.title ?? "Role";
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const projectDropdownRef = React.useRef<HTMLDivElement>(null);
  const activeProject = projectList.find((p) => p.id === activeProjectId);

  // Close dropdowns when clicking outside
  React.useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) setShowRoleDropdown(false);
      if (projectDropdownRef.current && !projectDropdownRef.current.contains(e.target as Node)) setShowProjectDropdown(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <header className="h-16 border-b flex items-center gap-4 px-5 flex-shrink-0" style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.9)" }}>
      <button className="lg:hidden text-muted-foreground hover:text-foreground transition-colors" onClick={onMobileMenuToggle}>
        <Menu size={20} />
      </button>

      {/* Project switcher — shown only when there are projects loaded */}
      {projectList.length > 0 ? (
        <div className="relative" ref={projectDropdownRef}>
          <button
            onClick={() => setShowProjectDropdown(!showProjectDropdown)}
            className="flex items-center gap-1.5 h-9 text-sm font-semibold px-3 rounded-lg transition-colors max-w-[200px]"
            style={{ background: "white", border: "1px solid var(--border)", color: "var(--foreground)" }}
          >
            <Film size={13} className="text-muted-foreground flex-shrink-0" />
            <span className="truncate">{activeProject?.name ?? productionName}</span>
            <ChevronDown size={12} className="text-muted-foreground flex-shrink-0" />
          </button>
          {showProjectDropdown && (
            <div className="absolute left-0 top-full mt-2 w-64 border rounded-xl shadow-lg z-50 py-1 overflow-hidden" style={{ background: "white", borderColor: "var(--border)" }}>
              <p className="text-xs font-bold tracking-widest uppercase text-muted-foreground px-3 py-2 border-b" style={{ borderColor: "var(--border)" }}>Switch Production</p>
              {projectList.map((proj) => (
                <button
                  key={proj.id}
                  onClick={() => { onProjectChange(proj.id); setShowProjectDropdown(false); toast.success(`Switched to "${proj.name}"`); }}
                  className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-sm transition-colors text-left ${proj.id === activeProjectId ? "bg-primary/5 text-primary font-semibold" : "text-foreground hover:bg-muted"}`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold truncate">{proj.name}</p>
                    <p className="text-xs text-muted-foreground">{proj.production_type ?? "Film"} · {proj.scenes_total} scenes</p>
                  </div>
                  {proj.id === activeProjectId && <CheckCircle size={13} className="ml-auto text-primary flex-shrink-0" />}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm text-muted-foreground min-w-0">
          <span className="font-semibold text-foreground truncate">{productionName}</span>
          <ChevronRight size={13} className="flex-shrink-0" />
          <span className="hidden sm:block">Dashboard</span>
        </div>
      )}

      <div className="flex-1" />

      <div className="hidden md:flex items-center gap-2 h-9 rounded-lg px-3 w-48 border" style={{ background: "white", borderColor: "var(--border)" }}>
        <Search size={13} className="text-muted-foreground flex-shrink-0" />
        <input
          placeholder="Search…"
          value={searchVal}
          onChange={(e) => setSearchVal(e.target.value)}
          className="flex-1 bg-transparent text-sm placeholder:text-muted-foreground focus:outline-none min-w-0"
          onKeyDown={(e) => e.key === "Enter" && toast.info(searchVal ? `Searching for "${searchVal}"…` : "Enter a search term.")}
        />
      </div>

      <button
        onClick={onRunAIAnalysis}
        className="hidden sm:flex items-center gap-1.5 h-9 text-xs font-bold px-3 rounded-lg transition-all hover:-translate-y-0.5"
        style={{ backgroundColor: "var(--verse-violet-light)", color: "var(--verse-violet)" }}
      >
        <Sparkles size={13} /> Analyze
      </button>

      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setShowRoleDropdown(!showRoleDropdown)}
          className="flex items-center gap-1.5 h-9 text-xs font-bold px-3 rounded-lg transition-colors"
          style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}
        >
          <Sparkles size={13} />
          <span className="hidden sm:block">{currentRoleLabel}</span>
          <ChevronDown size={12} />
        </button>
        {showRoleDropdown && (
          <div className="absolute right-0 top-full mt-2 w-52 border rounded-xl shadow-lg z-50 py-1" style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.9)" }}>
            <p className="text-xs font-bold tracking-widest uppercase text-muted-foreground px-3 py-2">Switch Role View</p>
            {userRoles.map((role) => (
              <button
                key={role.id}
                onClick={() => { onRoleChange(role.id); setShowRoleDropdown(false); toast.success(`Viewing as ${role.title}`); }}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-sm transition-colors ${activeRole === role.id ? "bg-primary/5 text-primary font-semibold" : "text-foreground hover:bg-muted"}`}
              >
                <span>{role.icon}</span>
                {role.title}
                {activeRole === role.id && <CheckCircle size={13} className="ml-auto text-primary" />}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        className="relative w-9 h-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
        onClick={() => { setNotifCount(0); toast.info("All notifications marked as read."); }}
      >
        <Bell size={16} />
        {notifCount > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-primary text-primary-foreground text-[9px] font-bold rounded-full flex items-center justify-center">{notifCount}</span>
        )}
      </button>
    </header>
  );
}

// ─── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, subtext, color = "var(--verse-midnight)", icon: Icon }: {
  label: string; value: string | number; subtext?: string; color?: string; icon: React.ElementType;
}) {
  return (
    <div className="rounded-2xl p-5 flex flex-col gap-3 hover:shadow-lg transition-all hover:-translate-y-1 border" style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${color} 7%, #F5F3FF) 0%, color-mix(in srgb, ${color} 14%, #EDE9FE) 100%)`, borderColor: `color-mix(in srgb, ${color} 22%, #D9D5F2)` }}>
      <div className="w-11 h-11 rounded-xl flex items-center justify-center shadow-sm" style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, white)`, border: `1px solid color-mix(in srgb, ${color} 28%, transparent)` }}>
        <Icon size={19} style={{ color }} />
      </div>
      <div>
        <p className="text-2xl font-black" style={{ fontFamily: "var(--font-display)", color: "var(--verse-midnight)" }}>{value}</p>
        <p className="text-sm mt-0.5" style={{ color: "var(--muted-foreground)" }}>{label}</p>
        {subtext && <p className="text-xs mt-0.5" style={{ color: "var(--muted-foreground)" }}>{subtext}</p>}
      </div>
    </div>
  );
}

// ─── AI Recommendation Card ────────────────────────────────────────────────────

function AIRecommendationCard({ rec, onAction }: { rec: typeof aiRecommendations[0]; onAction: (id: string, action: "accept" | "dismiss") => void }) {
  const configs = {
    critical: { color: "var(--verse-red)", bg: "#FEF2F2", label: "Critical" },
    warning: { color: "var(--verse-gold)", bg: "var(--verse-gold-light)", label: "Warning" },
    info: { color: "#0F62FE", bg: "#EFF6FF", label: "Info" },
  };
  const c = configs[rec.severity];
  return (
    <div className="rounded-2xl p-5 hover:shadow-md transition-all border" style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.85)" }}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <StatusBadge label={c.label} color={c.color} bg={c.bg} />
          <span className="text-xs font-bold" style={{ color: "var(--verse-violet)", fontFamily: "var(--font-mono)" }}>{rec.confidence}%</span>
        </div>
        <span className="text-xs text-muted-foreground">{rec.timestamp}</span>
      </div>
      <p className="text-xs font-bold text-muted-foreground mb-1" style={{ fontFamily: "var(--font-mono)" }}>{rec.scene}</p>
      <p className="text-sm text-foreground font-medium mb-3 leading-relaxed">{rec.issue}</p>
      <div className="rounded-xl p-3 mb-3" style={{ backgroundColor: "var(--muted)" }}>
        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-bold text-primary mr-1">VERSE suggests:</span>{rec.suggestion}
        </p>
      </div>
      <div className="flex gap-2">
        <button onClick={() => onAction(rec.id, "accept")} className="flex-1 h-8 text-xs font-bold rounded-lg transition-all" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>Accept</button>
        <button onClick={() => onAction(rec.id, "dismiss")} className="flex-1 h-8 border text-muted-foreground text-xs font-medium rounded-lg hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }}>Dismiss</button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRODUCER PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ProducerOverview({ productionName, onAIAction, projectId, userName }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void; projectId?: string; userName?: string }) {
  const [showNewProd, setShowNewProd] = useState(false);
  const [newProdName, setNewProdName] = useState("");
  const [creating, setCreating] = useState(false);

  // Live projects from the API
  const [liveProjects, setLiveProjects] = React.useState<Project[] | null>(null);
  React.useEffect(() => {
    apiProjects.list().then(setLiveProjects).catch(() => {});
  }, []);

  // Live continuity issues from the engine
  const [liveRecs, setLiveRecs] = React.useState<Array<{
    id: string; severity: "critical" | "warning" | "info";
    scene: string; issue: string; confidence: number;
    suggestion: string; timestamp: string;
  }> | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiContinuity.issues(projectId)
      .then((issues) => {
        setLiveRecs(
          issues.slice(0, 5).map((i) => ({
            id: i.issue_id,
            severity: toDisplaySeverity(i.severity),
            scene: i.scene_id ?? "—",
            issue: i.explanation || i.attribute,
            confidence: Math.round(i.confidence * 100),
            suggestion: i.suggested_fix || "Review the flagged scene with your script supervisor.",
            timestamp: "Just now",
          }))
        );
      })
      .catch(() => {});
  }, [projectId]);

  // Live scene overview
  const { overview, scenes: liveScenes } = useSceneViews(projectId ?? null);

  // Live team from the API
  const [liveTeam, setLiveTeam] = React.useState<TeamMember[] | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiProjects.getTeam(projectId).then(setLiveTeam).catch(() => {});
  }, [projectId]);

  const handleCreateProduction = async () => {
    if (!newProdName.trim()) { toast.error("Enter a production name."); return; }
    setCreating(true);
    try {
      const p = await apiProjects.create({ name: newProdName });
      toast.success(`"${p.name}" workspace created!`);
    } catch {
      toast.error("Could not create production — is the backend running?");
    } finally {
      setCreating(false);
      setNewProdName("");
      setShowNewProd(false);
    }
  };

  const statsIssues = liveRecs?.length ?? 0;
  const statsCritical = liveRecs?.filter((r) => r.severity === "critical").length ?? 0;

  const isLive = !!(overview || liveRecs || liveProjects);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">{`Good morning, ${userName ? userName.split(" ")[0] : "there"}.`} <DataSourceBadge live={isLive} /></span>}
        subtitle={`Production intelligence summary for ${productionName}.`}
        actions={<>
          <Btn variant="secondary" icon={Download} onClick={() => {
            toast.promise(new Promise((r) => setTimeout(r, 1200)), { loading: "Generating report…", success: "Production report ready.", error: "Failed." });
          }}>Export Report</Btn>
          <Btn variant="primary" icon={Plus} onClick={() => setShowNewProd(true)}>New Production</Btn>
        </>}
      />
      {showNewProd && (
        <div className="rounded-2xl border p-5 flex flex-col gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <p className="text-sm font-bold text-foreground">New Production</p>
          <input
            placeholder="Production name…"
            value={newProdName}
            onChange={(e) => setNewProdName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreateProduction()}
            className="h-10 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25"
            style={{ borderColor: "var(--border)" }}
            autoFocus
          />
          <div className="flex gap-2">
            <Btn variant="primary" onClick={handleCreateProduction}>{creating ? "Creating…" : "Create"}</Btn>
            <Btn variant="secondary" onClick={() => { setShowNewProd(false); setNewProdName(""); }}>Cancel</Btn>
          </div>
        </div>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active Productions" value={liveProjects?.length ?? "—"} icon={Film} color="var(--verse-midnight)" />
        <StatCard
          label="Scenes Logged"
          value={overview ? `${overview.scenes_shot}/${overview.scenes_total}` : "—"}
          subtext={overview ? `${overview.scenes_total > 0 ? Math.round((overview.scenes_shot / overview.scenes_total) * 100) : 0}% complete` : "Upload a screenplay"}
          icon={FileText}
          color="var(--verse-emerald)"
        />
        <StatCard
          label="Continuity Issues"
          value={statsIssues || "—"}
          subtext={statsCritical > 0 ? `${statsCritical} critical` : statsIssues > 0 ? "all low/medium" : "Upload screenplay"}
          icon={AlertTriangle}
          color="var(--verse-red)"
        />
        <StatCard
          label="Team Members"
          value={liveTeam?.length ?? "—"}
          subtext={liveTeam ? `${liveTeam.filter((m) => m.status === "accepted").length} active` : undefined}
          icon={Users}
          color="var(--verse-violet)"
        />
      </div>

      {/* Active projects from the API */}
      {liveProjects && liveProjects.length > 0 && (
        <Card>
          <SectionTitle action={<button className="text-xs text-primary font-semibold hover:underline" onClick={() => toast.info("Opening all productions…")}>View all</button>}>Active Productions</SectionTitle>
          <div className="flex flex-col gap-3">
            {liveProjects.map((proj) => {
              const sc = { Development: { c: "var(--verse-violet)", bg: "#F3F0FF" }, "Pre-Production": { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" }, "In Production": { c: "var(--verse-emerald)", bg: "#ECFDF5" }, "Post-Production": { c: "#0F62FE", bg: "#EFF6FF" }, Completed: { c: "#64748B", bg: "#F1F3F7" } }[proj.status] || { c: "#64748B", bg: "#F1F3F7" };
              return (
                <div key={proj.id} className="flex items-center gap-3 p-3 rounded-xl border hover:shadow-sm transition-all cursor-pointer" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Opening ${proj.name}…`)}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-semibold text-foreground truncate" style={{ fontFamily: "var(--font-display)" }}>{proj.name}</p>
                      <StatusBadge label={proj.status} color={sc.c} bg={sc.bg} />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{proj.production_type || "Film"}</span><span>·</span>
                      <span>{proj.scenes_total} scenes</span><span>·</span>
                      <span>{proj.facts_count} facts</span>
                    </div>
                  </div>
                  <ChevronRight size={13} className="text-muted-foreground flex-shrink-0" />
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Scene progress from the engine */}
      {overview && overview.scenes_total > 0 && (
        <Card>
          <SectionTitle>Scene Progress</SectionTitle>
          <div className="flex items-center gap-4 mb-2">
            <div className="flex-1"><ProgressBar value={(overview.scenes_shot / overview.scenes_total) * 100} color="var(--verse-midnight)" /></div>
            <span className="text-sm font-bold text-muted-foreground">{overview.scenes_shot}/{overview.scenes_total} shot</span>
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground mt-2">
            <span><span className="font-bold text-foreground">{overview.scenes_clean}</span> clean</span>
            <span><span className="font-bold text-foreground">{overview.issues_total}</span> open issues</span>
            <span>avg score <span className="font-bold text-foreground">{overview.average_scene_score}%</span></span>
            <span><span className="font-bold text-foreground">{overview.facts}</span> facts</span>
          </div>
        </Card>
      )}

      {/* AI Recommendations from the engine */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div>
          <SectionTitle>
            <span>AI Recommendations {liveRecs && liveRecs.length > 0 && <VioletBadge>{liveRecs.length} new</VioletBadge>}</span>
          </SectionTitle>
          {liveRecs && liveRecs.length > 0 ? (
            <div className="flex flex-col gap-3">
              {liveRecs.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
            </div>
          ) : (
            <EmptyState icon={Brain} title="No issues yet" description="Upload a screenplay to generate AI continuity recommendations." />
          )}
        </div>
        <div>
          <SectionTitle action={<Btn variant="ghost" onClick={() => toast.info("Opening team management…")}>Manage</Btn>}>Team</SectionTitle>
          {liveTeam && liveTeam.length > 0 ? (
            <Card>
              <div className="flex flex-col gap-3">
                {liveTeam.slice(0, 6).map((member) => (
                  <div key={member.id} className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full text-primary text-sm font-bold flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)" }}>
                      {member.email.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground truncate">{member.email}</p>
                      <p className="text-xs text-muted-foreground">{member.role}</p>
                    </div>
                    <StatusBadge label={member.status} color={member.status === "accepted" ? "var(--verse-emerald)" : "var(--verse-gold)"} bg={member.status === "accepted" ? "#ECFDF5" : "var(--verse-gold-light)"} />
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <EmptyState icon={Users} title="No team members yet" description="Invite colleagues to collaborate on this production." action={<Btn variant="primary" icon={Plus} onClick={() => toast.info("Opening invite…")}>Invite Member</Btn>} />
          )}
        </div>
      </div>
    </div>
  );
}

function ProducerProductions({ onOpenProject }: { onOpenProject?: (id: string) => void }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [liveProjects, setLiveProjects] = React.useState<Project[] | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    apiProjects.list()
      .then(setLiveProjects)
      .catch(() => setLiveProjects([]))
      .finally(() => setLoading(false));
  }, []);

  const filters = ["All", "Development", "Pre-Production", "In Production", "Post-Production", "Completed"];
  const filtered = (liveProjects ?? []).filter((p) =>
    (filter === "All" || p.status === filter) &&
    p.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Productions" subtitle="Manage all active and upcoming productions." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.info("Use the New Production button on Overview.")}>New Production</Btn>} />
      <div className="flex flex-wrap items-center gap-3">
        <SearchBox placeholder="Search productions…" value={search} onChange={setSearch} />
        <div className="flex items-center gap-1">
          {filters.map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`h-8 text-xs font-semibold px-3 rounded-lg transition-all ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>{f}</button>
          ))}
        </div>
      </div>
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Loading productions…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((proj) => {
            const sc = { Development: { c: "var(--verse-violet)", bg: "#F3F0FF" }, "Pre-Production": { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" }, "In Production": { c: "var(--verse-emerald)", bg: "#ECFDF5" }, "Post-Production": { c: "#0F62FE", bg: "#EFF6FF" }, Completed: { c: "#64748B", bg: "#F1F3F7" } }[proj.status] || { c: "#64748B", bg: "#F1F3F7" };
            return (
              <Card key={proj.id}>
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{proj.name}</h3>
                    <p className="text-xs text-muted-foreground">{proj.production_type || "Film"}</p>
                  </div>
                  <StatusBadge label={proj.status} color={sc.c} bg={sc.bg} />
                </div>
                <div className="grid grid-cols-3 gap-3 mb-4 text-center">
                  {[{ label: "Scenes", value: proj.scenes_total }, { label: "Facts", value: proj.facts_count }, { label: "Entities", value: proj.entities_count }].map((kpi) => (
                    <div key={kpi.label} className="rounded-lg p-2" style={{ backgroundColor: "var(--muted)" }}>
                      <p className="text-sm font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{kpi.value}</p>
                      <p className="text-xs text-muted-foreground">{kpi.label}</p>
                    </div>
                  ))}
                </div>
                {proj.description && <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{proj.description}</p>}
                <div className="flex gap-2">
                  <button onClick={() => { if (onOpenProject) { onOpenProject(proj.id); toast.success(`Switched to "${proj.name}"`); } else { toast.info(`Opening ${proj.name} workspace…`); } }} className="flex-1 h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>Open Workspace</button>
                  <button onClick={() => toast.info("Opening analytics…")} className="h-8 w-8 rounded-lg flex items-center justify-center border hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }}><BarChart3 size={13} className="text-muted-foreground" /></button>
                </div>
              </Card>
            );
          })}
          {filtered.length === 0 && !loading && (
            <div className="col-span-2">
              <EmptyState icon={Film} title="No productions yet" description="Create your first production from the Overview page." />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ProducerTeam() {
  const [liveTeam, setLiveTeam] = React.useState<TeamMember[] | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [inviting, setInviting] = useState(false);

  React.useEffect(() => {
    apiProjects.list()
      .then((projects) => projects[0] ? apiProjects.getTeam(projects[0].id) : Promise.resolve([]))
      .then(setLiveTeam)
      .catch(() => setLiveTeam([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = (liveTeam ?? []).filter((m) =>
    m.email.toLowerCase().includes(search.toLowerCase()) ||
    m.role.toLowerCase().includes(search.toLowerCase())
  );

  const handleInvite = async () => {
    if (!inviteEmail.trim()) { toast.error("Enter an email address."); return; }
    setInviting(true);
    try {
      const projectList = await apiProjects.list().catch(() => []);
      const projectId = projectList[0]?.id;
      if (projectId) {
        await apiProjects.inviteMember(projectId, inviteEmail);
        toast.success(`Invite sent to ${inviteEmail}!`);
      } else {
        toast.error("Create a project first before inviting team members.");
      }
    } catch {
      toast.error("Could not send invite — is the backend running?");
    } finally {
      setInviting(false);
      setInviteEmail("");
      setShowInvite(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Team" subtitle="Manage your production team." actions={<Btn variant="primary" icon={Plus} onClick={() => setShowInvite(true)}>Invite Member</Btn>} />
      {showInvite && (
        <div className="rounded-2xl border p-5 flex flex-col gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <p className="text-sm font-bold text-foreground">Invite Team Member</p>
          <input type="email" placeholder="colleague@studio.com" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleInvite()} className="h-10 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} autoFocus />
          <div className="flex gap-2">
            <Btn variant="primary" onClick={handleInvite}>{inviting ? "Sending…" : "Send Invite"}</Btn>
            <Btn variant="secondary" onClick={() => { setShowInvite(false); setInviteEmail(""); }}>Cancel</Btn>
          </div>
        </div>
      )}
      <div className="flex items-center gap-3">
        <SearchBox placeholder="Search team…" value={search} onChange={setSearch} />
      </div>
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Loading team…</div>
      ) : filtered.length === 0 ? (
        <EmptyState icon={Users} title="No team members yet" description="Invite colleagues to collaborate on this production." action={<Btn variant="primary" icon={Plus} onClick={() => setShowInvite(true)}>Invite Member</Btn>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((member) => {
            const statusColor = member.status === "accepted" ? "var(--verse-emerald)" : "var(--verse-gold)";
            return (
              <Card key={member.id}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-xl text-primary text-base font-black flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)", fontFamily: "var(--font-display)" }}>
                    {member.email.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-foreground truncate">{member.email}</p>
                    <p className="text-xs text-muted-foreground">{member.role}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                  <StatusBadge label={member.status} color={statusColor} bg={`color-mix(in srgb, ${statusColor} 12%, white)`} />
                  <span>Joined {new Date(member.joined_at).toLocaleDateString()}</span>
                </div>
                <button className="w-full h-7 text-xs font-medium rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info(`Viewing ${member.email}'s profile.`)}>Profile</button>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ProducerContinuityReports({ projectId }: { projectId?: string }) {
  const [filter, setFilter] = useState("All");
  const [isRunning, setIsRunning] = useState(false);
  const [liveReport, setLiveReport] = useState<{ score: number; issueCount: number } | null>(null);
  const [liveReportRows, setLiveReportRows] = React.useState<Array<{
    id: string; title: string; date: string; severity: string; scenes: number; issues: number; score: number;
  }> | null>(null);

  const sev = { critical: { c: "var(--verse-red)", bg: "#FEF2F2", l: "Critical" }, warning: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)", l: "Warning" }, info: { c: "#0F62FE", bg: "#EFF6FF", l: "Info" } };
  const filtered = (liveReportRows ?? []).filter((r) => filter === "All" || r.severity === filter.toLowerCase());

  React.useEffect(() => {
    if (!projectId) return;
    apiContinuity.issues(projectId).then((issues) => {
      const now = new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      setLiveReportRows(
        issues.slice(0, 10).map((issue, i) => ({
          id: issue.issue_id,
          title: issue.explanation || issue.attribute || `Issue #${i + 1}`,
          date: now,
          severity: toDisplaySeverity(issue.severity),
          scenes: issue.related_scene_ids?.length ?? 1,
          issues: 1,
          score: Math.round(100 - (issue.score_impact ?? 0) * 100),
        }))
      );
    }).catch(() => {});
  }, [projectId]);

  const handleRunAnalysis = async () => {
    if (isRunning) return;
    setIsRunning(true);
    try {
      const report = await apiContinuity.analyse(projectId ?? "VERSE_DEMO");
      setLiveReport({ score: Math.round(report.overall_score), issueCount: report.issues.length });
      const now = new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      setLiveReportRows(
        report.issues.slice(0, 10).map((issue, i) => ({
          id: issue.issue_id,
          title: issue.explanation || issue.attribute || `Issue #${i + 1}`,
          date: now,
          severity: toDisplaySeverity(issue.severity),
          scenes: issue.related_scene_ids?.length ?? 1,
          issues: 1,
          score: Math.round(100 - (issue.score_impact ?? 0) * 100),
        }))
      );
      toast.success(`Analysis complete — score ${Math.round(report.overall_score)}%, ${report.issues.length} issue(s) found.`);
    } catch {
      toast.error("Analysis failed — upload a screenplay first.");
    } finally {
      setIsRunning(false);
    }
  };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Continuity Reports"
        subtitle={liveReport ? `Latest run: ${liveReport.score}% continuity score · ${liveReport.issueCount} issue(s)` : "AI-generated continuity analysis reports."}
        actions={<>
          <Btn variant="secondary" icon={Download} onClick={() => toast.promise(new Promise((r) => setTimeout(r, 1000)), { loading: "Exporting reports…", success: "Reports exported.", error: "Export failed." })}>Export All</Btn>
          <Btn variant="primary" icon={RefreshCw} onClick={handleRunAnalysis}>{isRunning ? "Running…" : "Run Analysis"}</Btn>
        </>}
      />
      <div className="flex items-center gap-2">
        {["All", "Critical", "Warning", "Info"].map((f) => (
          <button key={f} onClick={() => setFilter(f)} className={`h-8 text-xs font-semibold px-3 rounded-lg transition-all ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>{f}</button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <EmptyState icon={FileText} title="No reports yet" description="Upload a screenplay and run analysis to generate continuity reports." action={<Btn variant="primary" icon={RefreshCw} onClick={handleRunAnalysis}>Run Analysis</Btn>} />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((r) => {
            const s = sev[r.severity as keyof typeof sev];
            return (
              <Card key={r.id}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge label={s.l} color={s.c} bg={s.bg} />
                      <h3 className="text-sm font-bold text-foreground">{r.title}</h3>
                    </div>
                    <p className="text-xs text-muted-foreground">{r.date} · {r.scenes} scenes reviewed · {r.issues} issue{r.issues !== 1 ? "s" : ""} found</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <ScorePill value={r.score} />
                    <p className="text-xs text-muted-foreground mt-0.5">score</p>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button className="text-xs font-medium text-primary hover:underline" onClick={() => toast.info(`Viewing: ${r.title}`)}>View Report →</button>
                  <button className="text-xs font-medium text-muted-foreground hover:text-foreground ml-auto" onClick={() => toast.promise(new Promise((res) => setTimeout(res, 800)), { loading: "Generating PDF…", success: `${r.title}.pdf ready.`, error: "Download failed." })}><Download size={12} className="inline mr-1" />PDF</button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ProducerAnalytics({ projectId }: { projectId?: string }) {
  const { overview, scenes } = useSceneViews(projectId ?? null);
  const [liveIssues, setLiveIssues] = React.useState<Array<{ severity: string; status: string }> | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiContinuity.issues(projectId).then((issues) => setLiveIssues(issues as any)).catch(() => {});
  }, [projectId]);

  const avgScore = overview?.average_scene_score ?? null;
  const totalIssues = liveIssues?.length ?? null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Analytics" subtitle="Production-wide performance metrics and trends." actions={<Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting analytics…")}>Export</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Avg. Continuity Score" value={avgScore != null ? `${avgScore}%` : "—"} icon={TrendingUp} color="var(--verse-emerald)" />
        <StatCard label="Total Issues" value={totalIssues ?? "—"} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Scenes in Engine" value={overview?.scenes_total ?? "—"} icon={Film} color="var(--verse-violet)" />
        <StatCard label="Semantic Facts" value={overview?.facts ?? "—"} icon={Brain} color="var(--verse-gold)" />
      </div>
      {scenes.length > 0 ? (
        <Card>
          <SectionTitle>Scene Continuity Scores</SectionTitle>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={scenes.slice(0, 20).map((s) => ({ name: s.scene_id.replace("SCENE_", "S"), score: Math.round(s.score), issues: s.issue_count }))}>
              <CartesianGrid key="bar-grid" strokeDasharray="3 3" stroke="#E8E5FF" />
              <XAxis key="bar-x" dataKey="name" tick={{ fontSize: 10, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <YAxis key="bar-y" domain={[0, 100]} tick={{ fontSize: 10, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <Tooltip key="bar-tooltip" contentStyle={{ borderRadius: 12, border: "1px solid #D9D5F2" }} />
              <Bar key="bar-score" dataKey="score" fill="var(--verse-midnight)" radius={[4, 4, 0, 0]} name="Score" />
              <Bar key="bar-issues" dataKey="issues" fill="#FEE2E2" radius={[4, 4, 0, 0]} name="Issues" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      ) : (
        <EmptyState icon={BarChart3} title="No data yet" description="Upload a screenplay to populate analytics." />
      )}
    </div>
  );
}

function ProducerAIInsights({ projectId }: { projectId?: string }) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [liveInsights, setLiveInsights] = React.useState<Array<{
    id: string; type: string; title: string; body: string; confidence: number; impact: string;
  }> | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const loadInsights = React.useCallback(async () => {
    if (!projectId) return;
    setIsRunning(true);
    try {
      const report = await apiContinuity.analyse(projectId);
      const sev = (s: string) => s === "critical" ? "Critical" : s === "high" ? "High" : s === "medium" ? "Medium" : "Low";
      const typeOf = (i: any): string => {
        if (i.category === "costume" || i.category === "prop") return "Pattern";
        if (i.category === "timeline") return "Anomaly";
        if (i.severity === "low") return "Opportunity";
        return "Prediction";
      };
      setLiveInsights(
        report.issues.slice(0, 8).map((i) => ({
          id: i.issue_id,
          type: typeOf(i),
          title: i.explanation || `${i.category}: ${i.attribute}`,
          body: i.suggested_fix || i.explanation || "Review this scene with your continuity supervisor.",
          confidence: Math.round(i.confidence * 100),
          impact: sev(i.severity),
        }))
      );
    } catch {
      toast.error("Upload a screenplay first to generate AI insights.");
    } finally {
      setIsRunning(false);
    }
  }, [projectId]);

  const colors = { Pattern: { c: "var(--verse-violet)", bg: "var(--verse-violet-light)" }, Prediction: { c: "#0F62FE", bg: "#EFF6FF" }, Opportunity: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Anomaly: { c: "var(--verse-red)", bg: "#FEF2F2" } };

  const visible = (liveInsights ?? []).filter((ins) => !dismissed.includes(ins.id));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-violet)" }}>Insights</span></span>} subtitle="IBM Granite-powered semantic analysis of your production." actions={
        <Btn variant="primary" icon={Sparkles} onClick={loadInsights}>{isRunning ? "Running…" : "Run Deep Analysis"}</Btn>
      } />
      <div className="flex flex-col gap-4">
        {visible.length === 0 && !isRunning && (
          <EmptyState icon={Sparkles} title="No insights yet" description="Click 'Run Deep Analysis' after uploading a screenplay to generate AI-powered insights." action={<Btn variant="primary" icon={Sparkles} onClick={loadInsights}>Run Deep Analysis</Btn>} />
        )}
        {visible.map((ins) => {
          const s = colors[ins.type as keyof typeof colors] ?? colors.Prediction;
          return (
            <Card key={ins.id}>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5" style={{ backgroundColor: s.bg }}>
                  <Brain size={18} style={{ color: s.c }} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge label={ins.type} color={s.c} bg={s.bg} />
                    <span className="text-xs font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--verse-violet)" }}>{ins.confidence}% confidence</span>
                    <span className="ml-auto text-xs font-bold" style={{ color: ins.impact === "Critical" ? "var(--verse-red)" : ins.impact === "High" ? "var(--verse-gold)" : "var(--verse-midnight)" }}>{ins.impact} impact</span>
                  </div>
                  <h3 className="font-bold text-foreground mb-1" style={{ fontFamily: "var(--font-display)" }}>{ins.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{ins.body}</p>
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button className="flex-1 h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.success(`Insight applied: "${ins.title}"`)}>Apply Insight</button>
                <button className="h-8 px-3 text-xs border rounded-lg text-muted-foreground hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }} onClick={() => { setDismissed((d) => [...d, ins.id]); toast.info("Insight dismissed."); }}>Dismiss</button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ProducerWorkspace() {
  const [wsName, setWsName] = useState("VERSE — The Last Scene");
  const [notifications, setNotifications] = useState(true);
  const [aiAuto, setAiAuto] = useState(true);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Workspace" subtitle="Manage your production workspace settings." />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 flex flex-col gap-5">
          <Card>
            <SectionTitle>General Settings</SectionTitle>
            <div className="flex flex-col gap-4">
              <div>
                <label className="text-sm font-semibold text-foreground block mb-1.5">Workspace Name</label>
                <input value={wsName} onChange={(e) => setWsName(e.target.value)} className="w-full h-10 px-3 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)", background: "white" }} />
              </div>
              <div>
                <label className="text-sm font-semibold text-foreground block mb-1.5">Production Type</label>
                <select className="w-full h-10 px-3 rounded-lg border text-sm focus:outline-none" style={{ borderColor: "var(--border)", background: "white" }}>
                  <option>Feature Film</option><option>TV Series</option><option>Documentary</option><option>Short Film</option>
                </select>
              </div>
              <Btn variant="primary" onClick={() => toast.success("Workspace settings saved!")}>Save Changes</Btn>
            </div>
          </Card>
          <Card>
            <SectionTitle>AI & Automation</SectionTitle>
            <div className="flex flex-col gap-4">
              {[
                { label: "AI Continuity Monitoring", description: "Automatically analyze scenes as they are logged.", val: aiAuto, set: setAiAuto },
                { label: "Email Notifications", description: "Receive daily production summaries.", val: notifications, set: setNotifications },
              ].map((s) => (
                <div key={s.label} className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{s.label}</p>
                    <p className="text-xs text-muted-foreground">{s.description}</p>
                  </div>
                  <button onClick={() => { s.set(!s.val); toast.success(`${s.label} ${!s.val ? "enabled" : "disabled"}.`); }} className={`relative w-10 h-5 rounded-full transition-all ${s.val ? "bg-primary" : "bg-muted"}`}>
                    <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${s.val ? "left-5" : "left-0.5"}`} />
                  </button>
                </div>
              ))}
            </div>
          </Card>
        </div>
        <div className="flex flex-col gap-4">
          <Card>
            <SectionTitle>Storage</SectionTitle>
            <div className="mb-3">
              <div className="flex justify-between text-xs text-muted-foreground mb-1"><span>Used</span><span>4.2 GB / 50 GB</span></div>
              <ProgressBar value={8.4} color="var(--verse-midnight)" />
            </div>
            <p className="text-xs text-muted-foreground">8.4% of workspace storage used.</p>
          </Card>
          <Card>
            <SectionTitle>Integrations</SectionTitle>
            <div className="flex flex-col gap-3">
              {[
                { name: "IBM watsonx", status: "Connected", icon: Brain, color: "var(--verse-violet)" },
                { name: "Slack", status: "Not connected", icon: MessageSquare, color: "#64748B" },
                { name: "Google Drive", status: "Connected", icon: Globe, color: "var(--verse-emerald)" },
              ].map((int) => (
                <div key={int.name} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `color-mix(in srgb, ${int.color} 12%, white)` }}>
                    <int.icon size={15} style={{ color: int.color }} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{int.name}</p>
                    <p className="text-xs" style={{ color: int.status === "Connected" ? "var(--verse-emerald)" : "var(--muted-foreground)" }}>{int.status}</p>
                  </div>
                  <button className="text-xs font-medium text-primary hover:underline" onClick={() => toast.info(`Managing ${int.name} integration…`)}>{int.status === "Connected" ? "Manage" : "Connect"}</button>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DIRECTOR PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function DirectorOverview({ productionName, onAIAction, projectId }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void; projectId?: string }) {
  const { scenes: liveScenes, overview } = useSceneViews(projectId ?? null);
  const { entities: liveEntities } = useEntityViews(projectId ?? null, { entityType: "character" });
  const [liveRecs, setLiveRecs] = React.useState<Array<{ id: string; severity: "critical"|"warning"|"info"; scene: string; issue: string; confidence: number; suggestion: string; timestamp: string }> | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiContinuity.issues(projectId).then((issues) => {
      setLiveRecs(issues.slice(0, 3).map((i) => ({
        id: i.issue_id, severity: toDisplaySeverity(i.severity),
        scene: i.scene_id ?? "—", issue: i.explanation || i.attribute,
        confidence: Math.round(i.confidence * 100),
        suggestion: i.suggested_fix || "Review with your script supervisor.",
        timestamp: "Just now",
      })));
    }).catch(() => {});
  }, [projectId]);

  const characterEntities = liveEntities ?? [];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Director's View" subtitle={`Scene tracking and character continuity for ${productionName}.`} actions={<Btn variant="primary" icon={Sparkles} onClick={() => toast.loading("Running scene analysis…")}>Analyze Scenes</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Scenes" value={overview?.scenes_total ?? "—"} icon={Film} color="var(--verse-midnight)" />
        <StatCard label="Characters Tracked" value={characterEntities.length || "—"} icon={Users} color="var(--verse-violet)" />
        <StatCard label="AI Issues" value={liveRecs?.length ?? "—"} icon={Sparkles} color="var(--verse-gold)" />
        <StatCard label="Continuity Score" value={overview?.average_scene_score != null ? `${overview.average_scene_score}%` : "—"} icon={CheckCircle} color="var(--verse-emerald)" />
      </div>
      {characterEntities.length > 0 ? (
        <Card>
          <SectionTitle>Character Continuity Tracker</SectionTitle>
          <div className="flex flex-col gap-4">
            {characterEntities.map((view) => {
              const summary = summariseEntity(view);
              return (
                <div key={view.entity.key} className="p-4 border rounded-xl" style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{view.entity.name}</h4>
                    {summary.continuity > 0 && (
                      <p className="text-xl font-black" style={{ fontFamily: "var(--font-display)", color: summary.continuity >= 90 ? "var(--verse-emerald)" : "var(--verse-gold)" }}>{summary.continuity}%</p>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">Scenes: {summary.scenes || "—"} · {summary.slots.length} tracked attribute(s)</p>
                </div>
              );
            })}
          </div>
        </Card>
      ) : (
        <EmptyState icon={Users} title="No characters yet" description="Upload a screenplay to extract and track characters automatically." />
      )}
      <div>
        <SectionTitle>AI Recommendations</SectionTitle>
        {liveRecs && liveRecs.length > 0 ? (
          <div className="flex flex-col gap-3">
            {liveRecs.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
          </div>
        ) : (
          <EmptyState icon={Brain} title="No issues detected" description="Upload a screenplay and footage to generate AI continuity recommendations." />
        )}
      </div>
    </div>
  );
}

const sceneList = [
  { id: "s1", scene: "Scene 17", location: "INT. OFFICE — DAY", chars: "Elena, Marcus", status: "Logged", shots: 8, duration: "3:42", score: 100 },
  { id: "s2", scene: "Scene 18", location: "INT. OFFICE — NIGHT", chars: "Elena, Dr. Park", status: "Flagged", shots: 5, duration: "2:15", score: 72 },
  { id: "s3", scene: "Scene 19", location: "EXT. PARKING LOT — NIGHT", chars: "Marcus", status: "In Progress", shots: 3, duration: "1:05", score: 85 },
  { id: "s4", scene: "Scene 20", location: "INT. CAFE — DAY", chars: "Elena", status: "Scheduled", shots: 0, duration: "—", score: 0 },
  { id: "s5", scene: "Scene 23", location: "INT. DINER — EVENING", chars: "Elena, Marcus", status: "Flagged", shots: 6, duration: "4:10", score: 81 },
  { id: "s6", scene: "Scene 24", location: "EXT. STREET — DAY", chars: "Marcus", status: "Logged", shots: 9, duration: "5:30", score: 96 },
  { id: "s7", scene: "Scene 31", location: "EXT. ROOFTOP — NIGHT", chars: "Elena, Marcus", status: "Review", shots: 7, duration: "3:55", score: 88 },
];

/**
 * Turn the engine's per-scene rollup into the rows this table already renders.
 * `shots` is the number of facts recorded for the scene — the closest live
 * equivalent to "how much do we know about this scene".
 */
function sceneViewsToRows(scenes: SceneView[]) {
  return scenes.map((s) => ({
    id: s.scene_id,
    scene: s.scene_id.replace(/_/g, " "),
    location: s.slugline ?? s.location ?? "—",
    chars: s.entities.filter((e) => e.type === "character").map((e) => e.name).join(", ") || "—",
    status: sceneStatus(s),
    shots: s.fact_count,
    duration: s.time_of_day ?? "—",
    score: s.has_footage ? Math.round(s.score) : 0,
  }));
}

function DirectorSceneTracking({ projectId }: { projectId?: string }) {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [showAddScene, setShowAddScene] = useState(false);
  const [newSceneName, setNewSceneName] = useState("");
  const [added, setAdded] = useState<ReturnType<typeof sceneViewsToRows>>([]);

  // Live scenes from the ingestion pipeline; the mock list stands in until a
  // screenplay has been ingested (or when the backend is offline).
  const { scenes: liveScenes, overview, loading } = useSceneViews(projectId ?? null);
  const isLive = liveScenes.length > 0;
  const scenes = [...(isLive ? sceneViewsToRows(liveScenes) : sceneList), ...added];

  const sev = { Logged: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Flagged: { c: "var(--verse-red)", bg: "#FEF2F2" }, "In Progress": { c: "var(--verse-violet)", bg: "var(--verse-violet-light)" }, Scheduled: { c: "#64748B", bg: "#F1F3F7" }, Review: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" } };
  const filtered = scenes.filter((s) => (filter === "All" || s.status === filter) && (s.scene + s.location + s.chars).toLowerCase().includes(search.toLowerCase()));
  const addScene = () => {
    if (!newSceneName.trim()) { toast.error("Enter a scene name."); return; }
    setAdded((prev) => [...prev, { id: `s${prev.length + 1}`, scene: newSceneName, location: "TBD", chars: "—", status: "Scheduled", shots: 0, duration: "—", score: 0 }]);
    toast.success(`${newSceneName} added.`);
    setNewSceneName(""); setShowAddScene(false);
  };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Scene Tracking <DataSourceBadge live={isLive} /></span>}
        subtitle={
          overview
            ? `${overview.scenes_shot}/${overview.scenes_total} scenes shot · ${overview.scenes_clean} clean · ${overview.issues_total} open issue(s) · avg score ${overview.average_scene_score}%`
            : loading ? "Loading scenes from the continuity engine…" : "Monitor all scenes across the production."
        }
        actions={<>
        <Btn variant="secondary" icon={Download} onClick={() => toast.promise(new Promise((r) => setTimeout(r, 800)), { loading: "Exporting…", success: "Scene log exported.", error: "Failed." })}>Export</Btn>
        <Btn variant="primary" icon={Plus} onClick={() => setShowAddScene(true)}>Add Scene</Btn>
      </>} />
      {showAddScene && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Scene name (e.g. Scene 35)…" value={newSceneName} onChange={(e) => setNewSceneName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addScene()} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={addScene}>Add</Btn>
          <Btn variant="secondary" onClick={() => { setShowAddScene(false); setNewSceneName(""); }}>Cancel</Btn>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <SearchBox placeholder="Search scenes…" value={search} onChange={setSearch} />
        <div className="flex items-center gap-1">
          {["All", "Logged", "In Progress", "Flagged", "Review", "Scheduled"].map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`h-8 text-xs font-semibold px-3 rounded-lg transition-all ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted"}`}>{f}</button>
          ))}
        </div>
      </div>
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b" style={{ borderColor: "var(--border)" }}>
                {["Scene", "Location", "Characters", "Shots", "Duration", "Status", "Score"].map((h) => (
                  <th key={h} className="pb-3 pr-4 text-left text-xs font-bold text-muted-foreground whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => {
                const s = sev[row.status as keyof typeof sev] || sev.Scheduled;
                return (
                  <tr key={row.id} className="border-b hover:bg-muted/30 transition-colors cursor-pointer" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Opening ${row.scene} detail…`)}>
                    <td className="py-3 pr-4 font-semibold text-foreground" style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>{row.scene}</td>
                    <td className="py-3 pr-4 text-muted-foreground text-xs max-w-[160px] truncate">{row.location}</td>
                    <td className="py-3 pr-4 text-muted-foreground text-xs">{row.chars}</td>
                    <td className="py-3 pr-4 text-foreground text-xs font-medium">{row.shots}</td>
                    <td className="py-3 pr-4 text-foreground text-xs font-mono">{row.duration}</td>
                    <td className="py-3 pr-4"><StatusBadge label={row.status} color={s.c} bg={s.bg} /></td>
                    <td className="py-3">{row.score > 0 ? <ScorePill value={row.score} /> : <span className="text-xs text-muted-foreground">—</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && <EmptyState icon={Film} title="No scenes match" description="Adjust your search or filter." />}
        </div>
      </Card>
    </div>
  );
}

function DirectorCharacters({ projectId }: { projectId?: string }) {
  const { entities: liveEntities, loading } = useEntityViews(projectId ?? null, { entityType: "character" });
  const [showAdd, setShowAdd] = useState(false);
  const [charName, setCharName] = useState("");
  const characters = liveEntities ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Characters" subtitle="Track character continuity and state across all scenes." actions={<Btn variant="primary" icon={Plus} onClick={() => setShowAdd(true)}>Add Character</Btn>} />
      {showAdd && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Character name…" value={charName} onChange={(e) => setCharName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && charName.trim() && (toast.success(`${charName} added.`), setCharName(""), setShowAdd(false))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!charName.trim()) { toast.error("Enter a name."); return; } toast.success(`${charName} character created.`); setCharName(""); setShowAdd(false); }}>Create</Btn>
          <Btn variant="secondary" onClick={() => { setShowAdd(false); setCharName(""); }}>Cancel</Btn>
        </div>
      )}
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Loading characters…</div>
      ) : characters.length === 0 ? (
        <EmptyState icon={Users} title="No characters yet" description="Upload a screenplay to extract characters automatically." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {characters.map((view) => {
            const summary = summariseEntity(view);
            const wears = view.latest.wears ? String(view.latest.wears) : "—";
            return (
              <Card key={view.entity.key}>
                <div className="flex items-start justify-between mb-4">
                  <div className="w-14 h-14 rounded-2xl font-black flex items-center justify-center text-2xl" style={{ backgroundColor: "var(--verse-midnight-light)", fontFamily: "var(--font-display)" }}>
                    {view.entity.name.split(" ").map((n: string) => n[0]).join("")}
                  </div>
                  <StatusBadge label={view.entity.type} color="var(--verse-midnight)" bg="var(--verse-midnight-light)" />
                </div>
                <h3 className="font-black text-foreground mb-0.5" style={{ fontFamily: "var(--font-display)" }}>{view.entity.name}</h3>
                <div className="flex flex-col gap-2 text-xs mb-4 mt-2">
                  {[
                    { label: "Scenes", val: view.scene_ids.length },
                    { label: "Attributes", val: view.attributes.join(", ") || "—" },
                    { label: "Costume", val: wears },
                  ].map((f) => (
                    <div key={f.label} className="flex items-start gap-2">
                      <span className="text-muted-foreground w-20 flex-shrink-0">{f.label}</span>
                      <span className="text-foreground font-medium flex-1">{f.val}</span>
                    </div>
                  ))}
                </div>
                {summary.continuity > 0 && (
                  <div className="mb-3">
                    <div className="flex justify-between text-xs text-muted-foreground mb-1"><span>Continuity</span><ScorePill value={summary.continuity} /></div>
                    <ProgressBar value={summary.continuity} color={summary.continuity >= 90 ? "var(--verse-emerald)" : "var(--verse-gold)"} />
                  </div>
                )}
                <button className="w-full h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info(`Opening ${view.entity.name} full profile…`)}>View Full Profile</button>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

const milestones = [
  { id: "m1", date: "Nov 12", label: "Pre-Production Complete", status: "done", color: "var(--verse-emerald)" },
  { id: "m2", date: "Nov 28", label: "Principal Photography Begins", status: "done", color: "var(--verse-emerald)" },
  { id: "m3", date: "Dec 12", label: "Act 1 Wrap", status: "done", color: "var(--verse-emerald)" },
  { id: "m4", date: "Dec 20", label: "Location Shoot — Rooftop", status: "current", color: "var(--verse-violet)" },
  { id: "m5", date: "Jan 5", label: "Act 2 Begins", status: "upcoming", color: "#CBD5E1" },
  { id: "m6", date: "Jan 30", label: "Principal Photography Wrap", status: "upcoming", color: "#CBD5E1" },
  { id: "m7", date: "Feb 15", label: "Post-Production Begins", status: "upcoming", color: "#CBD5E1" },
];

function DirectorTimeline({ projectId }: { projectId?: string }) {
  const { overview } = useSceneViews(projectId ?? null);

  // Compute days in production and days remaining from the active project
  const [projectDates, setProjectDates] = React.useState<{ start: string; end: string } | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiProjects.get(projectId)
      .then((p) => { if (p.start_date && p.end_date) setProjectDates({ start: p.start_date, end: p.end_date }); })
      .catch(() => {});
  }, [projectId]);

  const today = new Date();
  const daysIn = projectDates
    ? Math.max(0, Math.floor((today.getTime() - new Date(projectDates.start).getTime()) / 86400000))
    : null;
  const daysLeft = projectDates
    ? Math.max(0, Math.floor((new Date(projectDates.end).getTime() - today.getTime()) / 86400000))
    : null;
  const scenesShot = overview ? `${overview.scenes_shot}/${overview.scenes_total}` : null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Production Timeline" subtitle="Key milestones and schedule overview." actions={<Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting timeline…")}>Export Timeline</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Days in Production" value={daysIn ?? "—"} icon={Calendar} color="var(--verse-midnight)" />
        <StatCard label="Days Remaining" value={daysLeft ?? "—"} icon={Clock} color="var(--verse-gold)" />
        <StatCard label="Scenes Shot" value={scenesShot ?? "—"} icon={Film} color="var(--verse-emerald)" />
        <StatCard label="Avg. Score" value={overview?.average_scene_score != null ? `${Math.round(overview.average_scene_score)}%` : "—"} icon={CheckCircle} color="var(--verse-emerald)" />
      </div>
      <Card>
        <SectionTitle>Production Milestones</SectionTitle>
        <div className="relative pl-8">
          <div className="absolute left-3.5 top-2 bottom-2 w-px" style={{ background: "linear-gradient(to bottom, var(--verse-emerald), var(--verse-violet), #E8E5FF)" }} />
          <div className="flex flex-col gap-5">
            {milestones.map((m) => (
              <div key={m.id} className="relative flex items-start gap-4">
                <div className="absolute -left-8 w-5 h-5 rounded-full border-2 border-white flex items-center justify-center flex-shrink-0" style={{ backgroundColor: m.color, top: "2px" }}>
                  {m.status === "done" && <CheckCircle size={10} className="text-white" />}
                  {m.status === "current" && <div className="w-2 h-2 rounded-full bg-white animate-pulse" />}
                </div>
                <div className={`flex-1 p-3 rounded-xl border transition-all ${m.status === "current" ? "shadow-sm" : ""}`} style={{ borderColor: m.status === "current" ? m.color : "var(--border)", background: m.status === "current" ? `color-mix(in srgb, ${m.color} 5%, white)` : "transparent" }}>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-muted-foreground">{m.date}</span>
                    {m.status === "current" && <VioletBadge>Current</VioletBadge>}
                    {m.status === "done" && <StatusBadge label="Complete" color="var(--verse-emerald)" bg="#ECFDF5" />}
                  </div>
                  <p className={`text-sm font-semibold mt-0.5 ${m.status === "upcoming" ? "text-muted-foreground" : "text-foreground"}`}>{m.label}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}

function DirectorAIRecs({ onAIAction, projectId }: { onAIAction: (id: string, action: "accept" | "dismiss") => void; projectId?: string }) {
  const [liveRecs, setLiveRecs] = React.useState<Array<{ id: string; severity: "critical"|"warning"|"info"; scene: string; issue: string; confidence: number; suggestion: string; timestamp: string }> | null>(null);
  const [loading, setLoading] = React.useState(true);
  const load = React.useCallback(() => {
    if (!projectId) { setLoading(false); return; }
    setLoading(true);
    apiContinuity.issues(projectId).then((issues) => {
      setLiveRecs(issues.map((i) => ({
        id: i.issue_id, severity: toDisplaySeverity(i.severity),
        scene: i.scene_id ?? "—", issue: i.explanation || i.attribute,
        confidence: Math.round(i.confidence * 100),
        suggestion: i.suggested_fix || "Review the flagged scene.",
        timestamp: "Just now",
      })));
    }).catch(() => setLiveRecs([])).finally(() => setLoading(false));
  }, [projectId]);
  React.useEffect(() => { load(); }, [load]);

  const recs = liveRecs ?? [];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-violet)" }}>Recommendations</span></span>} subtitle="Explainable AI insights powered by IBM Granite." actions={<Btn variant="primary" icon={RefreshCw} onClick={load}>Refresh</Btn>} />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Pending Review" value={recs.filter(r => r.severity !== "info").length || "—"} icon={AlertTriangle} color="var(--verse-gold)" />
        <StatCard label="Critical" value={recs.filter(r => r.severity === "critical").length || "—"} icon={CheckCircle} color="var(--verse-red)" />
        <StatCard label="Total Issues" value={recs.length || "—"} icon={Brain} color="var(--verse-violet)" />
      </div>
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Loading recommendations…</div>
      ) : recs.length === 0 ? (
        <EmptyState icon={Brain} title="No issues detected" description="Upload a screenplay to generate AI continuity recommendations." />
      ) : (
        <div className="flex flex-col gap-3">
          {recs.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
        </div>
      )}
    </div>
  );
}

function DirectorSemanticMemory({ projectId }: { projectId?: string }) {
  const { entities: liveEntities, loading } = useEntityViews(projectId ?? null);
  const { overview } = useSceneViews(projectId ?? null);
  const entities = liveEntities ?? [];
  const entityColorMap: Record<string, string> = { character: "var(--verse-midnight)", prop: "var(--verse-gold)", location: "var(--verse-violet)", scene: "#CBD5E1" };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span><span style={{ color: "var(--verse-violet)" }}>Semantic</span> Memory</span>} subtitle="IBM Granite-constructed knowledge graph of your production's relationships." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Entities Tracked" value={overview?.entities ?? "—"} icon={Brain} color="var(--verse-violet)" />
        <StatCard label="Semantic Facts" value={overview?.facts ?? "—"} icon={GitBranch} color="var(--verse-midnight)" />
        <StatCard label="Scenes Analyzed" value={overview?.scenes_total ?? "—"} icon={Film} color="var(--verse-gold)" />
        <StatCard label="Memory Coverage" value={overview ? `${Math.round((overview.scenes_shot / Math.max(overview.scenes_total, 1)) * 100)}%` : "—"} icon={Layers} color="var(--verse-emerald)" />
      </div>
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Loading knowledge graph…</div>
      ) : entities.length === 0 ? (
        <EmptyState icon={Brain} title="Knowledge graph empty" description="Upload a screenplay to build the semantic knowledge graph." />
      ) : (
        <Card>
          <SectionTitle action={<VioletBadge>Live · IBM Granite</VioletBadge>}>Knowledge Graph — Key Entities</SectionTitle>
          <p className="text-xs text-muted-foreground mb-4">Semantic relationships between characters, locations, costumes, and props as constructed by the VERSE AI engine.</p>
          <div className="flex flex-col gap-4">
            {entities.slice(0, 10).map((view) => {
              const color = entityColorMap[view.entity.type] ?? "#64748B";
              const connections = view.scene_ids.slice(0, 5).map(id => id.replace(/_/g, " "));
              return (
                <div key={view.entity.key} className="p-4 rounded-xl border" style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                    <span className="text-sm font-bold text-foreground">{view.entity.name}</span>
                    <StatusBadge label={view.entity.type} color={color} bg={`color-mix(in srgb, ${color} 12%, white)`} />
                    <span className="ml-auto text-xs text-muted-foreground">{view.fact_count} facts</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {connections.map((c) => (
                      <button key={c} className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-muted" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Exploring: ${c}`)}>
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCRIPT SUPERVISOR PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ScriptSupervisorOverview({ productionName, onAIAction, projectId }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void; projectId?: string }) {
  const { scenes: liveScenes, overview } = useSceneViews(projectId ?? null);
  const [liveRecs, setLiveRecs] = React.useState<Array<{ id: string; severity: "critical"|"warning"|"info"; scene: string; issue: string; confidence: number; suggestion: string; timestamp: string }> | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiContinuity.issues(projectId).then((issues) => {
      setLiveRecs(issues.slice(0, 2).map((i) => ({
        id: i.issue_id, severity: toDisplaySeverity(i.severity),
        scene: i.scene_id ?? "—", issue: i.explanation || i.attribute,
        confidence: Math.round(i.confidence * 100),
        suggestion: i.suggested_fix || "Review the flagged scene.",
        timestamp: "Just now",
      })));
    }).catch(() => {});
  }, [projectId]);

  const rows = liveScenes.length > 0 ? sceneViewsToRows(liveScenes) : [];
  const issues = liveRecs ?? [];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Script Supervisor Overview <DataSourceBadge live={liveScenes.length > 0 || (liveRecs != null && liveRecs.length > 0)} /></span>}
        subtitle={`Continuity tracking for ${productionName}.`}
        actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New continuity note added.")}>Add Note</Btn>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Scenes" value={overview?.scenes_total ?? "—"} icon={FileText} color="#0F62FE" />
        <StatCard label="Issues" value={issues.length || "—"} subtext={issues.filter(i => i.severity === "critical").length > 0 ? `${issues.filter(i => i.severity === "critical").length} critical` : undefined} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Clean Scenes" value={overview?.scenes_clean ?? "—"} icon={Zap} color="var(--verse-gold)" />
        <StatCard label="Avg. Score" value={overview?.average_scene_score != null ? `${overview.average_scene_score}%` : "—"} icon={CheckCircle} color="var(--verse-emerald)" />
      </div>
      {rows.length > 0 ? (
        <Card>
          <SectionTitle action={<button className="text-xs text-primary font-semibold hover:underline" onClick={() => toast.info("Downloading CSV…")}><Download size={12} className="inline mr-1" />Export</button>}>Continuity Log</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b" style={{ borderColor: "var(--border)" }}>
                {["Scene", "Location", "Characters", "Status", "Score", "Flag"].map((h) => <th key={h} className="pb-3 pr-4 text-left text-xs font-bold text-muted-foreground">{h}</th>)}
              </tr></thead>
              <tbody>
                {rows.map((row) => {
                  const sc = { Flagged: { bg: "#FEF2F2", c: "var(--verse-red)" }, Logged: { bg: "#ECFDF5", c: "var(--verse-emerald)" }, Review: { bg: "var(--verse-gold-light)", c: "var(--verse-gold)" }, "In Progress": { bg: "var(--verse-violet-light)", c: "var(--verse-violet)" }, Scheduled: { bg: "#F1F3F7", c: "#64748B" } }[row.status] || { bg: "#F1F3F7", c: "#64748B" };
                  return (
                    <tr key={row.id} className="border-b hover:bg-muted/30 transition-colors" style={{ borderColor: "var(--border)" }}>
                      <td className="py-3 pr-4 font-semibold text-foreground" style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>{row.scene}</td>
                      <td className="py-3 pr-4 text-muted-foreground text-xs">{row.location}</td>
                      <td className="py-3 pr-4 text-muted-foreground text-xs">{row.chars}</td>
                      <td className="py-3 pr-4"><StatusBadge label={row.status} color={sc.c} bg={sc.bg} /></td>
                      <td className="py-3 pr-4">{row.score > 0 ? <ScorePill value={row.score} /> : <span className="text-xs text-muted-foreground">—</span>}</td>
                      <td className="py-3">{row.status === "Flagged" ? <AlertTriangle size={14} style={{ color: "var(--verse-red)" }} /> : <CheckCircle size={14} style={{ color: "var(--verse-emerald)" }} />}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState icon={FileText} title="No scenes yet" description="Upload a screenplay to populate the continuity log." />
      )}
      <div>
        <SectionTitle>AI Alerts</SectionTitle>
        {issues.length > 0 ? (
          <div className="flex flex-col gap-3">
            {issues.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
          </div>
        ) : (
          <EmptyState icon={Zap} title="No alerts" description="AI alerts will appear after screenplay upload and analysis." />
        )}
      </div>
    </div>
  );
}

function ContinuityTracking({ projectId }: { projectId?: string }) {
  const [showLog, setShowLog] = useState(false);
  const [newIssueDesc, setNewIssueDesc] = useState("");
  const [issues, setIssues] = useState<Array<{ id: string; scene: string; type: string; desc: string; severity: string; resolved: boolean; live: boolean }>>([]);
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [engineError, setEngineError] = useState<string | null>(null);

  // Converts a ContinuityIssue from the engine into the display shape.
  const mapIssue = (i: { issue_id: string; scene_id: string | null; category: string; explanation: string; attribute: string; expected: { value: unknown } | null; observed: { value: unknown } | null; severity: string; status: string }) => ({
    id: i.issue_id,
    scene: i.scene_id ?? "—",
    type: i.category ?? "General",
    desc: i.explanation || `${i.attribute ?? "attribute"}: expected ${String(i.expected?.value ?? "—")}, observed ${String(i.observed?.value ?? "—")}`,
    severity: i.severity === "critical" ? "critical" : i.severity === "low" ? "info" : ("warning" as "critical" | "warning" | "info"),
    resolved: i.status === "resolved" || i.status === "dismissed",
    live: true,
  });

  // Fetch live issues from the engine; surfaces errors instead of silently keeping stale mock data.
  const fetchIssues = React.useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    setEngineError(null);
    apiContinuity.issues(projectId)
      .then((liveIssues) => {
        setIsLive(true);
        setIssues(liveIssues.map(mapIssue));
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setEngineError(msg);
      })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  React.useEffect(() => { fetchIssues(); }, [fetchIssues]);

  const toggleResolved = async (id: string) => {
    const issue = issues.find((i) => i.id === id);
    // Optimistic update
    setIssues((prev) => prev.map((i) => i.id === id ? { ...i, resolved: !i.resolved } : i));
    if (issue?.live && projectId) {
      try {
        await apiContinuity.feedback(projectId, id, issue.resolved ? "reopen" : "resolve");
        toast.success(issue.resolved ? "Issue reopened." : "Issue resolved — score refreshed on next analysis.");
        // Refetch so stat cards reflect the real engine state
        fetchIssues();
        return;
      } catch {
        // Roll back optimistic change on error
        setIssues((prev) => prev.map((i) => i.id === id ? { ...i, resolved: issue.resolved } : i));
        toast.error("Could not record the decision with the engine.");
        return;
      }
    }
    toast.success("Continuity issue status updated.");
  };
  const sev = { critical: { c: "var(--verse-red)", bg: "#FEF2F2", l: "Critical" }, warning: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)", l: "Warning" }, info: { c: "#0F62FE", bg: "#EFF6FF", l: "Info" } };
  const openCount     = issues.filter((i) => !i.resolved).length;
  const resolvedCount = issues.filter((i) =>  i.resolved).length;
  const resolutionRate = issues.length > 0 ? Math.round((resolvedCount / issues.length) * 100) : 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Continuity Tracking <DataSourceBadge live={isLive} /></span>}
        subtitle="Monitor, flag, and resolve continuity issues. Resolving a detected issue is recorded with the engine and re-scores the production."
        actions={
          <div className="flex items-center gap-2">
            <Btn variant="secondary" icon={RefreshCw} onClick={fetchIssues}>Refresh</Btn>
            <Btn variant="primary" icon={Plus} onClick={() => setShowLog(true)}>Log Issue</Btn>
          </div>
        }
      />

      {/* Loading banner — shown while the first fetch is in flight */}
      {loading && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "rgba(124,58,237,0.25)", background: "var(--verse-violet-light)" }}>
          <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin flex-shrink-0" />
          <p className="text-sm font-medium" style={{ color: "var(--verse-violet)" }}>Loading continuity issues from the engine…</p>
        </div>
      )}

      {/* Engine error — surface the real reason instead of silently showing nothing */}
      {!loading && engineError && (
        <div className="rounded-2xl border p-4 flex items-start gap-3" style={{ borderColor: "rgba(239,68,68,0.25)", background: "#FEF2F2" }}>
          <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" style={{ color: "var(--verse-red)" }} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold" style={{ color: "var(--verse-red)" }}>Could not reach the continuity engine</p>
            <p className="text-xs text-muted-foreground mt-0.5 break-words">{engineError}</p>
          </div>
          <Btn variant="secondary" icon={RefreshCw} onClick={fetchIssues}>Retry</Btn>
        </div>
      )}

      {showLog && (
        <div className="rounded-2xl border p-4 flex flex-col gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <p className="text-sm font-bold text-foreground">Log New Issue</p>
          <textarea autoFocus placeholder="Describe the continuity issue…" value={newIssueDesc} onChange={(e) => setNewIssueDesc(e.target.value)} rows={2} className="border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <div className="flex gap-2">
            <Btn variant="primary" onClick={() => { if (!newIssueDesc.trim()) { toast.error("Enter a description."); return; } setIssues((prev) => [{ id: `ci${prev.length + 1}`, scene: "New Scene", type: "General", desc: newIssueDesc, severity: "info", resolved: false, live: false }, ...prev]); setNewIssueDesc(""); setShowLog(false); toast.success("Issue logged."); }}>Log Issue</Btn>
            <Btn variant="secondary" onClick={() => { setShowLog(false); setNewIssueDesc(""); }}>Cancel</Btn>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Open Issues"      value={loading ? "…" : openCount}                     icon={AlertTriangle} color="var(--verse-red)"      />
        <StatCard label="Resolved"         value={loading ? "…" : resolvedCount}                  icon={CheckCircle}   color="var(--verse-emerald)"  />
        <StatCard label="Resolution Rate"  value={loading ? "…" : `${resolutionRate}%`}            icon={TrendingUp}    color="var(--verse-midnight)" />
      </div>

      <div className="flex flex-col gap-3">
        {!loading && !engineError && issues.length === 0 && (
          <EmptyState
            icon={CheckCircle}
            title={isLive ? "No issues detected" : "No project selected"}
            description={
              isLive
                ? "The continuity engine found no open issues. Upload a screenplay to generate AI-powered continuity checks."
                : "Select a project to load live continuity issues from the engine."
            }
          />
        )}
        {issues.map((issue) => {
          const s = sev[issue.severity as keyof typeof sev];
          return (
            <Card key={issue.id}>
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <StatusBadge label={s.l} color={s.c} bg={s.bg} />
                    <span className="text-xs font-mono text-muted-foreground">{issue.scene}</span>
                    <span className="text-xs text-muted-foreground">· {issue.type}</span>
                    {issue.resolved && <StatusBadge label="Resolved" color="var(--verse-emerald)" bg="#ECFDF5" />}
                    {issue.live && <StatusBadge label="Live" color="var(--verse-emerald)" bg="#ECFDF5" />}
                  </div>
                  <p className={`text-sm leading-relaxed ${issue.resolved ? "line-through text-muted-foreground" : "text-foreground"}`}>{issue.desc}</p>
                </div>
                <button
                  onClick={() => toggleResolved(issue.id)}
                  className="flex-shrink-0 w-8 h-8 rounded-lg border flex items-center justify-center transition-colors hover:bg-muted"
                  style={{ borderColor: "var(--border)" }}
                  title={issue.resolved ? "Reopen issue" : "Mark resolved"}
                >
                  <CheckCircle size={15} style={{ color: issue.resolved ? "var(--verse-emerald)" : "var(--muted-foreground)" }} />
                </button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ScreenplayAnalysis({ projectId }: { projectId?: string }) {
  // ── script-intelligence service health ────────────────────────────────
  // Used to decide whether to call /api/v1/analyse-and-ingest (Granite AI)
  // or fall back to the engine's own extraction path.
  const { online: siOnline, graniteConfigured } = useScriptIntelligenceHealth();

  // ── upload state ───────────────────────────────────────────────────────
  const [uploading, setUploading]   = useState(false);
  const [analysing, setAnalysing]   = useState(false);
  const [activeTab, setActiveTab]   = useState<"scenes" | "characters" | "props" | "timeline">("scenes");
  // Live Granite result from script-intelligence service (optional)
  const [graniteResult, setGraniteResult] = useState<AnalyseScriptResult | null>(null);

  const [uploadResult, setUploadResult] = useState<{
    scenes_detected: number; facts_ingested: number; filename: string;
    extractor?: string;
    warnings?: string[];
    entities?: string[];   // "character:VICTOR_FRANKENSTEIN", "prop:KNIFE", …
  } | null>(null);

  // ── raw engine data ────────────────────────────────────────────────────
  const [sceneViews,  setSceneViews]  = useState<SceneView[]>([]);
  const [entityViews, setEntityViews] = useState<EntityView[]>([]);
  const [avgScore,    setAvgScore]    = useState<number | null>(null);

  // ── on-mount: load existing engine data ───────────────────────────────
  React.useEffect(() => {
    if (!projectId) return;
    setAnalysing(true);
    Promise.allSettled([
      apiContinuity.scenes(projectId, false),
      apiContinuity.entities(projectId),
    ]).then(([scenesRes, entitiesRes]) => {
      if (scenesRes.status === "fulfilled" && scenesRes.value.scenes?.length) {
        const views = scenesRes.value.scenes;
        setSceneViews(views);
        const ov = scenesRes.value.overview;
        setUploadResult((prev) => prev ?? {
          scenes_detected: ov?.scenes_total ?? views.length,
          facts_ingested:  ov?.facts        ?? views.reduce((n, sv) => n + sv.fact_count, 0),
          filename: "Previously ingested screenplay",
        });
        setAvgScore(
          ov?.average_scene_score != null
            ? Math.round(ov.average_scene_score)
            : views.length > 0
              ? Math.round(views.reduce((n, sv) => n + sv.score, 0) / views.length)
              : null,
        );
      }
      if (entitiesRes.status === "fulfilled" && entitiesRes.value.length) {
        setEntityViews(entitiesRes.value);
      }
    }).finally(() => setAnalysing(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // ── entity type classification ─────────────────────────────────────────
  // The heuristic extractor uses many raw_type strings (CHARACTER, ACTOR,
  // PERSON_NAME, etc.).  We check both entity.type and entity.raw_type so
  // entities are never silently dropped into an "unknown" bucket.
  const CHARACTER_TYPES = new Set(["character","person","actor","actor_name","person_name","character_name","named_entity"]);
  const PROP_TYPES      = new Set(["prop","object","item","artefact","artifact","thing","element"]);
  const LOCATION_TYPES  = new Set(["location","place","set","setting","environment","locale"]);

  const classifyEntity = (ev: EntityView): "character" | "prop" | "location" | "other" => {
    const t  = (ev.entity.type      ?? "").toLowerCase().replace(/[_\- ]/g, "");
    const rt = (ev.entity.raw_type  ?? "").toLowerCase().replace(/[_\- ]/g, "");
    const k  = (ev.entity.key       ?? "").toLowerCase();
    if (CHARACTER_TYPES.has(t) || CHARACTER_TYPES.has(rt)) return "character";
    if (PROP_TYPES.has(t)      || PROP_TYPES.has(rt))      return "prop";
    if (LOCATION_TYPES.has(t)  || LOCATION_TYPES.has(rt))  return "location";
    // Key-prefix heuristic: engine keys like "character:victor_frankenstein"
    if (k.startsWith("character:") || k.startsWith("person:") || k.startsWith("actor:")) return "character";
    if (k.startsWith("prop:") || k.startsWith("object:") || k.startsWith("item:"))       return "prop";
    if (k.startsWith("location:") || k.startsWith("place:") || k.startsWith("set:"))     return "location";
    return "other";
  };

  const charEntities = entityViews.filter((ev) => classifyEntity(ev) === "character");
  const propEntities = entityViews.filter((ev) => classifyEntity(ev) === "prop");
  const locEntities  = entityViews.filter((ev) => classifyEntity(ev) === "location");

  // ── parse upload-result entity strings as the ground-truth character list ──
  // UploadResult.entities[] contains strings like "character:VICTOR_FRANKENSTEIN"
  // or "prop:KNIFE" — these come directly from the ingestion pipeline and are the
  // most reliable source of type information when entity.type is ambiguous.
  const parseTypedEntities = (raw: string[]): EntityView[] =>
    raw.map((s): EntityView | null => {
      const colonIdx = s.indexOf(":");
      if (colonIdx === -1) return null;
      const rawType = s.slice(0, colonIdx).toLowerCase();
      const rawName = s.slice(colonIdx + 1);
      const name = rawName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      const key  = s.toLowerCase().replace(/ /g, "_");
      const type = CHARACTER_TYPES.has(rawType) ? "character"
                 : PROP_TYPES.has(rawType)      ? "prop"
                 : LOCATION_TYPES.has(rawType)  ? "location"
                 : rawType;
      return {
        entity: { type, name, key, raw_type: rawType },
        scene_ids: [], slots: [], attributes: [],
        issue_count: 0, conflict_count: 0, fact_count: 0, latest: {},
      };
    }).filter((x): x is EntityView => x !== null);

  // If the engine returned entities but none classified as characters,
  // treat ALL engine entities as potential characters (engine may use
  // non-standard type strings for real PDF extractions).
  // Also merge upload-result entity strings as a guaranteed character source.
  const buildCharList = (): EntityView[] => {
    // First try: properly classified characters from the engine
    if (charEntities.length > 0) return charEntities;

    // Second try: all engine entities (when type classification is ambiguous)
    if (entityViews.length > 0) return entityViews;

    // Third try: parse the upload-result entity strings directly
    if (uploadResult?.entities?.length) {
      return parseTypedEntities(uploadResult.entities).filter(
        (ev) => classifyEntity(ev) === "character"
      );
    }

    // Fourth try: mine names from SceneView.entities[] EntityRefs across all scenes
    if (sceneViews.length > 0) {
      const seen = new Set<string>();
      const synthChars: EntityView[] = [];
      sceneViews.forEach((sv) => {
        sv.entities.forEach((eref) => {
          const cls = classifyEntity({ entity: eref } as EntityView);
          if ((cls === "character" || cls === "other") && !seen.has(eref.key)) {
            seen.add(eref.key);
            synthChars.push({
              entity: eref,
              scene_ids: [sv.scene_id],
              slots: [], attributes: [],
              issue_count: 0, conflict_count: 0, fact_count: 0, latest: {},
            });
          }
        });
      });
      if (synthChars.length > 0) return synthChars;
    }

    return [];
  };

  const buildPropList = (): EntityView[] => {
    if (propEntities.length > 0) return propEntities;
    if (uploadResult?.entities?.length) {
      return parseTypedEntities(uploadResult.entities).filter(
        (ev) => classifyEntity(ev) === "prop"
      );
    }
    // Mine from SceneView entity refs
    const seen = new Set<string>();
    const synthProps: EntityView[] = [];
    sceneViews.forEach((sv) => {
      sv.entities.forEach((eref) => {
        if (classifyEntity({ entity: eref } as EntityView) === "prop" && !seen.has(eref.key)) {
          seen.add(eref.key);
          synthProps.push({
            entity: eref,
            scene_ids: [sv.scene_id],
            slots: [], attributes: [],
            issue_count: 0, conflict_count: 0, fact_count: 0, latest: {},
          });
        }
      });
    });
    return synthProps;
  };

  // ── fallback demo data shown before first upload ───────────────────────
  const demoScenes: SceneView[] = [
    { scene_id: "SCENE_017", sequence: 17, slugline: "INT. OFFICE — DAY",       location: "Office Interior",  time_of_day: "DAY",   score: 100, issue_count: 0, issues_by_severity: {}, category_scores: {}, categories: [], entities: [{ type: "character", name: "Elena Chen", key: "elena_chen", raw_type: null }, { type: "character", name: "Marcus Reyes", key: "marcus_reyes", raw_type: null }, { type: "prop", name: "Coffee Mug", key: "coffee_mug", raw_type: null }], sources: [], has_footage: false, fact_count: 5, headline: "Elena and Marcus discuss the case over coffee." },
    { scene_id: "SCENE_018", sequence: 18, slugline: "INT. OFFICE — MORNING",   location: "Office Interior",  time_of_day: "MORNING", score: 72, issue_count: 1, issues_by_severity: { warning: 1 }, category_scores: {}, categories: ["timeline"], entities: [{ type: "character", name: "Elena Chen", key: "elena_chen", raw_type: null }, { type: "character", name: "Dr. Park", key: "dr_park", raw_type: null }], sources: [], has_footage: false, fact_count: 3, headline: "Timeline inconsistency: Scene 17 ends Monday evening." },
    { scene_id: "SCENE_023", sequence: 23, slugline: "INT. DINER — EVENING",    location: "Diner Interior",   time_of_day: "EVENING", score: 81, issue_count: 1, issues_by_severity: { warning: 1 }, category_scores: {}, categories: ["costume"], entities: [{ type: "character", name: "Elena Chen", key: "elena_chen", raw_type: null }, { type: "prop", name: "Navy Jacket", key: "navy_jacket", raw_type: null }], sources: [], has_footage: false, fact_count: 4, headline: "Jacket colour conflict: navy vs. black between shots." },
  ];
  const demoEntityViews: EntityView[] = [
    { entity: { type: "character", name: "Elena Chen",   key: "elena_chen",   raw_type: null }, scene_ids: ["SCENE_017","SCENE_018","SCENE_023"], slots: [], attributes: ["wears","carries"], issue_count: 1, conflict_count: 1, fact_count: 8,  latest: { wears: "Navy blazer" } },
    { entity: { type: "character", name: "Marcus Reyes", key: "marcus_reyes", raw_type: null }, scene_ids: ["SCENE_017"],                        slots: [], attributes: ["wears"],           issue_count: 0, conflict_count: 0, fact_count: 3,  latest: { wears: "Charcoal suit" } },
    { entity: { type: "character", name: "Dr. Park",     key: "dr_park",      raw_type: null }, scene_ids: ["SCENE_018"],                        slots: [], attributes: ["wears"],           issue_count: 0, conflict_count: 0, fact_count: 2,  latest: { wears: "White lab coat" } },
    { entity: { type: "prop",      name: "Coffee Mug",   key: "coffee_mug",   raw_type: null }, scene_ids: ["SCENE_017"],                        slots: [], attributes: ["appearance"],      issue_count: 0, conflict_count: 0, fact_count: 1,  latest: {} },
    { entity: { type: "prop",      name: "Navy Jacket",  key: "navy_jacket",  raw_type: null }, scene_ids: ["SCENE_023"],                        slots: [], attributes: ["colour"],          issue_count: 1, conflict_count: 1, fact_count: 2,  latest: { colour: "Navy" } },
  ];

  // ── parse "character:ELENA_CHEN" → "Elena Chen" ───────────────────────
  const parseEntityNames = (raw: string[]): string[] =>
    raw.map((s) => {
      const name = s.includes(":") ? s.split(":").slice(1).join(":") : s;
      return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    });

  // ── synthesize tags from SceneView structural fields ──────────────────
  // Used as a per-scene fallback when EntityRef[] is empty.
  const synthesizeFromScene = (sv: SceneView): string[] => {
    const tags: string[] = [];
    if (sv.location) tags.push(sv.location);
    if (sv.time_of_day) tags.push(sv.time_of_day);
    if (sv.slugline) {
      sv.slugline.split(/[\-–—,/]+/).map((p) => p.trim()).forEach((part) => {
        const clean = part.replace(/^(INT|EXT|INT\/EXT|I\/E)\.\s*/i, "").trim();
        if (clean.length > 1 && clean !== sv.location && clean !== sv.time_of_day && !tags.includes(clean))
          tags.push(clean);
      });
    }
    sv.categories?.forEach((cat) => {
      const label = cat.charAt(0).toUpperCase() + cat.slice(1);
      if (!tags.includes(label)) tags.push(label);
    });
    return tags.filter(Boolean);
  };

  // ── upload handler ────────────────────────────────────────────────────
  // Primary path: script-intelligence /api/v1/analyse-and-ingest
  //   → Granite AI extracts characters, props, wardrobe, continuity notes
  //   → ingest_bridge.py forwards structured data to the continuity engine
  //   → we then ask the engine for scenes/entities to populate the UI
  // Fallback path: continuity-engine /upload/screenplay
  //   → Granite cloud or heuristic regex extraction, no wardrobe/props
  const handleUpload = async (file: File) => {
    if (!file) return;
    const pid = projectId ?? "VERSE_DEMO";
    setUploading(true);
    try {
      let rawResult: UploadResult;

      if (siOnline && graniteConfigured) {
        // ── Granite AI path via script-intelligence ──────────────────────
        // analyseAndIngest runs Granite scene analysis and POSTs structured
        // output to the continuity engine's /continuity/ingest/script.
        const graniteRes = await apiScript.analyseAndIngest(file, pid);
        setGraniteResult(graniteRes);

        // Build a synthetic UploadResult so downstream code stays uniform
        const charCount = graniteRes.scenes.reduce((n, s) => n + (s.characters?.length ?? 0), 0);
        const propCount = graniteRes.scenes.reduce((n, s) => n + (s.props?.length ?? 0), 0);
        rawResult = {
          project_id: pid,
          filename: graniteRes.filename,
          scenes_detected: graniteRes.scene_count,
          facts_ingested: charCount + propCount,
          graph_stats: {},
          extractor: "script-intelligence/granite",
          entities: [
            ...graniteRes.scenes.flatMap((s) => s.characters?.map((c) => `character:${c.name}`) ?? []),
            ...graniteRes.scenes.flatMap((s) => s.props?.map((p) => `prop:${p.name}`) ?? []),
          ],
          warnings: graniteRes.errors?.length ? graniteRes.errors : undefined,
        };

        toast.success(
          `"${graniteRes.filename}" analysed by IBM Granite — ${graniteRes.scene_count} scenes, ${charCount} characters, ${propCount} props extracted.`
        );
      } else {
        // ── Engine fallback path ─────────────────────────────────────────
        // Engine's own extraction: tries watsonx cloud Granite first, then
        // local Granite (port 11435), then heuristic regex parser.
        rawResult = await apiUpload.screenplay(pid, file);
        toast.success(`"${rawResult.filename}" ingested — ${rawResult.scenes_detected} scenes, ${rawResult.facts_ingested} facts extracted.`);
      }

      // Preserve entities[] — "character:NAME" strings are the ground-truth type map
      setUploadResult(rawResult);

      setAnalysing(true);
      try {
        const [scenesRes, entitiesRes] = await Promise.allSettled([
          apiContinuity.scenes(pid, /* analyse= */ true),
          apiContinuity.entities(pid),
        ]);

        if (scenesRes.status === "fulfilled") {
          const views = scenesRes.value.scenes ?? [];
          setSceneViews(views);
          const ov = scenesRes.value.overview;
          setAvgScore(
            ov?.average_scene_score != null
              ? Math.round(ov.average_scene_score)
              : views.length > 0
                ? Math.round(views.reduce((n, sv) => n + sv.score, 0) / views.length)
                : null,
          );
        } else if (rawResult.scene_ids?.length) {
          setSceneViews(rawResult.scene_ids.map((id, i) => ({
            scene_id: id, sequence: i + 1, slugline: id, location: null, time_of_day: null,
            score: 0, issue_count: 0, issues_by_severity: {}, category_scores: {},
            categories: [], entities: [], sources: [], has_footage: false, fact_count: 0, headline: "",
          })));
        }

        // Always store whatever the engine returns — buildCharList() handles
        // ambiguous entity.type values via its multi-fallback chain.
        if (entitiesRes.status === "fulfilled") {
          setEntityViews(entitiesRes.value);
        }
        // entities endpoint failure is handled by buildCharList() reading
        // uploadResult.entities directly — no separate synthesise step needed.
      } finally {
        setAnalysing(false);
      }
    } catch (e) {
      const isAuthError = e instanceof Error && (
        e.message.includes("401") ||
        e.message.toLowerCase().includes("not authenticated") ||
        e.message.toLowerCase().includes("sign in")
      );
      toast.error(
        isAuthError
          ? "You must be signed in to upload a screenplay. Please sign out and sign in again."
          : (e instanceof Error ? e.message : "Upload failed.")
      );
    } finally {
      setUploading(false);
    }
  };

  const openFilePicker = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.fdx,.txt,.fountain";
    input.onchange = () => { if (input.files?.[0]) handleUpload(input.files[0]); };
    input.click();
  };

  // ── Call-sheet upload ──────────────────────────────────────────────────
  const [callSheetUploading, setCallSheetUploading] = useState(false);
  const handleCallSheetUpload = async (file: File) => {
    const pid = projectId ?? "VERSE_DEMO";
    setCallSheetUploading(true);
    try {
      const result = await apiUpload.callSheet(pid, file);
      toast.success(`Call sheet "${result.filename}" ingested — ${result.facts_ingested} facts extracted.`);
      // Refresh entity views so costume/prop tabs reflect the new data
      const entitiesRes = await apiContinuity.entities(pid).catch(() => null);
      if (entitiesRes) setEntityViews(entitiesRes);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Call sheet upload failed.");
    } finally {
      setCallSheetUploading(false);
    }
  };
  const openCallSheetPicker = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".pdf,.txt,.csv";
    input.onchange = () => { if (input.files?.[0]) handleCallSheetUpload(input.files[0]); };
    input.click();
  };

  const isLive      = uploadResult != null;
  const scenes      = isLive ? sceneViews  : demoScenes;
  const allEntities = isLive ? entityViews : demoEntityViews;
  // Use the multi-fallback builders so Characters/Props tabs never show empty
  // when the engine has data — regardless of how entity.type is classified.
  const liveChars   = isLive ? buildCharList() : demoEntityViews.filter((e) => e.entity.type === "character");
  const liveProps   = isLive ? buildPropList() : demoEntityViews.filter((e) => e.entity.type === "prop");

  // Stat values
  const totalScenes  = uploadResult?.scenes_detected ?? scenes.length;
  const totalFacts   = uploadResult?.facts_ingested  ?? "—";
  const entityCount  = isLive ? allEntities.length : demoEntityViews.length;
  const scoreDisplay = avgScore != null ? `${avgScore}%` : (isLive ? "—" : "100%");

  // ── tab styles ─────────────────────────────────────────────────────────
  const tabs: { key: typeof activeTab; label: string; count: number }[] = [
    { key: "scenes",     label: "Scenes",     count: scenes.length },
    { key: "characters", label: "Characters", count: liveChars.length },
    { key: "props",      label: "Props",      count: liveProps.length },
    { key: "timeline",   label: "Timeline",   count: scenes.length },
  ];

  // ── service availability badge ─────────────────────────────────────────
  const extractorLabel = siOnline && graniteConfigured
    ? "IBM Granite · script-intelligence"
    : siOnline
      ? "script-intelligence (no Granite)"
      : "Engine extraction";

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Screenplay Analysis <DataSourceBadge live={isLive} /></span>}
        subtitle={
          <span>
            Upload your screenplay — VERSE extracts scenes, characters, props, and timelines automatically.{" "}
            <span className={`text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded ${siOnline && graniteConfigured ? "text-emerald-700 bg-emerald-50" : "text-slate-500 bg-slate-100"}`}>
              {extractorLabel}
            </span>
          </span>
        }
        actions={
          <>
            <Btn variant="secondary" icon={FileText} onClick={openCallSheetPicker}>
              {callSheetUploading ? "Uploading…" : "Call Sheet"}
            </Btn>
            <Btn variant="primary" icon={Upload} onClick={openFilePicker}>
              {uploading ? "Uploading…" : isLive ? "Re-upload Screenplay" : "Upload Screenplay"}
            </Btn>
          </>
        }
      />

      {/* Progress banners */}
      {(uploading || analysing) && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "rgba(124,58,237,0.25)", background: "var(--verse-violet-light)" }}>
          <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin flex-shrink-0" />
          <p className="text-sm font-medium" style={{ color: "var(--verse-violet)" }}>
            {uploading
              ? siOnline && graniteConfigured
                ? "Sending screenplay to IBM Granite for continuity analysis…"
                : "Ingesting screenplay into production memory…"
              : "Extracting scenes, characters, props and timeline…"}
          </p>
        </div>
      )}
      {uploadResult && !uploading && !analysing && (
        <div className="rounded-2xl border p-4 flex flex-col gap-1" style={{ borderColor: "rgba(5,150,105,0.25)", background: "#ECFDF5" }}>
          <div className="flex items-center gap-3">
            <CheckCircle size={16} style={{ color: "var(--verse-emerald)" }} />
            <p className="text-sm font-medium" style={{ color: "var(--verse-emerald)" }}>
              <span className="font-bold">{uploadResult.filename}</span> — {uploadResult.scenes_detected} scenes ingested, {uploadResult.facts_ingested} semantic facts extracted.
            </p>
          </div>
          {uploadResult.extractor && (
            <p className="text-[11px] text-muted-foreground ml-7">
              Extractor: <span className="font-semibold">{uploadResult.extractor}</span>
              {graniteResult && ` · ${graniteResult.scenes.reduce((n, s) => n + (s.characters?.length ?? 0), 0)} characters · ${graniteResult.scenes.reduce((n, s) => n + (s.props?.length ?? 0), 0)} props`}
            </p>
          )}
        </div>
      )}
      {uploadResult?.warnings && uploadResult.warnings.length > 0 && (
        <PipelineWarnings warnings={uploadResult.warnings} />
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Scenes"     value={totalScenes}  icon={FileText}    color="var(--verse-midnight)" />
        <StatCard label="Facts Extracted"  value={totalFacts}   icon={Brain}       color="var(--verse-violet)"   />
        <StatCard label="Entities Tracked" value={entityCount}  icon={Layers}      color="var(--verse-gold)"     />
        <StatCard label="Semantic Score"   value={scoreDisplay} icon={CheckCircle} color="var(--verse-emerald)"  />
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 rounded-xl border" style={{ borderColor: "var(--border)", background: "var(--muted)" }}>
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className="flex-1 flex items-center justify-center gap-1.5 h-8 rounded-lg text-xs font-semibold transition-all"
            style={activeTab === t.key
              ? { background: "white", color: "var(--verse-midnight)", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }
              : { color: "var(--muted-foreground)" }}
          >
            {t.label}
            <span className="inline-flex items-center justify-center rounded-md min-w-[18px] h-[18px] px-1 text-[10px] font-bold"
              style={activeTab === t.key
                ? { background: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }
                : { background: "transparent", color: "var(--muted-foreground)" }}>
              {t.count}
            </span>
          </button>
        ))}
      </div>

      {/* ── SCENES TAB ─────────────────────────────────────────────────── */}
      {activeTab === "scenes" && (
        <div className="flex flex-col gap-3">
          {scenes.length === 0 && !uploading && !analysing && (
            <div className="rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-14 gap-3" style={{ borderColor: "rgba(124,58,237,0.2)" }}>
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ backgroundColor: "var(--verse-violet-light)" }}>
                <FileText size={24} style={{ color: "var(--verse-violet)" }} />
              </div>
              <p className="font-bold text-foreground text-sm" style={{ fontFamily: "var(--font-display)" }}>Upload your screenplay to begin</p>
              <p className="text-xs text-muted-foreground text-center max-w-xs">Supports .pdf, .txt, .fountain, and .fdx formats.</p>
              <button onClick={openFilePicker} className="mt-1 flex items-center gap-2 h-9 text-sm font-semibold px-4 rounded-lg" style={{ backgroundColor: "var(--verse-midnight)", color: "white" }}>
                <Upload size={14} /> Choose File
              </button>
            </div>
          )}
          {scenes.map((sv, i) => {
            const entityNames = sv.entities.map((e) => e.name).filter(Boolean);
            const tags = entityNames.length > 0 ? entityNames : synthesizeFromScene(sv);
            const hasConflict = (sv.issue_count ?? 0) > 0;
            return (
              <Card key={sv.scene_id ?? i}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[10px] font-bold tabular-nums flex-shrink-0 rounded px-1.5 py-0.5" style={{ background: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>
                      #{sv.sequence || i + 1}
                    </span>
                    <div className="min-w-0">
                      <h3 className="font-bold text-foreground text-sm leading-tight truncate" style={{ fontFamily: "var(--font-display)" }}>
                        {sv.slugline ?? sv.scene_id}
                      </h3>
                      {sv.headline && <p className="text-xs text-muted-foreground truncate mt-0.5">{sv.headline}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                    {sv.fact_count > 0 && (
                      <span className="text-[10px] text-muted-foreground">{sv.fact_count} facts</span>
                    )}
                    {sv.score > 0 && <ScorePill value={Math.round(sv.score)} />}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {tags.length > 0 ? tags.map((e) => (
                    <span key={e} className="text-[11px] px-2 py-0.5 rounded-lg border"
                      style={{
                        borderColor: hasConflict ? "rgba(154,111,0,0.3)" : "var(--border)",
                        color:       hasConflict ? "var(--verse-gold)"   : "var(--muted-foreground)",
                        background:  hasConflict ? "var(--verse-gold-light)" : "transparent",
                      }}>
                      {e}
                    </span>
                  )) : (
                    <span className="text-xs text-muted-foreground italic">No entities</span>
                  )}
                  {hasConflict && (
                    <span className="text-[11px] px-2 py-0.5 rounded-lg border font-semibold" style={{ borderColor: "rgba(154,111,0,0.3)", color: "var(--verse-gold)", background: "var(--verse-gold-light)" }}>
                      ⚠ {sv.issue_count} issue{sv.issue_count !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* ── CHARACTERS TAB ─────────────────────────────────────────────── */}
      {activeTab === "characters" && (
        <div className="flex flex-col gap-3">
          {liveChars.length === 0 ? (
            <EmptyState icon={Users} title="No characters extracted yet"
              description={isLive ? "No characters were found in the production knowledge graph. Check the Scenes tab to see raw entity names extracted from the PDF." : "Upload a screenplay to extract character data."} />
          ) : (
            liveChars.map((ev) => {
              const initials = ev.entity.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase();
              const sceneCount = ev.scene_ids.length;
              const attrList = ev.attributes.length > 0 ? ev.attributes.join(", ") : null;
              const hasIssue = ev.conflict_count > 0;
              return (
                <Card key={ev.entity.key}>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl font-bold text-sm flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>
                      {initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-sm font-bold text-foreground">{ev.entity.name}</p>
                        {hasIssue && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded font-bold" style={{ background: "var(--verse-gold-light)", color: "var(--verse-gold)" }}>
                            {ev.conflict_count} conflict{ev.conflict_count !== 1 ? "s" : ""}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {sceneCount > 0 ? `Appears in ${sceneCount} scene${sceneCount !== 1 ? "s" : ""}` : "Scene data pending"}
                        {attrList ? ` · Tracked: ${attrList}` : ""}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs font-bold tabular-nums" style={{ color: "var(--verse-midnight)" }}>{ev.fact_count}</p>
                      <p className="text-[10px] text-muted-foreground">facts</p>
                    </div>
                  </div>
                  {/* Latest tracked attribute values */}
                  {Object.keys(ev.latest).length > 0 && (
                    <div className="mt-3 pt-3 border-t flex flex-wrap gap-2" style={{ borderColor: "var(--border)" }}>
                      {Object.entries(ev.latest).map(([attr, val]) => (
                        <span key={attr} className="text-[11px] px-2 py-0.5 rounded-lg border" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
                          <span className="font-semibold text-foreground">{attr}:</span> {String(val)}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* ── PROPS TAB ──────────────────────────────────────────────────── */}
      {activeTab === "props" && (
        <div className="flex flex-col gap-3">
          {liveProps.length === 0 ? (
            <EmptyState icon={Layers} title="No props extracted yet"
              description={isLive ? "No prop entities found — the engine may classify props differently. Check the Scenes tab." : "Upload a screenplay to extract prop data."} />
          ) : (
            liveProps.map((ev) => {
              const sceneCount = ev.scene_ids.length;
              const hasIssue = ev.conflict_count > 0;
              const statusColor = hasIssue ? "var(--verse-gold)" : ev.fact_count > 0 ? "var(--verse-emerald)" : "#64748B";
              const statusLabel = hasIssue ? "Flagged" : ev.fact_count > 0 ? "Tracked" : "Listed";
              return (
                <Card key={ev.entity.key}>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: "var(--verse-violet-light)" }}>
                      <Layers size={16} style={{ color: "var(--verse-violet)" }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-foreground">{ev.entity.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {sceneCount > 0
                          ? `In ${sceneCount} scene${sceneCount !== 1 ? "s" : ""}`
                          : "Scene data pending"}
                        {ev.fact_count > 0 ? ` · ${ev.fact_count} facts` : ""}
                      </p>
                    </div>
                    <span className="text-xs font-bold flex-shrink-0" style={{ color: statusColor }}>
                      {statusLabel}
                    </span>
                  </div>
                  {Object.keys(ev.latest).length > 0 && (
                    <div className="mt-3 pt-3 border-t flex flex-wrap gap-2" style={{ borderColor: "var(--border)" }}>
                      {Object.entries(ev.latest).map(([attr, val]) => (
                        <span key={attr} className="text-[11px] px-2 py-0.5 rounded-lg border" style={{ borderColor: "var(--border)", color: "var(--muted-foreground)" }}>
                          <span className="font-semibold text-foreground">{attr}:</span> {String(val)}
                        </span>
                      ))}
                    </div>
                  )}
                </Card>
              );
            })
          )}
          {/* Locations sub-section — shown inside the Props tab when present */}
          {locEntities.length > 0 && (
            <>
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wide mt-2 px-1">Locations</p>
              {locEntities.map((ev) => (
                <Card key={ev.entity.key}>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: "#EFF6FF" }}>
                      <Globe size={16} style={{ color: "#3B82F6" }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-foreground">{ev.entity.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {ev.scene_ids.length > 0 ? `${ev.scene_ids.length} scenes` : "Listed"}
                        {ev.fact_count > 0 ? ` · ${ev.fact_count} facts` : ""}
                      </p>
                    </div>
                  </div>
                </Card>
              ))}
            </>
          )}
        </div>
      )}

      {/* ── TIMELINE TAB ───────────────────────────────────────────────── */}
      {activeTab === "timeline" && (
        <div className="flex flex-col gap-2">
          {scenes.length === 0 ? (
            <EmptyState icon={Clock} title="No timeline yet" description="Upload a screenplay to generate the scene timeline." />
          ) : (
            <>
              <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--border)" }}>
                <div className="grid text-[11px] font-bold text-muted-foreground uppercase tracking-wide px-4 py-2.5 border-b"
                  style={{ gridTemplateColumns: "3rem 1fr 6rem 5rem 4rem", borderColor: "var(--border)", background: "var(--muted)" }}>
                  <span>#</span>
                  <span>Scene</span>
                  <span>Location</span>
                  <span>Time</span>
                  <span className="text-right">Score</span>
                </div>
                {scenes.map((sv, i) => {
                  const hasConflict = (sv.issue_count ?? 0) > 0;
                  return (
                    <div key={sv.scene_id ?? i}
                      className="grid items-center px-4 py-3 border-b last:border-0 hover:bg-muted/40 transition-colors text-sm"
                      style={{ gridTemplateColumns: "3rem 1fr 6rem 5rem 4rem", borderColor: "var(--border)" }}>
                      <span className="text-xs font-bold tabular-nums" style={{ color: "var(--verse-violet)" }}>
                        {sv.sequence || i + 1}
                      </span>
                      <div className="min-w-0 pr-2">
                        <p className="font-medium text-foreground truncate text-xs leading-tight">
                          {sv.slugline ?? sv.scene_id}
                        </p>
                        {sv.headline && (
                          <p className="text-[11px] text-muted-foreground truncate mt-0.5">{sv.headline}</p>
                        )}
                      </div>
                      <span className="text-[11px] text-muted-foreground truncate">
                        {sv.location ?? "—"}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {sv.time_of_day ?? "—"}
                      </span>
                      <div className="text-right">
                        {sv.score > 0 ? (
                          <span className="text-xs font-bold tabular-nums"
                            style={{ color: hasConflict ? "var(--verse-gold)" : "var(--verse-emerald)" }}>
                            {Math.round(sv.score)}%
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="text-[11px] text-muted-foreground text-right px-1">
                {scenes.length} scenes · ordered by screenplay sequence
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SceneTimeline({ projectId }: { projectId?: string }) {
  // Screenplay order comes from the engine's timeline, which is built from the
  // `sequence` each scene was ingested with — not from shooting order.
  const { scenes: liveScenes, overview, loading } = useSceneViews(projectId ?? null);
  const isLive = liveScenes.length > 0;
  const rows = isLive
    ? sceneViewsToRows(liveScenes).map((r, i) => ({ ...r, headline: liveScenes[i].headline }))
    : sceneList.map((s) => ({ ...s, headline: "" }));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Scene Timeline <DataSourceBadge live={isLive} /></span>}
        subtitle={
          overview
            ? `Screenplay order · ${overview.scenes_shot}/${overview.scenes_total} shot · avg score ${overview.average_scene_score}%`
            : loading ? "Loading the screenplay timeline…" : "Chronological scene order with continuity status."
        }
        actions={<Btn variant="secondary" icon={Filter} onClick={() => toast.info("Opening filter options…")}>Filter</Btn>}
      />
      <Card>
        <div className="flex flex-col gap-0">
          {rows.map((s, i) => {
            const sc = { Flagged: "var(--verse-red)", Logged: "var(--verse-emerald)", "In Progress": "var(--verse-violet)", Review: "var(--verse-gold)", Scheduled: "#CBD5E1" }[s.status] || "#CBD5E1";
            return (
              <div key={s.id} className="relative flex gap-4 group cursor-pointer" onClick={() => toast.info(`Opening ${s.scene}…`)}>
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full border-2 border-white mt-4 z-10" style={{ backgroundColor: sc }} />
                  {i < rows.length - 1 && <div className="w-px flex-1 mt-1" style={{ backgroundColor: "var(--border)" }} />}
                </div>
                <div className={`flex-1 p-3 rounded-xl mb-2 border transition-all group-hover:shadow-sm`} style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <span className="text-xs font-mono font-bold text-foreground">{s.scene}</span>
                      <span className="text-xs text-muted-foreground ml-2">{s.location}</span>
                      {s.headline && <p className="text-xs text-muted-foreground truncate">{s.headline}</p>}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-muted-foreground">{s.chars}</span>
                      {s.score > 0 && <ScorePill value={s.score} />}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

function AIAlerts({ onAIAction, projectId }: { onAIAction: (id: string, action: "accept" | "dismiss") => void; projectId?: string }) {
  const [liveRecs, setLiveRecs] = React.useState<Array<{ id: string; severity: "critical"|"warning"|"info"; scene: string; issue: string; confidence: number; suggestion: string; timestamp: string }> | null>(null);
  const [loading, setLoading] = React.useState(true);
  const scan = React.useCallback(() => {
    if (!projectId) { setLoading(false); return; }
    setLoading(true);
    apiContinuity.issues(projectId).then((issues) => {
      setLiveRecs(issues.map((i) => ({
        id: i.issue_id, severity: toDisplaySeverity(i.severity),
        scene: i.scene_id ?? "—", issue: i.explanation || i.attribute,
        confidence: Math.round(i.confidence * 100),
        suggestion: i.suggested_fix || "Review the flagged scene.",
        timestamp: "Just now",
      })));
    }).catch(() => setLiveRecs([])).finally(() => setLoading(false));
  }, [projectId]);
  React.useEffect(() => { scan(); }, [scan]);

  const alerts = liveRecs ?? [];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-red)" }}>Alerts</span></span>} subtitle="Real-time continuity alerts generated by the VERSE AI engine." actions={<Btn variant="primary" icon={RefreshCw} onClick={scan}>Scan Now</Btn>} />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Critical Alerts" value={alerts.filter(a => a.severity === "critical").length || "—"} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Warnings" value={alerts.filter(a => a.severity === "warning").length || "—"} icon={Zap} color="var(--verse-gold)" />
        <StatCard label="Total" value={alerts.length || "—"} icon={Brain} color="var(--verse-violet)" />
      </div>
      {loading ? (
        <div className="text-center py-12 text-sm text-muted-foreground">Scanning for alerts…</div>
      ) : alerts.length === 0 ? (
        <EmptyState icon={AlertTriangle} title="No alerts" description="Upload a screenplay and run analysis to detect continuity issues." />
      ) : (
        <div className="flex flex-col gap-3">
          {alerts.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
        </div>
      )}
    </div>
  );
}

function NarrativeProgression({ projectId }: { projectId?: string }) {
  const { scenes: liveScenes, overview } = useSceneViews(projectId ?? null);
  const isLive = liveScenes.length > 0;
  const total = overview?.scenes_total ?? 0;
  const shot = overview?.scenes_shot ?? 0;
  const progress = total > 0 ? Math.round((shot / total) * 100) : 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Narrative Progression" subtitle="Story structure and semantic progression analysis." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Scenes" value={total || "—"} icon={BookOpen} color="var(--verse-midnight)" />
        <StatCard label="Scenes Shot" value={shot || "—"} icon={Film} color="var(--verse-emerald)" />
        <StatCard label="Story Progress" value={total > 0 ? `${progress}%` : "—"} icon={TrendingUp} color="var(--verse-violet)" />
        <StatCard label="Avg. Score" value={overview?.average_scene_score != null ? `${overview.average_scene_score}%` : "—"} icon={Star} color="var(--verse-gold)" />
      </div>
      {isLive ? (
        <Card>
          <SectionTitle>Scene Progression</SectionTitle>
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1"><ProgressBar value={progress} color="var(--verse-midnight)" /></div>
            <span className="text-sm font-bold text-muted-foreground">{shot}/{total}</span>
          </div>
          <div className="flex flex-col gap-2">
            {liveScenes.map((s) => {
              const status = sceneStatus(s);
              const color = status === "Logged" ? "var(--verse-emerald)" : status === "Flagged" ? "var(--verse-red)" : "#CBD5E1";
              return (
                <div key={s.scene_id} className="flex items-center gap-3 p-2 rounded-lg border text-xs" style={{ borderColor: "var(--border)" }}>
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                  <span className="font-mono text-muted-foreground w-24 flex-shrink-0">{s.scene_id.replace(/_/g, " ")}</span>
                  <span className="flex-1 truncate text-foreground">{s.slugline ?? s.location ?? "—"}</span>
                  {s.score > 0 && <ScorePill value={Math.round(s.score)} />}
                </div>
              );
            })}
          </div>
        </Card>
      ) : (
        <EmptyState icon={TrendingUp} title="No screenplay yet" description="Upload a screenplay to visualise narrative progression." />
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONTINUITY SUPERVISOR PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ContinuitySupervisorOverview({ productionName, projectId }: { productionName: string; projectId?: string }) {
  const { entities: charEntities } = useEntityViews(projectId ?? null, { entityType: "character", attribute: "wears" });
  const { entities: propEntities } = useEntityViews(projectId ?? null, { entityType: "prop" });
  const { overview } = useSceneViews(projectId ?? null);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Supervisor" subtitle={`Asset continuity workspace for ${productionName}.`} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Costumes Tracked" value={charEntities?.length ?? "—"} icon={Eye} color="var(--verse-midnight)" />
        <StatCard label="Props Tracked" value={propEntities?.length ?? "—"} icon={Layers} color="var(--verse-violet)" />
        <StatCard label="Scenes Clean" value={overview?.scenes_clean ?? "—"} icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="Open Issues" value={overview?.issues_total ?? "—"} icon={AlertTriangle} color="var(--verse-gold)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {charEntities && charEntities.length > 0 ? (
          <Card>
            <SectionTitle>Costume Continuity</SectionTitle>
            {charEntities.slice(0, 6).map((view) => {
              const summary = summariseEntity(view, "wears");
              return (
                <div key={view.entity.key} className="flex items-center gap-3 py-2 border-b last:border-0" style={{ borderColor: "var(--border)" }}>
                  <div className="w-8 h-8 rounded-lg font-bold text-xs flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>{view.entity.name.split(" ").map((n: string) => n[0]).join("")}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground">{view.entity.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{summary.current !== "—" ? summary.current : "No costume data yet"}</p>
                  </div>
                  {summary.continuity > 0 && <ScorePill value={summary.continuity} />}
                </div>
              );
            })}
          </Card>
        ) : (
          <EmptyState icon={Eye} title="No costume data yet" description="Upload footage to compare costumes against the screenplay." />
        )}
        {propEntities && propEntities.length > 0 ? (
          <Card>
            <SectionTitle>Prop Continuity</SectionTitle>
            <div className="flex flex-col gap-3">
              {propEntities.slice(0, 4).map((view) => {
                const summary = summariseEntity(view);
                const stColor = summary.status === "Verified" ? "var(--verse-emerald)" : summary.status === "Issue" ? "var(--verse-gold)" : "#64748B";
                return (
                  <div key={view.entity.key} className="flex items-center gap-3 text-sm">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground">{view.entity.name}</p>
                      <p className="text-xs text-muted-foreground">{summary.scenes || "—"}</p>
                    </div>
                    <span className="text-xs font-bold flex-shrink-0" style={{ color: stColor }}>{summary.status === "Verified" ? "✓ Verified" : summary.status === "Issue" ? "⚠ Flagged" : "Pending"}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        ) : (
          <EmptyState icon={Layers} title="No prop data yet" description="Upload footage to track props against the screenplay." />
        )}
      </div>
    </div>
  );
}

/**
 * Collapse an entity's per-scene slots into the card summary these pages show.
 * Continuity score is the share of comparable slots that agreed — the honest
 * per-entity equivalent of the project score, and 0 when nothing has been shot.
 */
function summariseEntity(view: EntityView, attribute?: string) {
  const slots = attribute ? view.slots.filter((s) => s.attribute === attribute) : view.slots;
  const compared = slots.filter((s) => s.state === "match" || s.state === "conflict");
  const matched = slots.filter((s) => s.state === "match").length;
  const flagged = slots.filter((s) => s.flagged).length;
  const status = flagged > 0
    ? "Issue"
    : compared.length === 0 ? "Pending" : "Verified";
  return {
    slots,
    status,
    continuity: compared.length === 0 ? 0 : Math.round((matched / compared.length) * 100),
    scenes: [...new Set(slots.map((s) => s.scene_id).filter(Boolean))].join(", "),
    /** Most recent expected value — what the production currently believes. */
    current: attribute ? String(view.latest[attribute] ?? "—") : "—",
  };
}

function CostumeTracking({ projectId }: { projectId?: string }) {
  const mockCostumes = [
    { id: "c1", name: "Navy Blazer", character: "Elena Chen", scenes: "17, 18, 23, 24", status: "Verified", continuity: 97, slots: [] as SlotView[] },
    { id: "c2", name: "Charcoal Suit", character: "Marcus Reyes", scenes: "17, 24, 31", status: "Issue", continuity: 89, slots: [] as SlotView[] },
    { id: "c3", name: "White Lab Coat", character: "Dr. Helena Park", scenes: "18, 19", status: "Verified", continuity: 100, slots: [] as SlotView[] },
    { id: "c4", name: "Casual — Blue Jeans", character: "Elena Chen", scenes: "20, 21", status: "Pending", continuity: 0, slots: [] as SlotView[] },
  ];

  // Wardrobe state per character, straight from the engine's production memory.
  const { entities, loading } = useEntityViews(projectId ?? null, {
    entityType: "character",
    attribute: "wears",
  });
  const isLive = !!entities && entities.length > 0;
  const costumes = isLive
    ? entities.map((view) => {
        const summary = summariseEntity(view, "wears");
        return {
          id: view.entity.key,
          name: summary.current,
          character: view.entity.name,
          scenes: summary.scenes || "—",
          status: summary.status,
          continuity: summary.continuity,
          slots: summary.slots,
        };
      })
    : mockCostumes;

  const [showLog, setShowLog] = useState(false);
  const [newCostumeName, setNewCostumeName] = useState("");
  const sc = { Verified: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Issue: { c: "var(--verse-red)", bg: "#FEF2F2" }, Pending: { c: "#64748B", bg: "#F1F3F7" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Costume Tracking <DataSourceBadge live={isLive} /></span>}
        subtitle={loading ? "Loading wardrobe state from production memory…" : "Character costume continuity across all scenes — script expectation vs. what the footage shows."}
        actions={<Btn variant="primary" icon={Plus} onClick={() => setShowLog(true)}>Log Costume</Btn>}
      />
      {showLog && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Costume name (e.g. Red Evening Dress)…" value={newCostumeName} onChange={(e) => setNewCostumeName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newCostumeName.trim() && (toast.success(`"${newCostumeName}" logged.`), setNewCostumeName(""), setShowLog(false))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!newCostumeName.trim()) { toast.error("Enter a costume name."); return; } toast.success(`"${newCostumeName}" costume logged.`); setNewCostumeName(""); setShowLog(false); }}>Log</Btn>
          <Btn variant="secondary" onClick={() => { setShowLog(false); setNewCostumeName(""); }}>Cancel</Btn>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {costumes.map((c) => {
          const s = sc[c.status as keyof typeof sc];
          return (
            <Card key={c.id}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{c.name}</h3>
                  <p className="text-xs text-muted-foreground">{c.character}</p>
                </div>
                <StatusBadge label={c.status} color={s.c} bg={s.bg} />
              </div>
              <p className="text-xs text-muted-foreground mb-2">Appears in: <span className="text-foreground font-medium">Scenes {c.scenes}</span></p>
              {c.continuity > 0 && <>
                <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Continuity score</span><ScorePill value={c.continuity} /></div>
                <ProgressBar value={c.continuity} color={s.c} />
              </>}
              {/* Per-scene expected vs observed, with the source of each half. */}
              {c.slots.length > 0 && (
                <div className="mt-3 flex flex-col gap-1">
                  {c.slots.map((slot, i) => {
                    const state = slotStateLabel(slot);
                    return (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="font-mono text-muted-foreground w-24 flex-shrink-0 truncate">{slot.scene_id}</span>
                        <span className="text-foreground truncate">{slotValue(slot.expected)}</span>
                        <ArrowRight size={11} className="text-muted-foreground flex-shrink-0" />
                        <span className="text-foreground truncate">{slotValue(slot.observed)}</span>
                        <span className="ml-auto font-semibold flex-shrink-0" style={{ color: state.color }}>{state.label}</span>
                        {slot.observed && (
                          <span className="text-muted-foreground font-mono flex-shrink-0">{pct(slot.observed.confidence)}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <button className="flex-1 h-7 text-xs rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info("Opening costume detail…")}>View Detail</button>
                <button className="h-7 px-3 text-xs border rounded-lg hover:bg-muted text-muted-foreground" style={{ borderColor: "var(--border)" }} onClick={() => toast.info("Editing costume log…")}><Edit3 size={12} /></button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function PropTracking({ projectId }: { projectId?: string }) {
  const mockProps = [
    { id: "p1", name: "Vintage Rolex Watch", category: "Jewelry", character: "Marcus Reyes", scenes: "31A, 31E", status: "Issue", note: "Absent in shots 31B–31D" },
    { id: "p2", name: "Hero Coffee Mug", category: "Prop", character: "Elena Chen", scenes: "17, 18", status: "Verified", note: "Consistent across all shots" },
    { id: "p3", name: "Police Badge #4821", category: "ID / Badge", character: "Elena Chen", scenes: "17–25", status: "Verified", note: "Visible in all applicable scenes" },
    { id: "p4", name: "Leather Briefcase", category: "Prop", character: "Marcus Reyes", scenes: "17, 24", status: "Pending", note: "Not yet logged for Scene 31" },
    { id: "p5", name: "Crime Board Photos", category: "Set Dressing", character: "—", scenes: "17, 18", status: "Verified", note: "Photo order confirmed consistent" },
  ];

  // Prop state per scene from the engine: hand, condition, owner, and whether
  // the footage confirmed the script.
  const { entities, loading } = useEntityViews(projectId ?? null, { entityType: "prop" });
  const isLive = !!entities && entities.length > 0;
  const props = isLive
    ? entities.map((view) => {
        const summary = summariseEntity(view);
        const worst = summary.slots.find((s) => s.flagged) ?? summary.slots.find((s) => s.state === "conflict");
        const owner = view.latest.owner;
        return {
          id: view.entity.key,
          name: view.entity.name,
          category: view.attributes.join(" · ") || "Prop",
          character: owner ? String(owner) : "—",
          scenes: summary.scenes || "—",
          status: summary.status,
          note: worst
            ? `${worst.attribute}: script says ${slotValue(worst.expected)}, footage shows ${slotValue(worst.observed)}${worst.flagged ? "" : " (below the flagging threshold)"}`
            : summary.status === "Pending"
              ? "Awaiting footage for the scenes this prop appears in."
              : `${summary.slots.length} attribute(s) verified against footage.`,
        };
      })
    : mockProps;

  const [showLog, setShowLog] = useState(false);
  const [newPropName, setNewPropName] = useState("");
  const sc = { Verified: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Issue: { c: "var(--verse-red)", bg: "#FEF2F2" }, Pending: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Prop Tracking <DataSourceBadge live={isLive} /></span>}
        subtitle={loading ? "Loading prop state from production memory…" : "Prop inventory and scene continuity verification."}
        actions={<Btn variant="primary" icon={Plus} onClick={() => setShowLog(true)}>Log Prop</Btn>}
      />
      {showLog && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Prop name (e.g. Antique Clock)…" value={newPropName} onChange={(e) => setNewPropName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newPropName.trim() && (toast.success(`"${newPropName}" logged.`), setNewPropName(""), setShowLog(false))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!newPropName.trim()) { toast.error("Enter a prop name."); return; } toast.success(`"${newPropName}" prop logged.`); setNewPropName(""); setShowLog(false); }}>Log</Btn>
          <Btn variant="secondary" onClick={() => { setShowLog(false); setNewPropName(""); }}>Cancel</Btn>
        </div>
      )}
      <div className="flex flex-col gap-3">
        {props.map((p) => {
          const s = sc[p.status as keyof typeof sc];
          return (
            <Card key={p.id}>
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `color-mix(in srgb, ${s.c} 12%, white)` }}>
                  <Layers size={18} style={{ color: s.c }} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-bold text-foreground text-sm">{p.name}</h3>
                    <span className="text-xs text-muted-foreground">{p.category}</span>
                    <StatusBadge label={p.status} color={s.c} bg={s.bg} />
                  </div>
                  <p className="text-xs text-muted-foreground">Character: <span className="text-foreground">{p.character}</span> · Scenes: <span className="font-mono text-foreground">{p.scenes}</span></p>
                  <p className="text-xs text-muted-foreground mt-0.5">{p.note}</p>
                </div>
                <button className="text-muted-foreground hover:text-foreground" onClick={() => toast.info(`Editing ${p.name}…`)}><Edit3 size={14} /></button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function ContinuityVerification({ projectId }: { projectId?: string }) {
  const mockItems = [
    { id: "v1", scene: "Scene 17", check: "Costume verified against Scene 16 reference", done: true, issueId: null as string | null },
    { id: "v2", scene: "Scene 18", check: "Timeline logic reviewed and flagged", done: true, issueId: null },
    { id: "v3", scene: "Scene 23", check: "Costume colour inconsistency resolved", done: false, issueId: null },
    { id: "v4", scene: "Scene 24", check: "Prop inventory confirmed for exterior shoot", done: true, issueId: null },
    { id: "v5", scene: "Scene 31", check: "Marcus watch continuity resolved", done: false, issueId: null },
    { id: "v6", scene: "Scene 31", check: "Rooftop lighting continuity verified", done: false, issueId: null },
  ];

  // The checklist is generated from what the engine actually compared: every
  // slot where script and footage disagree, plus the ones still awaiting footage.
  const { entities, loading, refetch } = useEntityViews(projectId ?? null);
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});

  const liveItems = React.useMemo(() => {
    if (!entities) return [];
    const rows: Array<{ id: string; scene: string; check: string; done: boolean; issueId: string | null }> = [];
    for (const view of entities) {
      for (const slot of view.slots) {
        if (slot.state === "match" || slot.state === "observed_only") continue;
        const id = `${view.entity.key}:${slot.attribute}:${slot.scene_id}`;
        const check = slot.state === "conflict"
          ? `${view.entity.name} — ${slot.attribute.replace(/_/g, " ")}: script says "${slotValue(slot.expected)}", footage shows "${slotValue(slot.observed)}"${slot.flagged ? "" : " (low confidence)"}`
          : `${view.entity.name} — ${slot.attribute.replace(/_/g, " ")}: "${slotValue(slot.expected)}" not yet confirmed by footage`;
        rows.push({
          id,
          scene: slot.scene_id ?? "—",
          check,
          done: overrides[id] ?? slot.human_confirmed,
          issueId: slot.issue_id,
        });
      }
    }
    return rows;
  }, [entities, overrides]);

  const isLive = liveItems.length > 0;
  const [mockState, setMockState] = useState(mockItems);
  const items = isLive ? liveItems : mockState;

  /**
   * Ticking a generated check records the human decision on the engine's issue
   * (`resolve`) so the score is recalculated on the next analysis run. Checks
   * with no issue behind them are local-only.
   */
  const toggle = async (id: string) => {
    if (!isLive) {
      setMockState((prev) => prev.map((i) => i.id === id ? { ...i, done: !i.done } : i));
      toast.success("Verification updated.");
      return;
    }
    const item = liveItems.find((i) => i.id === id);
    const next = !(item?.done ?? false);
    setOverrides((prev) => ({ ...prev, [id]: next }));
    if (item?.issueId && projectId) {
      try {
        await apiContinuity.feedback(projectId, item.issueId, next ? "resolve" : "reopen");
        toast.success(next ? "Marked resolved — score will update on the next analysis." : "Reopened.");
        void refetch();
        return;
      } catch {
        toast.error("Could not record the decision with the engine.");
        return;
      }
    }
    toast.success("Verification updated.");
  };

  const done = items.filter((i) => i.done).length;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Continuity Verification <DataSourceBadge live={isLive} /></span>}
        subtitle={loading ? "Loading comparisons from the continuity engine…" : "Upload footage for a scene, then verify what the engine compared against the script."}
        actions={<Btn variant="primary" icon={Download} onClick={() => toast.info("Exporting verification report…")}>Export Report</Btn>}
      />
      <FootageUploadPanel projectId={projectId} onIngested={() => refetch()} />
      <Card>
        <div className="flex items-center gap-4 mb-4">
          <div>
            <p className="text-2xl font-black" style={{ fontFamily: "var(--font-display)", color: "var(--verse-midnight)" }}>{done}/{items.length}</p>
            <p className="text-xs text-muted-foreground">checks complete</p>
          </div>
          <div className="flex-1"><ProgressBar value={(done / items.length) * 100} color="var(--verse-emerald)" /></div>
          <span className="text-sm font-bold" style={{ color: "var(--verse-gold)" }}>{Math.round((done / items.length) * 100)}%</span>
        </div>
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <button key={item.id} onClick={() => toggle(item.id)} className="flex items-center gap-3 p-3 rounded-xl border text-left hover:shadow-sm transition-all" style={{ borderColor: item.done ? "rgba(5,150,105,0.2)" : "var(--border)", background: item.done ? "#F0FDF4" : "white" }}>
              <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${item.done ? "border-emerald-500 bg-emerald-500" : ""}`} style={{ borderColor: item.done ? "var(--verse-emerald)" : "var(--border)" }}>
                {item.done && <CheckCircle size={12} className="text-white" />}
              </div>
              <div className="flex-1">
                <p className={`text-sm ${item.done ? "line-through text-muted-foreground" : "text-foreground"}`}>{item.check}</p>
                <p className="text-xs text-muted-foreground font-mono">{item.scene}</p>
              </div>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

// TimelineTracking — Continuity Supervisor view.
// Tracks scene shooting order vs. narrative order so the continuity supervisor
// can spot gaps, overlaps, and out-of-sequence anomalies at a glance.
// Previously listed as a role feature in mockData but had no nav entry or page.
function TimelineTracking({ projectId }: { projectId?: string }) {
  const mockScenes = [
    { id: "s1", scene: "Scene 17", shootDay: "Day 1", narrative: "Monday Morning", location: "INT. Office", status: "Verified", continuity: 100 },
    { id: "s2", scene: "Scene 18", shootDay: "Day 1", narrative: "Monday Morning", location: "INT. Office", status: "Flagged", continuity: 72 },
    { id: "s3", scene: "Scene 23", shootDay: "Day 3", narrative: "Tuesday Afternoon", location: "INT. Diner", status: "Flagged", continuity: 81 },
    { id: "s4", scene: "Scene 24", shootDay: "Day 4", narrative: "Tuesday Evening", location: "EXT. Parking Lot", status: "Verified", continuity: 97 },
    { id: "s5", scene: "Scene 31", shootDay: "Day 6", narrative: "Wednesday Night", location: "EXT. Rooftop", status: "Pending", continuity: 0 },
    { id: "s6", scene: "Scene 34", shootDay: "Day 8", narrative: "Thursday Morning", location: "INT. Precinct", status: "Verified", continuity: 99 },
  ];

  // Screenplay sequence and per-scene score come from the engine. "Verified"
  // means shot and clean; "Pending" means no footage has been ingested yet.
  const { scenes: liveScenes } = useSceneViews(projectId ?? null);
  const isLive = liveScenes.length > 0;
  const scenes = isLive
    ? liveScenes.map((s) => {
        const status = sceneStatus(s);
        return {
          id: s.scene_id,
          scene: s.scene_id.replace(/_/g, " "),
          shootDay: `Seq ${s.sequence}`,
          narrative: s.time_of_day ?? "—",
          location: s.location ?? "—",
          status: status === "Logged" ? "Verified" : status === "Scheduled" ? "Pending" : "Flagged",
          continuity: s.has_footage ? Math.round(s.score) : 0,
        };
      })
    : mockScenes;

  const statusStyle = {
    Verified: { c: "var(--verse-emerald)", bg: "#ECFDF5" },
    Flagged:  { c: "var(--verse-red)",     bg: "#FEF2F2" },
    Pending:  { c: "#64748B",              bg: "#F1F3F7" },
  };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Timeline Tracking <DataSourceBadge live={isLive} /></span>}
        subtitle="Screenplay order vs. continuity state — spot gaps across the schedule."
        actions={<Btn variant="secondary" icon={Download} onClick={() => toast.promise(new Promise((r) => setTimeout(r, 800)), { loading: "Exporting timeline…", success: "Timeline exported.", error: "Failed." })}>Export</Btn>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Scenes Tracked" value={scenes.length} icon={Clock} color="var(--verse-midnight)" />
        <StatCard label="Verified" value={scenes.filter((s) => s.status === "Verified").length} icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="Flagged" value={scenes.filter((s) => s.status === "Flagged").length} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Pending" value={scenes.filter((s) => s.status === "Pending").length} icon={Clock} color="var(--verse-gold)" />
      </div>
      <Card>
        <SectionTitle>Scene Timeline</SectionTitle>
        <div className="flex flex-col gap-2">
          {scenes.map((s) => {
            const st = statusStyle[s.status as keyof typeof statusStyle];
            return (
              <div key={s.id} className="flex items-center gap-4 p-3 rounded-xl border text-sm" style={{ borderColor: "var(--border)", background: "white" }}>
                <div className="w-20 text-xs font-mono text-muted-foreground flex-shrink-0">{s.shootDay}</div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{s.scene}</p>
                  <p className="text-xs text-muted-foreground truncate">{s.location} · {s.narrative}</p>
                </div>
                {s.continuity > 0 && <ScorePill value={s.continuity} />}
                <StatusBadge label={s.status} color={st.c} bg={st.bg} />
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}



function ProductionMemory({ projectId }: { projectId?: string }) {
  const mockEvents = [
    { time: "Dec 12, 10:45", event: "AI detected timeline inconsistency in Scene 18", color: "var(--verse-violet)" },
    { time: "Dec 12, 09:30", event: "Scene 17 fully verified and logged to production memory", color: "var(--verse-emerald)" },
    { time: "Dec 11, 16:20", event: "Elena's costume reference photos uploaded — Scenes 23–25", color: "var(--verse-midnight)" },
    { time: "Dec 11, 14:05", event: "Marcus watch issue flagged by script supervisor", color: "var(--verse-red)" },
    { time: "Dec 10, 11:30", event: "Scene 24 logged with full prop manifest", color: "var(--verse-emerald)" },
    { time: "Dec 9, 09:00", event: "Production memory snapshot created — Week 3", color: "var(--verse-gold)" },
  ];

  // The engine's semantic memory: what it believes about each entity, where the
  // belief came from, and whether footage has confirmed it.
  const { entities } = useEntityViews(projectId ?? null);
  const { overview } = useSceneViews(projectId ?? null);
  const isLive = !!entities && entities.length > 0;

  const events = isLive
    ? entities.flatMap((view) =>
        view.slots.map((slot) => {
          const state = slotStateLabel(slot);
          const half = slot.observed ?? slot.expected;
          return {
            time: `${slot.scene_id ?? "—"}${half?.source ? ` · ${half.source}` : ""}${
              half?.source_reference ? ` · ${half.source_reference}` : ""
            }`,
            event: `${view.entity.name} — ${slot.attribute.replace(/_/g, " ")}: ${slotValue(slot.expected)}`
              + (slot.observed ? ` → observed ${slotValue(slot.observed)}` : "")
              + ` (${state.label})`,
            color: state.color,
          };
        }),
      ).slice(0, 40)
    : mockEvents;

  const facts = overview?.facts ?? 284;
  const entityCount = overview?.entities ?? 127;
  const verified = isLive
    ? entities.reduce((n, v) => n + v.slots.filter((s) => s.state === "match").length, 0)
    : 42;
  const comparable = isLive
    ? entities.reduce((n, v) => n + v.slots.filter((s) => s.state !== "unverified").length, 0)
    : 58;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2"><span><span style={{ color: "var(--verse-violet)" }}>Production</span> Memory</span> <DataSourceBadge live={isLive} /></span>}
        subtitle="Every belief the engine holds about this production, with the source that produced it."
        actions={<Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting memory log…")}>Export Log</Btn>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Facts Stored" value={facts} icon={Brain} color="var(--verse-violet)" />
        <StatCard label="Entities Tracked" value={entityCount} icon={Layers} color="var(--verse-midnight)" />
        <StatCard label="Confirmed by Footage" value={verified} icon={Sparkles} color="var(--verse-gold)" />
        <StatCard
          label="Memory Coverage"
          value={comparable > 0 ? `${Math.round((verified / comparable) * 100)}%` : "—"}
          subtext="verified share of what footage could confirm"
          icon={TrendingUp}
          color="var(--verse-emerald)"
        />
      </div>
      <Card>
        <SectionTitle>Semantic Memory</SectionTitle>
        <div className="flex flex-col gap-4">
          {events.map((e, i) => <ActivityItem key={i} icon={Brain} color={e.color} text={e.event} time={e.time} />)}
        </div>
        {events.length === 0 && (
          <EmptyState icon={Brain} title="Nothing in memory yet" description="Upload a screenplay and footage to populate production memory." />
        )}
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRODUCTION MANAGER PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ProductionManagerOverview({ productionName, projectId }: { productionName: string; projectId?: string }) {
  const { overview } = useSceneViews(projectId ?? null);
  const [liveTeam, setLiveTeam] = React.useState<TeamMember[] | null>(null);
  React.useEffect(() => {
    if (!projectId) return;
    apiProjects.getTeam(projectId).then(setLiveTeam).catch(() => {});
  }, [projectId]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Production Manager" subtitle={`Coordination workspace for ${productionName}.`} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Team Members" value={liveTeam?.length ?? 12} icon={Users} color="var(--verse-midnight)" />
        <StatCard label="Open Issues" value={overview?.issues_total ?? "—"} icon={CheckCircle} color="var(--verse-violet)" />
        <StatCard label="Scenes Shot" value={overview ? `${overview.scenes_shot}/${overview.scenes_total}` : "—"} icon={Calendar} color="var(--verse-emerald)" />
        <StatCard label="Avg. Score" value={overview?.average_scene_score != null ? `${overview.average_scene_score}%` : "—"} icon={BarChart3} color="var(--verse-gold)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Today's Schedule</SectionTitle>
          <div className="flex flex-col gap-2">
            {[
              { time: "07:00", event: "Crew call — Rooftop location", status: "done" },
              { time: "08:30", event: "Scene 31 — First shot", status: "done" },
              { time: "12:00", event: "Lunch break", status: "current" },
              { time: "13:30", event: "Scene 31 — Afternoon block (4 shots)", status: "upcoming" },
              { time: "17:00", event: "Wrap + continuity review", status: "upcoming" },
            ].map((s) => (
              <div key={s.time} className={`flex items-center gap-3 p-2 rounded-lg ${s.status === "current" ? "bg-violet-50" : ""}`}>
                <span className="text-xs font-mono w-12 flex-shrink-0 text-muted-foreground">{s.time}</span>
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.status === "done" ? "bg-emerald-500" : s.status === "current" ? "bg-violet-500" : "bg-gray-200"}`} />
                <span className={`text-sm ${s.status === "done" ? "line-through text-muted-foreground" : s.status === "current" ? "font-semibold text-foreground" : "text-foreground"}`}>{s.event}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle>Team Overview</SectionTitle>
          <div className="flex flex-col gap-3">
            {teamMembers.slice(0, 4).map((m) => {
              const sc = { online: "var(--verse-emerald)", away: "var(--verse-gold)", offline: "#CBD5E1" }[m.status];
              return (
                <div key={m.id} className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-8 h-8 rounded-full text-primary text-xs font-bold flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)" }}>{m.avatar}</div>
                    <div className="absolute bottom-0 right-0 w-2 h-2 rounded-full border-2 border-white" style={{ backgroundColor: sc }} />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-foreground">{m.name}</p>
                    <p className="text-xs text-muted-foreground">{m.role}</p>
                  </div>
                  <span className="text-xs text-muted-foreground">{m.lastActive}</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}

function TeamCollaboration() {
  const [msg, setMsg] = useState("");
  const [messages, setMessages] = useState([
    { id: "m1", author: "James K.", role: "Director", text: "Scene 31 going well — we'll wrap rooftop by 5pm.", time: "12:05" },
    { id: "m2", author: "Nina T.", role: "Script Supervisor", text: "Flagged a watch continuity issue in shots 31B–D. Marcus needs to check.", time: "12:08" },
    { id: "m3", author: "Sarah C.", role: "Producer", text: "Noted. Wardrobe team is on it. Great work catching that, Nina.", time: "12:10" },
  ]);
  const sendMsg = () => {
    if (!msg.trim()) return;
    setMessages((prev) => [...prev, { id: `m${prev.length + 1}`, author: "Alex Chen", role: "Production Manager", text: msg, time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }) }]);
    setMsg("");
    toast.success("Message sent.");
  };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Team Collaboration" subtitle="Production-wide team communication and coordination." />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Card>
            <SectionTitle>Production Chat</SectionTitle>
            <div className="flex flex-col gap-3 mb-4 max-h-72 overflow-y-auto">
              {messages.map((m) => (
                <div key={m.id} className={`flex gap-3 ${m.author === "Alex Chen" ? "flex-row-reverse" : ""}`}>
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>
                    {m.author.split(" ").map((n) => n[0]).join("")}
                  </div>
                  <div className={`flex-1 ${m.author === "Alex Chen" ? "items-end" : "items-start"} flex flex-col gap-0.5`}>
                    <div className="flex items-center gap-1.5">
                      <p className="text-xs font-bold text-foreground">{m.author}</p>
                      <p className="text-xs text-muted-foreground">{m.role} · {m.time}</p>
                    </div>
                    <div className={`px-3 py-2 rounded-xl text-sm max-w-[85%] ${m.author === "Alex Chen" ? "bg-primary text-primary-foreground" : ""}`} style={m.author !== "Alex Chen" ? { background: "var(--muted)" } : {}}>
                      {m.text}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={msg} onChange={(e) => setMsg(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendMsg()} placeholder="Type a message…" className="flex-1 h-9 px-3 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)", background: "white" }} />
              <button onClick={sendMsg} className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--primary)" }}><Send size={14} className="text-white" /></button>
            </div>
          </Card>
        </div>
        <Card>
          <SectionTitle>Task Assignments</SectionTitle>
          <div className="flex flex-col gap-3">
            {[
              { task: "Resolve watch continuity", person: "Nina T.", priority: "high" },
              { task: "Book catering — Jan 5", person: "Alex C.", priority: "medium" },
              { task: "Export Week 3 report", person: "Sarah C.", priority: "low" },
              { task: "Location scout — Act 3", person: "Tom R.", priority: "medium" },
            ].map((t, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full flex-shrink-0`} style={{ backgroundColor: t.priority === "high" ? "var(--verse-red)" : t.priority === "medium" ? "var(--verse-gold)" : "#CBD5E1" }} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">{t.task}</p>
                  <p className="text-xs text-muted-foreground">{t.person}</p>
                </div>
                <button className="text-xs text-primary hover:underline" onClick={() => toast.success(`Task assigned: "${t.task}"`)}>Open</button>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Scheduling() {
  const days = ["Mon Dec 16", "Tue Dec 17", "Wed Dec 18", "Thu Dec 19", "Fri Dec 20"];
  const schedule = [
    { day: 0, event: "Scene 31A–C · Rooftop · 6 hrs", color: "var(--verse-violet)" },
    { day: 1, event: "Scene 31D–F · Rooftop · 5 hrs", color: "var(--verse-violet)" },
    { day: 2, event: "Scene 32 · INT. Lobby · 7 hrs", color: "var(--verse-midnight)" },
    { day: 3, event: "Scene 33–34 · INT. Office · 6 hrs", color: "var(--verse-midnight)" },
    { day: 4, event: "Crew day off / edit review", color: "var(--verse-gold)" },
  ];
  const [showAdd, setShowAdd] = useState(false);
  const [newEvent, setNewEvent] = useState("");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Scheduling" subtitle="Production schedule and calendar management." actions={<>
        <Btn variant="secondary" icon={Download} onClick={() => toast.promise(new Promise((r) => setTimeout(r, 800)), { loading: "Exporting schedule…", success: "Schedule exported.", error: "Failed." })}>Export</Btn>
        <Btn variant="primary" icon={Plus} onClick={() => setShowAdd(true)}>Add Event</Btn>
      </>} />
      {showAdd && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Event description…" value={newEvent} onChange={(e) => setNewEvent(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newEvent.trim() && (toast.success(`Event added: "${newEvent}"`), setNewEvent(""), setShowAdd(false))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!newEvent.trim()) { toast.error("Enter an event description."); return; } toast.success(`Event added: "${newEvent}"`); setNewEvent(""); setShowAdd(false); }}>Add</Btn>
          <Btn variant="secondary" onClick={() => { setShowAdd(false); setNewEvent(""); }}>Cancel</Btn>
        </div>
      )}
      <Card>
        <SectionTitle>Week of December 16–20</SectionTitle>
        <div className="grid grid-cols-5 gap-2">
          {days.map((day, i) => (
            <div key={day} className="rounded-xl border p-3 hover:shadow-sm transition-all cursor-pointer" style={{ borderColor: i === 0 ? "rgba(124,58,237,0.3)" : "var(--border)", background: i === 0 ? "rgba(124,58,237,0.04)" : "white" }} onClick={() => toast.info(`Opening ${day} schedule…`)}>
              <p className="text-xs font-bold text-muted-foreground mb-2">{day}</p>
              <div className="h-20 rounded-lg p-2 text-xs text-white font-medium leading-snug" style={{ backgroundColor: schedule[i].color, fontSize: "11px" }}>
                {schedule[i].event}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function WorkspaceManagement() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Workspace Management" subtitle="Manage production workspace settings and access." />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Access Control</SectionTitle>
          <div className="flex flex-col gap-3">
            {teamMembers.map((m) => (
              <div key={m.id} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full text-xs font-bold flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>{m.avatar}</div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">{m.name}</p>
                  <p className="text-xs text-muted-foreground">{m.role}</p>
                </div>
                <select className="h-7 text-xs border rounded-lg px-2 focus:outline-none" style={{ borderColor: "var(--border)" }} onChange={() => toast.success("Access updated.")}>
                  <option>Editor</option><option>Viewer</option><option>Admin</option>
                </select>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle>Workspace Info</SectionTitle>
          <div className="flex flex-col gap-3 text-sm">
            {[
              { label: "Workspace Name", value: "VERSE — The Last Scene" },
              { label: "Production Type", value: "Feature Film" },
              { label: "Created", value: "Nov 12, 2024" },
              { label: "Storage Used", value: "4.2 GB / 50 GB" },
              { label: "Team Members", value: "12 active" },
            ].map((f) => (
              <div key={f.label} className="flex items-center justify-between border-b pb-2 last:border-0" style={{ borderColor: "var(--border)" }}>
                <span className="text-muted-foreground">{f.label}</span>
                <span className="font-semibold text-foreground">{f.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function ManagerReports() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Reports" subtitle="Production performance and continuity reports." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.loading("Generating new report…")}>Generate Report</Btn>} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { title: "Weekly Production Summary", date: "Dec 12, 2024", desc: "Scenes filmed, continuity scores, team activity, and AI insights for week 3.", icon: BarChart3, color: "var(--verse-midnight)" },
          { title: "Continuity Health Report", date: "Dec 12, 2024", desc: "Detailed breakdown of all continuity issues, resolutions, and AI recommendations.", icon: Brain, color: "var(--verse-violet)" },
          { title: "Budget Utilization", date: "Dec 11, 2024", desc: "Department-wise budget tracking, variance analysis, and forecast.", icon: TrendingUp, color: "var(--verse-gold)" },
          { title: "Team Performance Metrics", date: "Dec 10, 2024", desc: "Individual productivity, task completion rates, and availability overview.", icon: Users, color: "var(--verse-emerald)" },
        ].map((r) => (
          <Card key={r.title}>
            <div className="flex items-start gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `color-mix(in srgb, ${r.color} 12%, white)` }}>
                <r.icon size={18} style={{ color: r.color }} />
              </div>
              <div>
                <h3 className="font-bold text-foreground text-sm">{r.title}</h3>
                <p className="text-xs text-muted-foreground">{r.date}</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mb-3">{r.desc}</p>
            <div className="flex gap-2">
              <button className="flex-1 h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info(`Opening ${r.title}…`)}>View Report</button>
              <button className="h-8 px-3 text-xs border rounded-lg hover:bg-muted" style={{ borderColor: "var(--border)" }} onClick={() => toast.info("Downloading PDF…")}><Download size={12} /></button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DEPARTMENT MEMBER PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function DeptMemberOverview({ productionName }: { productionName: string }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="My Workspace" subtitle={`Your personal dashboard for ${productionName}.`} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="My Tasks" value={5} subtext="2 due today" icon={CheckCircle} color="var(--verse-midnight)" />
        <StatCard label="Notes Created" value={12} icon={FileText} color="var(--verse-violet)" />
        <StatCard label="Continuity Updates" value={3} icon={Brain} color="var(--verse-gold)" />
        <StatCard label="Messages" value={8} icon={MessageSquare} color="var(--verse-emerald)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Today's Tasks</SectionTitle>
          <div className="flex flex-col gap-2">
            {[
              { task: "Review Scene 31 costume continuity notes", done: false, priority: "high" },
              { task: "Upload reference photos for Scene 32", done: false, priority: "high" },
              { task: "Complete wardrobe inventory check", done: true, priority: "medium" },
              { task: "Attend continuity review at 17:00", done: false, priority: "medium" },
            ].map((t, i) => (
              <div key={i} className={`flex items-center gap-3 p-2 rounded-lg ${t.done ? "opacity-60" : ""}`}>
                <div className={`w-4 h-4 rounded border-2 flex-shrink-0 flex items-center justify-center ${t.done ? "bg-emerald-500 border-emerald-500" : ""}`} style={{ borderColor: t.done ? "var(--verse-emerald)" : "var(--border)" }}>
                  {t.done && <CheckCircle size={10} className="text-white" />}
                </div>
                <span className={`text-sm flex-1 ${t.done ? "line-through text-muted-foreground" : "text-foreground"}`}>{t.task}</span>
                <div className={`w-1.5 h-1.5 rounded-full`} style={{ backgroundColor: t.priority === "high" ? "var(--verse-red)" : "#CBD5E1" }} />
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <SectionTitle>Recent Updates</SectionTitle>
          <div className="flex flex-col gap-3">
            {[
              { text: "Nina T. flagged watch continuity in Scene 31", time: "12:08", color: "var(--verse-gold)" },
              { text: "New AI alert: costume discrepancy in Scene 23", time: "11:42", color: "var(--verse-violet)" },
              { text: "Scene 31 schedule updated — extends to 5pm", time: "09:15", color: "var(--verse-midnight)" },
            ].map((u, i) => <ActivityItem key={i} icon={Bell} color={u.color} text={u.text} time={u.time} />)}
          </div>
        </Card>
      </div>
    </div>
  );
}

function MyTasks() {
  const [showAdd, setShowAdd] = useState(false);
  const [newTask, setNewTask] = useState("");
  const [tasks, setTasks] = useState([
    { id: "t1", task: "Upload Scene 32 costume reference photos", due: "Today", priority: "high", done: false },
    { id: "t2", task: "Review Scene 31 continuity notes from script supervisor", due: "Today", priority: "high", done: false },
    { id: "t3", task: "Complete wardrobe inventory — Act 2 costumes", due: "Dec 13", priority: "medium", done: true },
    { id: "t4", task: "Attend 17:00 continuity review meeting", due: "Today", priority: "medium", done: false },
    { id: "t5", task: "Update prop inventory for Scene 33", due: "Dec 14", priority: "low", done: false },
  ]);
  const toggle = (id: string) => { setTasks((prev) => prev.map((t) => t.id === id ? { ...t, done: !t.done } : t)); toast.success("Task updated."); };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="My Tasks" subtitle="Your assigned tasks and deadlines." actions={<Btn variant="primary" icon={Plus} onClick={() => setShowAdd(true)}>Add Task</Btn>} />
      {showAdd && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Task description…" value={newTask} onChange={(e) => setNewTask(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newTask.trim() && (setTasks((p) => [{ id: `t${p.length + 1}`, task: newTask, due: "Today", priority: "medium", done: false }, ...p]), setNewTask(""), setShowAdd(false), toast.success("Task added."))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!newTask.trim()) { toast.error("Enter a task."); return; } setTasks((p) => [{ id: `t${p.length + 1}`, task: newTask, due: "Today", priority: "medium", done: false }, ...p]); setNewTask(""); setShowAdd(false); toast.success("Task added."); }}>Add</Btn>
          <Btn variant="secondary" onClick={() => { setShowAdd(false); setNewTask(""); }}>Cancel</Btn>
        </div>
      )}
      <div className="flex flex-col gap-2">
        {tasks.map((t) => (
          <Card key={t.id}>
            <div className="flex items-center gap-3">
              <button onClick={() => toggle(t.id)} className={`w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${t.done ? "bg-emerald-500 border-emerald-500" : "border-border hover:border-primary"}`}>
                {t.done && <CheckCircle size={12} className="text-white" />}
              </button>
              <div className="flex-1">
                <p className={`text-sm font-medium ${t.done ? "line-through text-muted-foreground" : "text-foreground"}`}>{t.task}</p>
                <p className="text-xs text-muted-foreground">Due: {t.due}</p>
              </div>
              <div className={`w-2 h-2 rounded-full flex-shrink-0`} style={{ backgroundColor: t.priority === "high" ? "var(--verse-red)" : t.priority === "medium" ? "var(--verse-gold)" : "#CBD5E1" }} />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Notes() {
  const [notes, setNotes] = useState([
    { id: "n1", title: "Scene 31 — Costume notes", body: "Elena wears the navy blazer (ref: S17-A). Marcus in charcoal suit. Watch issue flagged for shots B–D.", date: "Dec 12" },
    { id: "n2", title: "Rooftop shoot reminders", body: "Check morning light continuity. Jacket collar must stay up for Elena in all exterior shots.", date: "Dec 12" },
  ]);
  const [newNote, setNewNote] = useState(false);
  const [draft, setDraft] = useState({ title: "", body: "" });
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Notes" subtitle="Your personal production notes." actions={<Btn variant="primary" icon={Plus} onClick={() => setNewNote(true)}>New Note</Btn>} />
      {newNote && (
        <Card>
          <input placeholder="Note title…" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className="w-full h-9 px-3 rounded-lg border text-sm font-bold mb-2 focus:outline-none" style={{ borderColor: "var(--border)", background: "white" }} />
          <textarea placeholder="Write your note…" value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value })} rows={3} className="w-full px-3 py-2 rounded-lg border text-sm resize-none focus:outline-none mb-3" style={{ borderColor: "var(--border)", background: "white" }} />
          <div className="flex gap-2">
            <Btn variant="primary" onClick={() => { setNotes([{ id: `n${Date.now()}`, title: draft.title || "Untitled", body: draft.body, date: "Now" }, ...notes]); setNewNote(false); setDraft({ title: "", body: "" }); toast.success("Note saved."); }}>Save Note</Btn>
            <Btn variant="secondary" onClick={() => setNewNote(false)}>Cancel</Btn>
          </div>
        </Card>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {notes.map((n) => (
          <Card key={n.id}>
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-bold text-foreground">{n.title}</h3>
              <span className="text-xs text-muted-foreground">{n.date}</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">{n.body}</p>
            <div className="flex gap-2 mt-3">
              <button className="text-xs text-muted-foreground hover:text-foreground" onClick={() => toast.info("Editing note…")}><Edit3 size={13} /></button>
              <button className="text-xs text-muted-foreground hover:text-red-500" onClick={() => { setNotes(notes.filter((no) => no.id !== n.id)); toast.info("Note deleted."); }}><Trash2 size={13} /></button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ContinuityUpdates({ projectId }: { projectId?: string }) {
  const demoUpdates = [
    { id: "u1", title: "AI flagged costume discrepancy — Scene 23", time: "11:42", type: "ai", body: "Elena's jacket colour changes from navy to black between shots 23A and 23C. Wardrobe team notified.", resolved: false },
    { id: "u2", title: "Marcus watch continuity issue logged", time: "09:30", type: "flag", body: "Watch absent in shots 31B–31D. Script supervisor requesting resolution before afternoon shoot.", resolved: false },
    { id: "u3", title: "Scene 17 fully verified", time: "Yesterday", type: "verified", body: "All costume, prop, and timeline elements confirmed. Continuity score: 100%.", resolved: true },
  ];
  const [updates, setUpdates] = React.useState<Array<{ id: string; title: string; time: string; type: string; body: string; resolved: boolean }>>([]);
  const [isLive, setIsLive] = React.useState(false);
  const [submitting, setSubmitting] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!projectId) { setUpdates(demoUpdates); return; }
    apiContinuity.issues(projectId)
      .then((issues) => {
        setIsLive(true);
        setUpdates(
          issues.slice(0, 10).map((i) => ({
            id: i.issue_id,
            title: i.explanation || `${i.category}: ${i.attribute}`,
            time: "Live",
            type: i.status === "resolved" || i.status === "dismissed" ? "verified" : i.severity === "critical" ? "flag" : "ai",
            body: i.suggested_fix || i.explanation || "Review the flagged scene with your continuity supervisor.",
            resolved: i.status === "resolved" || i.status === "dismissed",
          }))
        );
      })
      .catch(() => { setUpdates(demoUpdates); });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const handleResolve = async (id: string) => {
    setSubmitting(id);
    // Optimistic UI update
    setUpdates((prev) => prev.map((u) => u.id === id ? { ...u, resolved: true, type: "verified" } : u));
    if (isLive && projectId) {
      try {
        await apiContinuity.feedback(projectId, id, "resolve");
        toast.success("Update submitted — issue marked resolved.");
      } catch {
        toast.error("Could not submit to the engine — is the backend running?");
        // Revert optimistic update on failure
        setUpdates((prev) => prev.map((u) => u.id === id ? { ...u, resolved: false, type: "ai" } : u));
      }
    } else {
      toast.success("Update submitted.");
    }
    setSubmitting(null);
  };

  const colors = { ai: "var(--verse-violet)", flag: "var(--verse-red)", verified: "var(--verse-emerald)" };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={<span className="inline-flex items-center gap-2">Continuity Updates <DataSourceBadge live={isLive} /></span>}
        subtitle="Latest continuity changes affecting your department."
      />
      {updates.length === 0 ? (
        <EmptyState icon={Brain} title="No updates yet" description="Continuity updates will appear after a screenplay is uploaded and analysed." />
      ) : (
        <div className="flex flex-col gap-3">
          {updates.map((u) => {
            const c = colors[u.type as keyof typeof colors] ?? "var(--verse-violet)";
            return (
              <Card key={u.id}>
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `color-mix(in srgb, ${c} 12%, white)` }}>
                    <Brain size={16} style={{ color: c }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-bold text-foreground text-sm">{u.title}</h3>
                      <span className="text-xs text-muted-foreground">{u.time}</span>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">{u.body}</p>
                    {!u.resolved && (
                      <button
                        disabled={submitting === u.id}
                        onClick={() => handleResolve(u.id)}
                        className="mt-2 text-xs font-semibold px-3 py-1 rounded-lg transition-colors disabled:opacity-50"
                        style={{ backgroundColor: "var(--verse-emerald)", color: "white" }}
                      >
                        {submitting === u.id ? "Submitting…" : "Mark Resolved"}
                      </button>
                    )}
                    {u.resolved && (
                      <span className="mt-2 inline-block text-xs font-semibold px-3 py-1 rounded-lg" style={{ backgroundColor: "#ECFDF5", color: "var(--verse-emerald)" }}>
                        Resolved
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Discussions() {
  const threads = [
    { id: "d1", title: "Scene 31 — Rooftop continuity check", author: "Nina T.", replies: 4, time: "1h ago", tag: "Continuity" },
    { id: "d2", title: "Act 2 costume reference photos needed", author: "Sarah C.", replies: 2, time: "3h ago", tag: "Wardrobe" },
    { id: "d3", title: "Location change for Scene 35?", author: "Tom R.", replies: 7, time: "Yesterday", tag: "General" },
  ];
  const [showNew, setShowNew] = useState(false);
  const [threadTitle, setThreadTitle] = useState("");
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Discussions" subtitle="Team discussion threads for the production." actions={<Btn variant="primary" icon={Plus} onClick={() => setShowNew(true)}>New Thread</Btn>} />
      {showNew && (
        <div className="rounded-2xl border p-4 flex items-center gap-3" style={{ borderColor: "var(--border)", background: "white" }}>
          <input autoFocus placeholder="Thread title…" value={threadTitle} onChange={(e) => setThreadTitle(e.target.value)} onKeyDown={(e) => e.key === "Enter" && threadTitle.trim() && (toast.success(`Thread created: "${threadTitle}"`), setThreadTitle(""), setShowNew(false))} className="flex-1 h-9 border rounded-lg px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/25" style={{ borderColor: "var(--border)" }} />
          <Btn variant="primary" onClick={() => { if (!threadTitle.trim()) { toast.error("Enter a thread title."); return; } toast.success(`Thread "${threadTitle}" created.`); setThreadTitle(""); setShowNew(false); }}>Create</Btn>
          <Btn variant="secondary" onClick={() => { setShowNew(false); setThreadTitle(""); }}>Cancel</Btn>
        </div>
      )}
      <div className="flex flex-col gap-3">
        {threads.map((t) => (
          <Card key={t.id}>
            <div className="flex items-start gap-3 cursor-pointer" onClick={() => toast.info(`Opening: ${t.title}`)}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ backgroundColor: "var(--verse-midnight-light)" }}>
                <MessageSquare size={16} style={{ color: "var(--verse-midnight)" }} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <h3 className="font-bold text-foreground text-sm">{t.title}</h3>
                  <span className="text-xs px-1.5 py-0.5 rounded-md" style={{ backgroundColor: "var(--muted)", color: "var(--muted-foreground)" }}>{t.tag}</span>
                </div>
                <p className="text-xs text-muted-foreground">{t.author} · {t.replies} replies · {t.time}</p>
              </div>
              <ChevronRight size={14} className="text-muted-foreground flex-shrink-0 mt-1" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// FILM STUDENT PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function FilmStudentOverview() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>Welcome to <span style={{ color: "var(--verse-violet)" }}>VERSE</span> Learning</span>} subtitle="Your AI-powered filmmaking education workspace." />
      <div
        className="rounded-2xl p-6 border text-white"
        style={{ background: "linear-gradient(135deg, #1D3461 0%, #2D1B69 100%)", borderColor: "transparent" }}
      >
        <GoldBadge>Getting Started</GoldBadge>
        <h2 className="text-xl font-black mt-3 mb-2" style={{ fontFamily: "var(--font-display)" }}>Complete your first continuity exercise</h2>
        <p className="text-white/70 text-sm mb-4">Learn how VERSE's AI engine tracks semantic continuity across a sample production.</p>
        <div className="mb-4">
          <div className="flex justify-between text-xs text-white/60 mb-1"><span>Progress</span><span>2/5 steps</span></div>
          <div className="h-2 rounded-full bg-white/20 overflow-hidden"><div className="h-full rounded-full bg-white" style={{ width: "40%" }} /></div>
        </div>
        <button onClick={() => toast.info("Opening tutorial step 3…")} className="flex items-center gap-2 font-semibold px-5 py-2.5 rounded-xl text-sm transition-all hover:-translate-y-0.5" style={{ backgroundColor: "var(--verse-gold)", color: "#1D3461" }}>
          Continue Learning <ArrowRight size={15} />
        </button>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Lessons Completed" value="8/20" icon={BookOpen} color="var(--verse-midnight)" />
        <StatCard label="Exercises Done" value={4} icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="XP Earned" value="420" icon={Star} color="var(--verse-gold)" />
        <StatCard label="Rank" value="Beginner" icon={Award} color="var(--verse-violet)" />
      </div>
    </div>
  );
}

function DemoWorkspace() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Demo Workspace" subtitle="Explore a pre-loaded sample production with real data." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { title: "The Last Scene", type: "Feature Film", desc: "A neo-noir mystery. Practice continuity tracking across 47 scenes with 3 main characters.", score: 94, locked: false },
          { title: "Short Film Demo", type: "Short Film", desc: "A 12-scene short film perfect for learning basic continuity workflows.", score: 99, locked: false },
          { title: "TV Episode Demo", type: "TV Series Ep.", desc: "Explore how VERSE handles episodic production tracking.", score: 0, locked: true },
        ].map((p) => (
          <Card key={p.title}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{p.title}</h3>
                <p className="text-xs text-muted-foreground">{p.type}</p>
              </div>
              {p.locked ? <StatusBadge label="Locked" color="#64748B" bg="#F1F3F7" /> : <StatusBadge label="Available" color="var(--verse-emerald)" bg="#ECFDF5" />}
            </div>
            <p className="text-sm text-muted-foreground mb-4">{p.desc}</p>
            {!p.locked && <div className="mb-3"><div className="flex justify-between text-xs text-muted-foreground mb-1"><span>Continuity Score</span><ScorePill value={p.score} /></div><ProgressBar value={p.score} color="var(--verse-emerald)" /></div>}
            <button className={`w-full h-9 text-sm font-bold rounded-xl ${p.locked ? "opacity-50 cursor-not-allowed" : ""}`} style={{ backgroundColor: p.locked ? "#F1F3F7" : "var(--verse-midnight-light)", color: p.locked ? "#64748B" : "var(--verse-midnight)" }} disabled={p.locked} onClick={() => !p.locked && toast.info(`Opening ${p.title} demo workspace…`)}>
              {p.locked ? <><Lock size={13} className="inline mr-1" />Unlock in Level 5</> : "Open Demo →"}
            </button>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Tutorials() {
  const tutorials = [
    { id: "l1", title: "What is Semantic Continuity?", duration: "8 min", level: "Beginner", done: true },
    { id: "l2", title: "How VERSE Reads a Screenplay", duration: "12 min", level: "Beginner", done: true },
    { id: "l3", title: "Logging Your First Scene", duration: "15 min", level: "Beginner", done: false },
    { id: "l4", title: "Understanding AI Recommendations", duration: "10 min", level: "Intermediate", done: false },
    { id: "l5", title: "Costume & Prop Continuity", duration: "18 min", level: "Intermediate", done: false },
    { id: "l6", title: "Advanced Knowledge Graphs", duration: "22 min", level: "Advanced", done: false },
  ];
  const levelColor = { Beginner: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Intermediate: { c: "var(--verse-violet)", bg: "var(--verse-violet-light)" }, Advanced: { c: "var(--verse-red)", bg: "#FEF2F2" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Tutorials" subtitle="Step-by-step lessons for mastering VERSE." />
      <div className="flex flex-col gap-3">
        {tutorials.map((t, i) => {
          const lc = levelColor[t.level as keyof typeof levelColor];
          return (
            <Card key={t.id}>
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${t.done ? "bg-emerald-500" : ""}`} style={!t.done ? { backgroundColor: "var(--verse-midnight-light)" } : {}}>
                  {t.done ? <CheckCircle size={18} className="text-white" /> : <span className="text-sm font-black" style={{ color: "var(--verse-midnight)", fontFamily: "var(--font-mono)" }}>{String(i + 1).padStart(2, "0")}</span>}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className={`text-sm font-bold ${t.done ? "text-muted-foreground line-through" : "text-foreground"}`}>{t.title}</p>
                    <StatusBadge label={t.level} color={lc.c} bg={lc.bg} />
                  </div>
                  <p className="text-xs text-muted-foreground">{t.duration}</p>
                </div>
                <button className="h-8 px-3 text-xs font-bold rounded-lg" style={{ backgroundColor: t.done ? "#F1F3F7" : "var(--verse-midnight-light)", color: t.done ? "#64748B" : "var(--verse-midnight)" }} onClick={() => toast.info(t.done ? "Lesson already complete." : `Opening: ${t.title}`)}>
                  {t.done ? "Revisit" : "Start →"}
                </button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function SampleProductions() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Sample Productions" subtitle="Explore real-world film production examples with VERSE AI analysis." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { title: "Noir Detective Film", genre: "Film Noir", scenes: 47, chars: 3, lesson: "Complex character continuity tracking", score: 94 },
          { title: "Nature Documentary", genre: "Documentary", scenes: 18, chars: 0, lesson: "Location and environmental continuity", score: 99 },
          { title: "Romantic Comedy", genre: "Comedy", scenes: 62, chars: 6, lesson: "High-character-count production management", score: 88 },
          { title: "Action Short", genre: "Short Film", scenes: 12, chars: 2, lesson: "Fast-paced continuity with multiple takes", score: 96 },
        ].map((p) => (
          <Card key={p.title}>
            <h3 className="font-black text-foreground mb-0.5" style={{ fontFamily: "var(--font-display)" }}>{p.title}</h3>
            <p className="text-xs text-muted-foreground mb-3">{p.genre} · {p.scenes} scenes · {p.chars > 0 ? `${p.chars} characters` : "No main characters"}</p>
            <div className="p-2 rounded-lg mb-3" style={{ backgroundColor: "var(--verse-violet-light)" }}>
              <p className="text-xs font-semibold" style={{ color: "var(--verse-violet)" }}>Learning focus: {p.lesson}</p>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground mb-1"><span>AI Continuity Score</span><ScorePill value={p.score} /></div>
            <ProgressBar value={p.score} color="var(--verse-emerald)" />
            <button className="w-full h-8 text-xs font-bold rounded-lg mt-3" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info(`Exploring: ${p.title}`)}>Explore Sample →</button>
          </Card>
        ))}
      </div>
    </div>
  );
}

function InteractiveLearning() {
  const [quizAnswer, setQuizAnswer] = useState<string | null>(null);
  const exercises = [
    { id: "e1", title: "Spot the Continuity Error", type: "Quiz", xp: 50, done: true },
    { id: "e2", title: "Log a Costume Detail", type: "Exercise", xp: 30, done: false },
    { id: "e3", title: "Identify AI Recommendation", type: "Quiz", xp: 40, done: false },
    { id: "e4", title: "Build a Scene Timeline", type: "Exercise", xp: 60, done: false },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Interactive Learning" subtitle="Hands-on exercises to build your continuity skills." />
      <Card>
        <SectionTitle><span>Active Exercise — Spot the Error</span></SectionTitle>
        <div className="p-4 rounded-xl mb-4" style={{ backgroundColor: "var(--verse-midnight-light)" }}>
          <p className="text-sm font-semibold text-foreground mb-2">Scene 18 — Elena and Dr. Park in the Office</p>
          <p className="text-sm text-muted-foreground">Elena is wearing a <span className="font-bold text-foreground">navy blazer</span> throughout Scene 17. In Scene 18, she appears in a <span className="font-bold text-foreground">dark charcoal jacket</span> in shot 18B. Which continuity element is incorrect?</p>
        </div>
        <div className="flex flex-col gap-2 mb-4">
          {["Timeline continuity", "Costume continuity", "Dialogue continuity", "Prop continuity"].map((opt) => (
            <button key={opt} onClick={() => { setQuizAnswer(opt); if (opt === "Costume continuity") toast.success("Correct! Costume continuity error detected. +40 XP"); else toast.error("Not quite. Try again!"); }}
              className="p-3 rounded-xl border text-sm font-medium text-left transition-all hover:shadow-sm"
              style={{ borderColor: quizAnswer === opt ? (opt === "Costume continuity" ? "var(--verse-emerald)" : "var(--verse-red)") : "var(--border)", background: quizAnswer === opt ? (opt === "Costume continuity" ? "#ECFDF5" : "#FEF2F2") : "white" }}>
              {opt}
            </button>
          ))}
        </div>
      </Card>
      <div className="flex flex-col gap-3">
        {exercises.map((e) => (
          <Card key={e.id}>
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${e.done ? "bg-emerald-500" : ""}`} style={!e.done ? { backgroundColor: "var(--verse-midnight-light)" } : {}}>
                {e.done ? <CheckCircle size={16} className="text-white" /> : <Target size={16} style={{ color: "var(--verse-midnight)" }} />}
              </div>
              <div className="flex-1">
                <p className={`text-sm font-bold ${e.done ? "text-muted-foreground line-through" : "text-foreground"}`}>{e.title}</p>
                <p className="text-xs text-muted-foreground">{e.type} · +{e.xp} XP</p>
              </div>
              <button disabled={e.done} className={`h-8 px-3 text-xs font-bold rounded-lg ${e.done ? "opacity-50 cursor-not-allowed" : ""}`} style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => !e.done && toast.info(`Opening: ${e.title}`)}>
                {e.done ? "Done" : "Start →"}
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SHARED SETTINGS PAGE
// ═══════════════════════════════════════════════════════════════════════════════

function SettingsPage() {
  const [name, setName] = useState("Alex Chen");
  const [notif, setNotif] = useState(true);
  const [ai, setAi] = useState(true);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" subtitle="Manage your account preferences and notifications." />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Profile</SectionTitle>
          <div className="flex flex-col gap-4">
            <div><label className="text-sm font-semibold text-foreground block mb-1.5">Display Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full h-10 px-3 rounded-lg border text-sm focus:outline-none" style={{ borderColor: "var(--border)", background: "white" }} /></div>
            <div><label className="text-sm font-semibold text-foreground block mb-1.5">Email</label>
              <input value="alex@studioproductions.com" readOnly className="w-full h-10 px-3 rounded-lg border text-sm opacity-60" style={{ borderColor: "var(--border)", background: "white" }} /></div>
            <Btn variant="primary" onClick={() => toast.success("Profile updated.")}>Save Profile</Btn>
          </div>
        </Card>
        <Card>
          <SectionTitle>Preferences</SectionTitle>
          <div className="flex flex-col gap-4">
            {[
              { label: "AI Recommendations", desc: "Show AI suggestions in my dashboard.", val: ai, set: setAi },
              { label: "Email Notifications", desc: "Receive daily production summaries.", val: notif, set: setNotif },
            ].map((s) => (
              <div key={s.label} className="flex items-center justify-between">
                <div><p className="text-sm font-semibold text-foreground">{s.label}</p><p className="text-xs text-muted-foreground">{s.desc}</p></div>
                <button onClick={() => { s.set(!s.val); toast.success(`${s.label} ${!s.val ? "enabled" : "disabled"}.`); }} className={`relative w-10 h-5 rounded-full transition-all ${s.val ? "bg-primary" : "bg-muted"}`}>
                  <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${s.val ? "left-5" : "left-0.5"}`} />
                </button>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DASHBOARD CONTENT ROUTER
// ═══════════════════════════════════════════════════════════════════════════════

function DashboardContent({
  userRole, productionName, onAIAction, activeNav, projectId, userName, onProjectChange,
}: {
  userRole: UserRole; productionName: string;
  onAIAction: (id: string, action: "accept" | "dismiss") => void;
  activeNav: string;
  projectId?: string;
  userName?: string;
  onProjectChange?: (id: string) => void;
}) {
  // Settings page is shared across all roles
  if (activeNav === "Settings") return <SettingsPage />;

  switch (userRole) {
    case "producer":
      switch (activeNav) {
        case "Productions": return <ProducerProductions onOpenProject={onProjectChange} />;
        case "Team": return <ProducerTeam />;
        case "Continuity Reports": return <ProducerContinuityReports projectId={projectId} />;
        case "Analytics": return <ProducerAnalytics projectId={projectId} />;
        case "AI Insights": return <ProducerAIInsights projectId={projectId} />;
        case "Workspace": return <ProducerWorkspace />;
        default: return <ProducerOverview productionName={productionName} onAIAction={onAIAction} projectId={projectId} userName={userName} />;
      }

    case "director":
      switch (activeNav) {
        case "Scene Tracking": return <DirectorSceneTracking projectId={projectId} />;
        case "Characters": return <DirectorCharacters projectId={projectId} />;
        case "Production Timeline": return <DirectorTimeline projectId={projectId} />;
        case "AI Recommendations": return <DirectorAIRecs onAIAction={onAIAction} projectId={projectId} />;
        case "Semantic Memory": return <DirectorSemanticMemory projectId={projectId} />;
        default: return <DirectorOverview productionName={productionName} onAIAction={onAIAction} projectId={projectId} />;
      }

    case "script-supervisor":
      switch (activeNav) {
        case "Continuity Tracking": return <ContinuityTracking projectId={projectId} />;
        case "Screenplay Analysis": return <ScreenplayAnalysis projectId={projectId} />;
        case "Scene Timeline": return <SceneTimeline projectId={projectId} />;
        case "AI Alerts": return <AIAlerts onAIAction={onAIAction} projectId={projectId} />;
        case "Narrative Progression": return <NarrativeProgression projectId={projectId} />;
        default: return <ScriptSupervisorOverview productionName={productionName} onAIAction={onAIAction} projectId={projectId} />;
      }

    case "continuity-supervisor":
      switch (activeNav) {
        case "Costume Tracking": return <CostumeTracking projectId={projectId} />;
        case "Prop Tracking": return <PropTracking projectId={projectId} />;
        // Route for the previously missing "Timeline Tracking" nav item.
        case "Timeline Tracking": return <TimelineTracking projectId={projectId} />;
        case "Continuity Verification": return <ContinuityVerification projectId={projectId} />;
        case "Production Memory": return <ProductionMemory projectId={projectId} />;
        default: return <ContinuitySupervisorOverview productionName={productionName} projectId={projectId} />;
      }

    case "production-manager":
      switch (activeNav) {
        case "Team Collaboration": return <TeamCollaboration />;
        case "Scheduling": return <Scheduling />;
        case "Workspace Management": return <WorkspaceManagement />;
        case "Reports": return <ManagerReports />;
        default: return <ProductionManagerOverview productionName={productionName} projectId={projectId} />;
      }

    case "department-member":
      switch (activeNav) {
        case "My Tasks": return <MyTasks />;
        case "Notes": return <Notes />;
        case "Continuity Updates": return <ContinuityUpdates projectId={projectId} />;
        case "Discussions": return <Discussions />;
        default: return <DeptMemberOverview productionName={productionName} />;
      }

    case "film-student":
      switch (activeNav) {
        case "Demo Workspace": return <DemoWorkspace />;
        case "Tutorials": return <Tutorials />;
        case "Sample Productions": return <SampleProductions />;
        case "Interactive Learning": return <InteractiveLearning />;
        default: return <FilmStudentOverview />;
      }

    default:
      return <ProducerOverview productionName={productionName} onAIAction={onAIAction} />;
  }
}

// ─── Main Dashboard Page ───────────────────────────────────────────────────────

export default function DashboardPage({
  userRole, productionName, userName = "Alex Chen", onSignOut,
}: DashboardPageProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeNav, setActiveNav] = useState("Overview");
  const [currentRole, setCurrentRole] = useState<UserRole>(userRole);
  const [isAIModalOpen, setIsAIModalOpen] = useState(false);
  // Full project list + active project selection
  const [projectList, setProjectList] = React.useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>(undefined);

  React.useEffect(() => {
    apiProjects.list()
      .then((list) => {
        setProjectList(list);
        if (list.length > 0 && !activeProjectId) setActiveProjectId(list[0].id);
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Switch production — re-fetch the project list so stats are fresh, then
  // switch the active id and navigate back to Overview for the new context.
  const handleProjectChange = (id: string) => {
    setActiveProjectId(id);
    setActiveNav("Overview");
    apiProjects.list().then(setProjectList).catch(() => {});
  };

  // handleAIAction — posts the human decision to POST /continuity/feedback so
  // the engine persists the accept/dismiss, adjusts the issue status, and
  // refreshes scores on the next analyse() call.
  // Falls back to a toast-only response if the backend is offline (demo mode).
  const handleAIAction = async (id: string, action: "accept" | "dismiss") => {
    if (activeProjectId) {
      try {
        await apiContinuity.feedback(
          activeProjectId,
          id,
          action === "accept" ? "confirm" : "dismiss",
        );
      } catch {
        // Backend offline — fall through to toast only (demo mode unchanged)
      }
    }
    if (action === "accept") toast.success("AI recommendation accepted. Continuity log updated.");
    else toast.info("Recommendation dismissed.");
  };

  // After a new workspace is created in ProducerOverview, refresh the list
  const handleProjectCreated = () => {
    apiProjects.list()
      .then((list) => {
        setProjectList(list);
        if (list.length > 0) setActiveProjectId(list[list.length - 1].id);
      })
      .catch(() => {});
  };

  const handleSignOut = () => {
    toast.success("Signed out successfully. See you next production!");
    setTimeout(onSignOut, 700);
  };

  const activeProductionName =
    projectList.find((p) => p.id === activeProjectId)?.name ?? productionName;

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <AIAnalysisModal isOpen={isAIModalOpen} onClose={() => setIsAIModalOpen(false)} projectId={activeProjectId} />
      {isSidebarOpen && <div className="lg:hidden fixed inset-0 bg-foreground/25 backdrop-blur-sm z-30" onClick={() => setIsSidebarOpen(false)} />}

      <DashboardSidebar
        userRole={currentRole}
        productionName={activeProductionName}
        userName={userName}
        isOpen={isSidebarOpen}
        activeNav={activeNav}
        onNavSelect={(label) => { setActiveNav(label); setIsSidebarOpen(false); }}
        onSignOut={handleSignOut}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <DashboardTopNav
          productionName={activeProductionName}
          onMobileMenuToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          activeRole={currentRole}
          onRoleChange={(role) => { setCurrentRole(role); setActiveNav("Overview"); }}
          onRunAIAnalysis={() => setIsAIModalOpen(true)}
          projects={projectList}
          activeProjectId={activeProjectId}
          onProjectChange={handleProjectChange}
        />
        <main className="flex-1 overflow-y-auto p-5 md:p-6" style={{ background: "linear-gradient(180deg, #F0EEFF 0%, #F5F3FF 100%)" }}>
          <div className="max-w-6xl mx-auto">
            <DashboardContent
              userRole={currentRole}
              productionName={activeProductionName}
              onAIAction={handleAIAction}
              activeNav={activeNav}
              projectId={activeProjectId}
              userName={userName}
              onProjectChange={handleProjectChange}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
