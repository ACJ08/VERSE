// Dashboard Page — Complete role-based workspace for VERSE.
// Every sidebar nav item renders a dedicated, fully interactive page.
// Roles: producer, director, script-supervisor, continuity-supervisor,
//        production-manager, department-member, film-student

import { useState } from "react";
import { toast } from "sonner";
import {
  Film, Brain, BarChart3, Users, Settings, Bell, Search, ChevronDown,
  Menu, AlertTriangle, CheckCircle, Clock, TrendingUp, Layers,
  FileText, Zap, Eye, MessageSquare, Home, LogOut, ArrowRight,
  BookOpen, Sparkles, ChevronRight, MoreHorizontal, Star,
  Plus, Download, Upload, RefreshCw, X, Calendar,
  Hash, Target, Award, Filter, Edit3,
  Trash2, Send, Globe, Lock, GitBranch,
} from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line,
} from "recharts";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import verseLogo from "@/imports/VERSE_LOGO_2.png";
import {
  mockProductions, continuityHealthData, sceneTimelineData,
  aiRecommendations, teamMembers, characters,
  userRoles, type UserRole,
} from "@/app/data/mockData";

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
  title: React.ReactNode; subtitle?: string; actions?: React.ReactNode;
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

// ─── AI Analysis Modal ─────────────────────────────────────────────────────────

function AIAnalysisModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [phase, setPhase] = useState<"loading" | "done">("loading");
  const [stepIndex, setStepIndex] = useState(0);

  const processingSteps = [
    { label: "Parsing screenplay semantic structure…", duration: 700 },
    { label: "Analyzing scene continuity vectors…", duration: 800 },
    { label: "Cross-referencing character states…", duration: 900 },
    { label: "Comparing wardrobe consistency logs…", duration: 700 },
    { label: "Detecting continuity discrepancies…", duration: 800 },
    { label: "Building production knowledge graph…", duration: 900 },
    { label: "Generating explainable AI recommendations…", duration: 700 },
  ];

  const runAnalysis = () => {
    setPhase("loading");
    setStepIndex(0);
    let currentStep = 0;
    const runNextStep = () => {
      if (currentStep >= processingSteps.length) { setPhase("done"); return; }
      setStepIndex(currentStep);
      setTimeout(() => { currentStep++; runNextStep(); }, processingSteps[currentStep].duration);
    };
    runNextStep();
  };

  if (!isOpen) return null;

  const mockResults = [
    { severity: "critical" as const, scene: "Scene 18", issue: "Timeline inconsistency: references 'Tuesday morning' but Scene 17 established 'Monday evening'.", confidence: 99 },
    { severity: "warning" as const, scene: "Scene 23", issue: "Elena's jacket changes from navy to black between shots 23A and 23C.", confidence: 96 },
    { severity: "warning" as const, scene: "Scene 31", issue: "Marcus's watch absent in shots 31B–31D but present in 31A and 31E.", confidence: 89 },
  ];

  if (phase === "loading" && stepIndex === 0 && isOpen) {
    setTimeout(() => runAnalysis(), 50);
  }

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
              <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>Semantic Continuity Engine · IBM watsonx</p>
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
                <p className="text-xs text-muted-foreground mt-1">The Last Scene · 47 scenes · 3 characters</p>
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
                <GoldBadge>3 issues found</GoldBadge>
              </div>
              {mockResults.map((result) => {
                const colors = {
                  critical: { color: "var(--verse-red)", bg: "#FEF2F2", label: "Critical" },
                  warning: { color: "var(--verse-gold)", bg: "var(--verse-gold-light)", label: "Warning" },
                };
                const c = colors[result.severity];
                return (
                  <div key={result.scene} className="p-4 rounded-xl border" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2 mb-2">
                      <StatusBadge label={c.label} color={c.color} bg={c.bg} />
                      <span className="text-xs font-mono text-muted-foreground">{result.scene}</span>
                      <span className="ml-auto text-xs font-bold text-primary">{result.confidence}%</span>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">{result.issue}</p>
                  </div>
                );
              })}
              <button
                onClick={() => { onClose(); toast.success("Analysis report saved to Continuity Reports."); }}
                className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-xl hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
              >
                Save Report <Download size={15} />
              </button>
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
        <div className="flex items-center gap-3 mb-3">
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
}: {
  productionName: string; onMobileMenuToggle: () => void;
  activeRole: UserRole; onRoleChange: (r: UserRole) => void;
  onRunAIAnalysis: () => void;
}) {
  const [showRoleDropdown, setShowRoleDropdown] = useState(false);
  const [notifCount, setNotifCount] = useState(4);
  const [searchVal, setSearchVal] = useState("");
  const currentRoleLabel = userRoles.find((r) => r.id === activeRole)?.title ?? "Role";

  return (
    <header className="h-16 border-b flex items-center gap-4 px-5 flex-shrink-0" style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.9)" }}>
      <button className="lg:hidden text-muted-foreground hover:text-foreground transition-colors" onClick={onMobileMenuToggle}>
        <Menu size={20} />
      </button>

      <div className="flex items-center gap-2 text-sm text-muted-foreground min-w-0">
        <span className="font-semibold text-foreground truncate">{productionName}</span>
        <ChevronRight size={13} className="flex-shrink-0" />
        <span className="hidden sm:block">Dashboard</span>
      </div>

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

      <div className="relative">
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

function ProducerOverview({ productionName, onAIAction }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Good morning, Alex."
        subtitle={`Production intelligence summary for ${productionName}.`}
        actions={<>
          <Btn variant="secondary" icon={Download} onClick={() => toast.info("Generating production report…")}>Export Report</Btn>
          <Btn variant="primary" icon={Plus} onClick={() => toast.success("New production workspace created!")}>New Production</Btn>
        </>}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Active Productions" value={3} icon={Film} color="var(--verse-midnight)" />
        <StatCard label="Scenes Logged" value="34/47" subtext="72% complete" icon={FileText} color="var(--verse-emerald)" />
        <StatCard label="Continuity Issues" value={4} subtext="2 critical" icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Team Members" value={12} subtext="8 active today" icon={Users} color="var(--verse-violet)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card>
          <SectionTitle><span>Continuity Health</span></SectionTitle>
          <p className="text-xs text-muted-foreground mb-2">Semantic accuracy score</p>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-4xl font-black" style={{ fontFamily: "var(--font-display)", color: "var(--verse-gold)" }}>94%</span>
            <span className="text-xs text-muted-foreground">↑ 2% this week</span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <RadarChart data={continuityHealthData}>
              <PolarGrid key="polar-grid" stroke="#D9D5F2" />
              <PolarAngleAxis key="polar-angle" dataKey="subject" tick={{ fontSize: 10, fill: "#5A6A85" }} />
              <Radar key="radar-score" name="Score" dataKey="score" stroke="var(--verse-midnight)" fill="var(--verse-midnight)" fillOpacity={0.12} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="lg:col-span-2">
          <SectionTitle action={<button className="text-xs text-primary font-semibold hover:underline" onClick={() => toast.info("Opening all productions…")}>View all</button>}>Active Productions</SectionTitle>
          <div className="flex flex-col gap-3">
            {mockProductions.map((prod) => {
              const sc = { "In Production": { c: "var(--verse-emerald)", bg: "#ECFDF5" }, "Pre-Production": { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" }, "Post-Production": { c: "#0F62FE", bg: "#EFF6FF" }, Completed: { c: "#64748B", bg: "#F1F3F7" } }[prod.status] || { c: "#64748B", bg: "#F1F3F7" };
              return (
                <div key={prod.id} className="flex items-center gap-3 p-3 rounded-xl border hover:shadow-sm transition-all cursor-pointer" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Opening ${prod.title}…`)}>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-semibold text-foreground truncate" style={{ fontFamily: "var(--font-display)" }}>{prod.title}</p>
                      <StatusBadge label={prod.status} color={sc.c} bg={sc.bg} />
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1.5">
                      <span>{prod.type}</span><span>·</span><span>{prod.scenesLogged}/{prod.scenesTotal} scenes</span>
                      <span>·</span><ScorePill value={prod.continuityScore} />
                    </div>
                    <ProgressBar value={(prod.scenesLogged / prod.scenesTotal) * 100} color={sc.c} />
                  </div>
                  <ChevronRight size={13} className="text-muted-foreground flex-shrink-0" />
                </div>
              );
            })}
          </div>
        </Card>
      </div>
      <Card>
        <SectionTitle>Scene Logging Progress</SectionTitle>
        <ResponsiveContainer width="100%" height={150}>
          <BarChart data={sceneTimelineData} barGap={4}>
            <CartesianGrid key="bar-grid" strokeDasharray="3 3" stroke="#F1F3F7" />
            <XAxis key="bar-x" dataKey="week" tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
            <YAxis key="bar-y" tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
            <Tooltip key="bar-tooltip" contentStyle={{ borderRadius: 12, border: "1px solid #D9D5F2", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }} />
            <Bar key="bar-total" dataKey="total" fill="#E8E5FF" radius={[4, 4, 0, 0]} name="Planned" />
            <Bar key="bar-logged" dataKey="logged" fill="var(--verse-midnight)" radius={[4, 4, 0, 0]} name="Logged" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div>
          <SectionTitle><span>AI Recommendations <VioletBadge>{aiRecommendations.length} new</VioletBadge></span></SectionTitle>
          <div className="flex flex-col gap-3">
            {aiRecommendations.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
          </div>
        </div>
        <div>
          <SectionTitle action={<Btn variant="ghost" onClick={() => toast.info("Opening team management…")}>Manage</Btn>}>Team Activity</SectionTitle>
          <Card>
            <div className="flex flex-col gap-3">
              {teamMembers.map((member) => {
                const sc = { online: "var(--verse-emerald)", away: "var(--verse-gold)", offline: "#CBD5E1" }[member.status];
                return (
                  <div key={member.id} className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-9 h-9 rounded-full text-primary text-sm font-bold flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)" }}>{member.avatar}</div>
                      <div className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white" style={{ backgroundColor: sc }} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground">{member.name}</p>
                      <p className="text-xs text-muted-foreground">{member.role}</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{member.lastActive}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

const allProductions = [
  { id: "p1", title: "The Last Scene", type: "Feature Film", status: "In Production", scenes: "34/47", score: 94, director: "James K.", budget: "$4.2M", days: 23 },
  { id: "p2", title: "Neon District", type: "TV Series", status: "Pre-Production", scenes: "0/62", score: 100, director: "Sarah M.", budget: "$12M", days: 45 },
  { id: "p3", title: "The Witness", type: "Documentary", status: "Post-Production", scenes: "18/18", score: 88, director: "Tom R.", budget: "$800K", days: 0 },
  { id: "p4", title: "Echoes", type: "Short Film", status: "Completed", scenes: "12/12", score: 99, director: "Lisa P.", budget: "$120K", days: 0 },
];

function ProducerProductions() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const filters = ["All", "In Production", "Pre-Production", "Post-Production", "Completed"];
  const filtered = allProductions.filter((p) => (filter === "All" || p.status === filter) && p.title.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Productions" subtitle="Manage all active and upcoming productions." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New production created!")}>New Production</Btn>} />
      <div className="flex flex-wrap items-center gap-3">
        <SearchBox placeholder="Search productions…" value={search} onChange={setSearch} />
        <div className="flex items-center gap-1">
          {filters.map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`h-8 text-xs font-semibold px-3 rounded-lg transition-all ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>{f}</button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered.map((prod) => {
          const sc = { "In Production": { c: "var(--verse-emerald)", bg: "#ECFDF5" }, "Pre-Production": { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" }, "Post-Production": { c: "#0F62FE", bg: "#EFF6FF" }, Completed: { c: "#64748B", bg: "#F1F3F7" } }[prod.status] || { c: "#64748B", bg: "#F1F3F7" };
          return (
            <Card key={prod.id}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{prod.title}</h3>
                  <p className="text-xs text-muted-foreground">{prod.type}</p>
                </div>
                <StatusBadge label={prod.status} color={sc.c} bg={sc.bg} />
              </div>
              <div className="grid grid-cols-3 gap-3 mb-4 text-center">
                {[{ label: "Scenes", value: prod.scenes }, { label: "Score", value: `${prod.score}%` }, { label: "Days Left", value: prod.days || "Done" }].map((kpi) => (
                  <div key={kpi.label} className="rounded-lg p-2" style={{ backgroundColor: "var(--muted)" }}>
                    <p className="text-sm font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>{kpi.value}</p>
                    <p className="text-xs text-muted-foreground">{kpi.label}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                <Users size={12} /><span>{prod.director}</span><span>·</span><span>{prod.budget}</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => toast.info(`Opening ${prod.title} workspace…`)} className="flex-1 h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>Open Workspace</button>
                <button onClick={() => toast.info("Opening analytics…")} className="h-8 w-8 rounded-lg flex items-center justify-center border hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }}><BarChart3 size={13} className="text-muted-foreground" /></button>
              </div>
            </Card>
          );
        })}
        {filtered.length === 0 && <div className="col-span-2"><EmptyState icon={Film} title="No productions found" description="Try adjusting your search or filters." /></div>}
      </div>
    </div>
  );
}

function ProducerTeam() {
  const extended = [
    ...teamMembers,
    { id: "t5", name: "Carlos Mendez", role: "Gaffer", status: "online" as const, lastActive: "Now", avatar: "CM" },
    { id: "t6", name: "Amy Foster", role: "2nd AD", status: "offline" as const, lastActive: "3h ago", avatar: "AF" },
  ];
  const [search, setSearch] = useState("");
  const filtered = extended.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()) || m.role.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Team" subtitle="Manage your production team." actions={<><Btn variant="secondary" icon={Upload} onClick={() => toast.info("Importing team roster…")}>Import</Btn><Btn variant="primary" icon={Plus} onClick={() => toast.success("Invite sent!")}>Invite Member</Btn></>} />
      <div className="flex items-center gap-3">
        <SearchBox placeholder="Search team…" value={search} onChange={setSearch} />
        <div className="flex items-center gap-1.5 ml-auto text-xs text-muted-foreground">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--verse-emerald)" }} />{extended.filter((m) => m.status === "online").length} online
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((member) => {
          const sc = { online: { c: "var(--verse-emerald)", label: "Online" }, away: { c: "var(--verse-gold)", label: "Away" }, offline: { c: "#CBD5E1", label: "Offline" } }[member.status];
          return (
            <Card key={member.id}>
              <div className="flex items-center gap-3 mb-4">
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl text-primary text-base font-black flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)", fontFamily: "var(--font-display)" }}>{member.avatar}</div>
                  <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-white" style={{ backgroundColor: sc.c }} />
                </div>
                <div className="flex-1">
                  <p className="font-bold text-foreground">{member.name}</p>
                  <p className="text-xs text-muted-foreground">{member.role}</p>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
                <StatusBadge label={sc.label} color={sc.c} bg={`color-mix(in srgb, ${sc.c} 12%, white)`} />
                <span>Active {member.lastActive}</span>
              </div>
              <div className="flex gap-2">
                <button className="flex-1 h-7 text-xs font-medium rounded-lg border hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Messaging ${member.name}…`)}>Message</button>
                <button className="flex-1 h-7 text-xs font-medium rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info("Opening profile…")}>Profile</button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

const reports = [
  { id: "r1", title: "Weekly Continuity Summary", date: "Dec 12, 2024", severity: "info", scenes: 7, issues: 2, score: 94 },
  { id: "r2", title: "Scene 18 Timeline Alert", date: "Dec 11, 2024", severity: "critical", scenes: 1, issues: 1, score: 72 },
  { id: "r3", title: "Costume Continuity Report", date: "Dec 10, 2024", severity: "warning", scenes: 5, issues: 3, score: 81 },
  { id: "r4", title: "AI Semantic Analysis #14", date: "Dec 9, 2024", severity: "info", scenes: 12, issues: 0, score: 99 },
];

function ProducerContinuityReports() {
  const [filter, setFilter] = useState("All");
  const sev = { critical: { c: "var(--verse-red)", bg: "#FEF2F2", l: "Critical" }, warning: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)", l: "Warning" }, info: { c: "#0F62FE", bg: "#EFF6FF", l: "Info" } };
  const filtered = reports.filter((r) => filter === "All" || r.severity === filter.toLowerCase());
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Reports" subtitle="AI-generated continuity analysis reports." actions={<><Btn variant="secondary" icon={Download} onClick={() => toast.info("Downloading all reports…")}>Export All</Btn><Btn variant="primary" icon={RefreshCw} onClick={() => toast.loading("Running new analysis…")}>Run Analysis</Btn></>} />
      <div className="flex items-center gap-2">
        {["All", "Critical", "Warning", "Info"].map((f) => (
          <button key={f} onClick={() => setFilter(f)} className={`h-8 text-xs font-semibold px-3 rounded-lg transition-all ${filter === f ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}>{f}</button>
        ))}
      </div>
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
                <button className="text-xs font-medium text-primary hover:underline" onClick={() => toast.info(`Opening report: ${r.title}`)}>View Report →</button>
                <button className="text-xs font-medium text-muted-foreground hover:text-foreground ml-auto" onClick={() => toast.info("Downloading PDF…")}><Download size={12} className="inline mr-1" />PDF</button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

const analyticsData = [
  { week: "W1", issues: 8, resolved: 5, score: 88 },
  { week: "W2", issues: 6, resolved: 6, score: 91 },
  { week: "W3", issues: 4, resolved: 4, score: 93 },
  { week: "W4", issues: 4, resolved: 2, score: 94 },
];

function ProducerAnalytics() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Analytics" subtitle="Production-wide performance metrics and trends." actions={<><Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting analytics…")}>Export</Btn><Btn variant="secondary" icon={Filter} onClick={() => toast.info("Opening filters…")}>Filter</Btn></>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Avg. Continuity Score" value="94%" icon={TrendingUp} color="var(--verse-emerald)" />
        <StatCard label="Issues Resolved" value="17/21" subtext="81% resolution rate" icon={CheckCircle} color="var(--verse-midnight)" />
        <StatCard label="AI Accuracy" value="97.2%" icon={Brain} color="var(--verse-violet)" />
        <StatCard label="Production Velocity" value="+12%" subtext="vs last month" icon={Zap} color="var(--verse-gold)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Continuity Score Over Time</SectionTitle>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={analyticsData}>
              <CartesianGrid key="line-grid" strokeDasharray="3 3" stroke="#E8E5FF" />
              <XAxis key="line-x" dataKey="week" tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <YAxis key="line-y" domain={[85, 100]} tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <Tooltip key="line-tooltip" contentStyle={{ borderRadius: 12, border: "1px solid #D9D5F2" }} />
              <Line key="line-score" type="monotone" dataKey="score" stroke="var(--verse-midnight)" strokeWidth={2} dot={{ fill: "var(--verse-midnight)", r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle>Issues vs Resolved</SectionTitle>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={analyticsData} barGap={4}>
              <CartesianGrid key="issues-grid" strokeDasharray="3 3" stroke="#E8E5FF" />
              <XAxis key="issues-x" dataKey="week" tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <YAxis key="issues-y" tick={{ fontSize: 11, fill: "#5A6A85" }} axisLine={false} tickLine={false} />
              <Tooltip key="issues-tooltip" contentStyle={{ borderRadius: 12, border: "1px solid #D9D5F2" }} />
              <Bar key="issues-bar" dataKey="issues" fill="#FEE2E2" radius={[4, 4, 0, 0]} name="Issues" />
              <Bar key="resolved-bar" dataKey="resolved" fill="var(--verse-emerald)" radius={[4, 4, 0, 0]} name="Resolved" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card>
        <SectionTitle>Production Performance by Department</SectionTitle>
        <div className="flex flex-col gap-3">
          {[
            { dept: "Script Supervision", score: 97, color: "var(--verse-midnight)" },
            { dept: "Costume & Wardrobe", score: 91, color: "var(--verse-violet)" },
            { dept: "Props & Set Dressing", score: 88, color: "var(--verse-gold)" },
            { dept: "Camera & Lighting", score: 95, color: "#0F62FE" },
          ].map((d) => (
            <div key={d.dept} className="flex items-center gap-4">
              <p className="text-sm text-foreground w-44 flex-shrink-0">{d.dept}</p>
              <div className="flex-1"><ProgressBar value={d.score} color={d.color} /></div>
              <ScorePill value={d.score} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ProducerAIInsights() {
  const insights = [
    { id: "i1", type: "Pattern", title: "Costume inconsistency pattern detected", body: "VERSE identified a recurring costume color-continuity issue across 3 scenes involving the lead character during interior night shots.", confidence: 94, impact: "High" },
    { id: "i2", type: "Prediction", title: "Scene 34–36 likely to require re-shoot", body: "Based on current prop tracking data, 3 props referenced in the screenplay are logged differently across these scenes.", confidence: 87, impact: "Medium" },
    { id: "i3", type: "Opportunity", title: "Batch filming opportunity identified", body: "5 scenes share the same location and character configuration. Scheduling them consecutively could reduce setup time by ~40%.", confidence: 91, impact: "High" },
    { id: "i4", type: "Anomaly", title: "Timeline anomaly in Act 2", body: "Scene 22 references a story event 3 days after Scene 18, but the 48-hour production schedule makes this continuity impossible.", confidence: 99, impact: "Critical" },
  ];
  const colors = { Pattern: { c: "var(--verse-violet)", bg: "var(--verse-violet-light)" }, Prediction: { c: "#0F62FE", bg: "#EFF6FF" }, Opportunity: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Anomaly: { c: "var(--verse-red)", bg: "#FEF2F2" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-violet)" }}>Insights</span></span>} subtitle="IBM watsonx-powered semantic analysis of your production." actions={<Btn variant="primary" icon={Sparkles} onClick={() => toast.loading("Running deep analysis…")}>Run Deep Analysis</Btn>} />
      <div className="flex flex-col gap-4">
        {insights.map((ins) => {
          const s = colors[ins.type as keyof typeof colors];
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
                <button className="flex-1 h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.success("Insight applied to production log.")}>Apply Insight</button>
                <button className="h-8 px-3 text-xs border rounded-lg text-muted-foreground hover:bg-muted transition-colors" style={{ borderColor: "var(--border)" }} onClick={() => toast.info("Dismissed.")}>Dismiss</button>
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

function DirectorOverview({ productionName, onAIAction }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Director's View" subtitle={`Scene tracking and character continuity for ${productionName}.`} actions={<Btn variant="primary" icon={Sparkles} onClick={() => toast.loading("Running scene analysis…")}>Analyze Scenes</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Scenes Directed" value="34" icon={Film} color="var(--verse-midnight)" />
        <StatCard label="Characters Tracked" value={3} icon={Users} color="var(--verse-violet)" />
        <StatCard label="AI Recommendations" value={3} icon={Sparkles} color="var(--verse-gold)" />
        <StatCard label="Continuity Score" value="94%" icon={CheckCircle} color="var(--verse-emerald)" />
      </div>
      <Card>
        <SectionTitle action={<Btn variant="ghost" onClick={() => toast.info("Opening character tracker…")}>View All →</Btn>}>Character Continuity Tracker</SectionTitle>
        <div className="flex flex-col gap-4">
          {characters.map((char) => (
            <div key={char.id} className="p-4 border rounded-xl hover:border-primary/20 transition-colors" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{char.name}</h4>
                    <StatusBadge label={char.type} color={char.type === "Lead" ? "var(--verse-midnight)" : "#64748B"} bg={char.type === "Lead" ? "var(--verse-midnight-light)" : "#F1F3F7"} />
                  </div>
                  <p className="text-xs text-muted-foreground">Played by {char.actor}</p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-black" style={{ fontFamily: "var(--font-display)", color: char.continuityScore >= 90 ? "var(--verse-emerald)" : "var(--verse-gold)" }}>{char.continuityScore}%</p>
                  <p className="text-xs text-muted-foreground">continuity</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><p className="text-muted-foreground">Scenes</p><p className="font-semibold">{char.scenesIn}</p></div>
                <div><p className="text-muted-foreground">Last scene</p><p className="font-semibold">{char.lastScene}</p></div>
                <div className="col-span-2"><p className="text-muted-foreground">Current costume</p><p className="font-medium">{char.lastCostume}</p></div>
              </div>
            </div>
          ))}
        </div>
      </Card>
      <div>
        <SectionTitle>AI Recommendations</SectionTitle>
        <div className="flex flex-col gap-3">
          {aiRecommendations.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
        </div>
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

function DirectorSceneTracking() {
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const sev = { Logged: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Flagged: { c: "var(--verse-red)", bg: "#FEF2F2" }, "In Progress": { c: "var(--verse-violet)", bg: "var(--verse-violet-light)" }, Scheduled: { c: "#64748B", bg: "#F1F3F7" }, Review: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" } };
  const filtered = sceneList.filter((s) => (filter === "All" || s.status === filter) && (s.scene + s.location + s.chars).toLowerCase().includes(search.toLowerCase()));
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Scene Tracking" subtitle="Monitor all scenes across the production." actions={<><Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting scene log…")}>Export</Btn><Btn variant="primary" icon={Plus} onClick={() => toast.success("New scene added.")}>Add Scene</Btn></>} />
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

function DirectorCharacters() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Characters" subtitle="Track character continuity and state across all scenes." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("Character profile created.")}>Add Character</Btn>} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {characters.map((char) => (
          <Card key={char.id}>
            <div className="flex items-start justify-between mb-4">
              <div className="w-14 h-14 rounded-2xl font-black flex items-center justify-center text-2xl" style={{ backgroundColor: "var(--verse-midnight-light)", fontFamily: "var(--font-display)" }}>
                {char.name.split(" ").map((n: string) => n[0]).join("")}
              </div>
              <StatusBadge label={char.type} color={char.type === "Lead" ? "var(--verse-midnight)" : "#64748B"} bg={char.type === "Lead" ? "var(--verse-midnight-light)" : "#F1F3F7"} />
            </div>
            <h3 className="font-black text-foreground mb-0.5" style={{ fontFamily: "var(--font-display)" }}>{char.name}</h3>
            <p className="text-xs text-muted-foreground mb-4">{char.actor}</p>
            <div className="flex flex-col gap-2 text-xs mb-4">
              {[{ label: "Scenes", val: char.scenesIn }, { label: "Last scene", val: char.lastScene }, { label: "Costume", val: char.lastCostume }].map((f) => (
                <div key={f.label} className="flex items-start gap-2">
                  <span className="text-muted-foreground w-20 flex-shrink-0">{f.label}</span>
                  <span className="text-foreground font-medium flex-1">{f.val}</span>
                </div>
              ))}
            </div>
            <div className="mb-3">
              <div className="flex justify-between text-xs text-muted-foreground mb-1"><span>Continuity</span><ScorePill value={char.continuityScore} /></div>
              <ProgressBar value={char.continuityScore} color={char.continuityScore >= 90 ? "var(--verse-emerald)" : "var(--verse-gold)"} />
            </div>
            <button className="w-full h-8 text-xs font-bold rounded-lg" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }} onClick={() => toast.info(`Opening ${char.name} full profile…`)}>View Full Profile</button>
          </Card>
        ))}
      </div>
      <Card>
        <SectionTitle>Character Appearance Notes</SectionTitle>
        <p className="text-xs text-muted-foreground mb-3">AI-generated notes on character consistency across all logged scenes.</p>
        <div className="flex flex-col gap-3">
          {[
            { char: "Elena Chen", note: "Costume colour confirmed consistent through Scenes 17–25. Hair continuity verified. Jewelry: gold bracelet present in all exterior shots.", score: 97 },
            { char: "Marcus Reyes", note: "Watch (vintage Rolex) absent in shots 31B–31D — flagged for review. Jacket consistent throughout.", score: 89 },
            { char: "Dr. Helena Park", note: "Lab coat continuity confirmed. Eyeglasses style verified across 4 scenes.", score: 95 },
          ].map((n) => (
            <div key={n.char} className="p-3 rounded-xl border" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-bold text-foreground">{n.char}</p>
                <ScorePill value={n.score} />
              </div>
              <p className="text-xs text-muted-foreground">{n.note}</p>
            </div>
          ))}
        </div>
      </Card>
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

function DirectorTimeline() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Production Timeline" subtitle="Key milestones and schedule overview." actions={<Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting timeline…")}>Export Timeline</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Days in Production" value={24} icon={Calendar} color="var(--verse-midnight)" />
        <StatCard label="Days Remaining" value={23} icon={Clock} color="var(--verse-gold)" />
        <StatCard label="Scenes Shot" value="34/47" icon={Film} color="var(--verse-emerald)" />
        <StatCard label="On Schedule" value="Yes" icon={CheckCircle} color="var(--verse-emerald)" />
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

function DirectorAIRecs({ onAIAction }: { onAIAction: (id: string, action: "accept" | "dismiss") => void }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-violet)" }}>Recommendations</span></span>} subtitle="Explainable AI insights for your directorial decisions." actions={<Btn variant="primary" icon={RefreshCw} onClick={() => toast.loading("Refreshing recommendations…")}>Refresh</Btn>} />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Pending Review" value={3} icon={AlertTriangle} color="var(--verse-gold)" />
        <StatCard label="Accepted this week" value={7} icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="AI Accuracy" value="97%" icon={Brain} color="var(--verse-violet)" />
      </div>
      <div className="flex flex-col gap-3">
        {aiRecommendations.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
      </div>
    </div>
  );
}

function DirectorSemanticMemory() {
  const nodes = [
    { id: "n1", label: "Elena Chen", type: "Character", color: "var(--verse-midnight)", connections: ["Scene 17", "Scene 18", "Scene 23", "Marcus Reyes", "Navy Jacket"] },
    { id: "n2", label: "Marcus Reyes", type: "Character", color: "var(--verse-violet)", connections: ["Scene 17", "Scene 24", "Elena Chen"] },
    { id: "n3", label: "Navy Jacket", type: "Costume", color: "var(--verse-gold)", connections: ["Elena Chen", "Scene 17", "Scene 23"] },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span><span style={{ color: "var(--verse-violet)" }}>Semantic</span> Memory</span>} subtitle="AI-constructed knowledge graph of your production's relationships." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Entities Tracked" value={127} icon={Brain} color="var(--verse-violet)" />
        <StatCard label="Relationships" value={384} icon={GitBranch} color="var(--verse-midnight)" />
        <StatCard label="Scenes Analyzed" value={34} icon={Film} color="var(--verse-gold)" />
        <StatCard label="Memory Depth" value="3 acts" icon={Layers} color="var(--verse-emerald)" />
      </div>
      <Card>
        <SectionTitle action={<VioletBadge>Live Graph</VioletBadge>}>Knowledge Graph — Key Entities</SectionTitle>
        <p className="text-xs text-muted-foreground mb-4">Semantic relationships between characters, locations, costumes, and props as understood by the VERSE AI engine.</p>
        <div className="flex flex-col gap-4">
          {nodes.map((node) => (
            <div key={node.id} className="p-4 rounded-xl border" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: node.color }} />
                <span className="text-sm font-bold text-foreground">{node.label}</span>
                <StatusBadge label={node.type} color={node.color} bg={`color-mix(in srgb, ${node.color} 12%, white)`} />
              </div>
              <div className="flex flex-wrap gap-2">
                {node.connections.map((c) => (
                  <button key={c} className="text-xs px-2 py-1 rounded-lg border transition-colors hover:bg-muted" style={{ borderColor: "var(--border)" }} onClick={() => toast.info(`Exploring: ${c}`)}>
                    {c}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCRIPT SUPERVISOR PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ScriptSupervisorOverview({ productionName, onAIAction }: { productionName: string; onAIAction: (id: string, action: "accept" | "dismiss") => void }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Script Supervisor" subtitle={`Continuity tracking for ${productionName}.`} actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New continuity note added.")}>Add Note</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Scenes Reviewed" value="34" icon={FileText} color="#0F62FE" />
        <StatCard label="Continuity Issues" value={4} subtext="2 critical" icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="AI Alerts" value={2} icon={Zap} color="var(--verse-gold)" />
        <StatCard label="Accuracy Score" value="97%" icon={CheckCircle} color="var(--verse-emerald)" />
      </div>
      <Card>
        <SectionTitle action={<button className="text-xs text-primary font-semibold hover:underline" onClick={() => toast.info("Downloading CSV…")}><Download size={12} className="inline mr-1" />Export</button>}>Continuity Log</SectionTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b" style={{ borderColor: "var(--border)" }}>
              {["Scene", "Location", "Characters", "Status", "Score", "Flag"].map((h) => <th key={h} className="pb-3 pr-4 text-left text-xs font-bold text-muted-foreground">{h}</th>)}
            </tr></thead>
            <tbody>
              {sceneList.map((row) => {
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
      <div>
        <SectionTitle>AI Alerts</SectionTitle>
        <div className="flex flex-col gap-3">
          {aiRecommendations.slice(0, 2).map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
        </div>
      </div>
    </div>
  );
}

function ContinuityTracking() {
  const [issues, setIssues] = useState([
    { id: "ci1", scene: "Scene 18", type: "Timeline", desc: "References 'Tuesday morning' but Scene 17 established 'Monday evening'.", severity: "critical", resolved: false },
    { id: "ci2", scene: "Scene 23", type: "Costume", desc: "Elena's jacket changes from navy to black between shots 23A and 23C.", severity: "warning", resolved: false },
    { id: "ci3", scene: "Scene 31", type: "Prop", desc: "Marcus's watch absent in shots 31B–31D.", severity: "warning", resolved: false },
    { id: "ci4", scene: "Scene 17", type: "Dialogue", desc: "Minor inconsistency in coffee cup position during dialogue exchange.", severity: "info", resolved: true },
  ]);
  const toggleResolved = (id: string) => {
    setIssues((prev) => prev.map((i) => i.id === id ? { ...i, resolved: !i.resolved } : i));
    toast.success("Continuity issue status updated.");
  };
  const sev = { critical: { c: "var(--verse-red)", bg: "#FEF2F2", l: "Critical" }, warning: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)", l: "Warning" }, info: { c: "#0F62FE", bg: "#EFF6FF", l: "Info" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Tracking" subtitle="Monitor, flag, and resolve continuity issues." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New issue logged.")}>Log Issue</Btn>} />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Open Issues" value={issues.filter((i) => !i.resolved).length} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Resolved" value={issues.filter((i) => i.resolved).length} icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="Resolution Rate" value={`${Math.round((issues.filter((i) => i.resolved).length / issues.length) * 100)}%`} icon={TrendingUp} color="var(--verse-midnight)" />
      </div>
      <div className="flex flex-col gap-3">
        {issues.map((issue) => {
          const s = sev[issue.severity as keyof typeof sev];
          return (
            <Card key={issue.id}>
              <div className="flex items-start gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <StatusBadge label={s.l} color={s.c} bg={s.bg} />
                    <span className="text-xs font-mono text-muted-foreground">{issue.scene}</span>
                    <span className="text-xs text-muted-foreground">· {issue.type}</span>
                    {issue.resolved && <StatusBadge label="Resolved" color="var(--verse-emerald)" bg="#ECFDF5" />}
                  </div>
                  <p className={`text-sm leading-relaxed ${issue.resolved ? "line-through text-muted-foreground" : "text-foreground"}`}>{issue.desc}</p>
                </div>
                <button
                  onClick={() => toggleResolved(issue.id)}
                  className="flex-shrink-0 w-8 h-8 rounded-lg border flex items-center justify-center transition-colors hover:bg-muted"
                  style={{ borderColor: "var(--border)" }}
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

function ScreenplayAnalysis() {
  const scenes = [
    { num: "Scene 17", entities: ["Elena Chen", "Marcus Reyes", "Office Interior", "Coffee Mug", "Monday Evening"], sentiment: "Tension", wordCount: 847, aiScore: 100 },
    { num: "Scene 18", entities: ["Elena Chen", "Dr. Park", "Office Interior", "Tuesday Morning (⚠)"], sentiment: "Conflict", wordCount: 623, aiScore: 72 },
    { num: "Scene 23", entities: ["Elena Chen", "Navy Jacket (⚠)", "Diner Interior", "Evening"], sentiment: "Introspective", wordCount: 312, aiScore: 81 },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Screenplay Analysis" subtitle="Semantic parsing and entity extraction from the screenplay." actions={<Btn variant="primary" icon={Upload} onClick={() => toast.info("Upload new screenplay version…")}>Update Screenplay</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Scenes" value={47} icon={FileText} color="var(--verse-midnight)" />
        <StatCard label="Characters" value={12} icon={Users} color="var(--verse-violet)" />
        <StatCard label="Props Tracked" value={34} icon={Layers} color="var(--verse-gold)" />
        <StatCard label="Semantic Score" value="91%" icon={Brain} color="var(--verse-emerald)" />
      </div>
      <div className="flex flex-col gap-4">
        {scenes.map((s) => (
          <Card key={s.num}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{s.num}</h3>
                <p className="text-xs text-muted-foreground">{s.wordCount} words · Mood: {s.sentiment}</p>
              </div>
              <ScorePill value={s.aiScore} />
            </div>
            <div>
              <p className="text-xs font-bold text-muted-foreground mb-2">Extracted Entities</p>
              <div className="flex flex-wrap gap-2">
                {s.entities.map((e) => (
                  <span key={e} className={`text-xs px-2 py-1 rounded-lg border ${e.includes("⚠") ? "" : ""}`} style={{ borderColor: e.includes("⚠") ? "rgba(154,111,0,0.3)" : "var(--border)", color: e.includes("⚠") ? "var(--verse-gold)" : "var(--muted-foreground)", background: e.includes("⚠") ? "var(--verse-gold-light)" : "transparent" }}>
                    {e}
                  </span>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function SceneTimeline() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Scene Timeline" subtitle="Chronological scene order with continuity status." actions={<Btn variant="secondary" icon={Filter} onClick={() => toast.info("Opening filter options…")}>Filter</Btn>} />
      <Card>
        <div className="flex flex-col gap-0">
          {sceneList.map((s, i) => {
            const sc = { Flagged: "var(--verse-red)", Logged: "var(--verse-emerald)", "In Progress": "var(--verse-violet)", Review: "var(--verse-gold)", Scheduled: "#CBD5E1" }[s.status] || "#CBD5E1";
            return (
              <div key={s.id} className="relative flex gap-4 group cursor-pointer" onClick={() => toast.info(`Opening ${s.scene}…`)}>
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full border-2 border-white mt-4 z-10" style={{ backgroundColor: sc }} />
                  {i < sceneList.length - 1 && <div className="w-px flex-1 mt-1" style={{ backgroundColor: "var(--border)" }} />}
                </div>
                <div className={`flex-1 p-3 rounded-xl mb-2 border transition-all group-hover:shadow-sm`} style={{ borderColor: "var(--border)" }}>
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-mono font-bold text-foreground">{s.scene}</span>
                      <span className="text-xs text-muted-foreground ml-2">{s.location}</span>
                    </div>
                    <div className="flex items-center gap-2">
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

function AIAlerts({ onAIAction }: { onAIAction: (id: string, action: "accept" | "dismiss") => void }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span>AI <span style={{ color: "var(--verse-red)" }}>Alerts</span></span>} subtitle="Real-time continuity alerts generated by the VERSE AI engine." actions={<Btn variant="primary" icon={RefreshCw} onClick={() => toast.loading("Scanning for new alerts…")}>Scan Now</Btn>} />
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Critical Alerts" value={1} icon={AlertTriangle} color="var(--verse-red)" />
        <StatCard label="Warnings" value={2} icon={Zap} color="var(--verse-gold)" />
        <StatCard label="AI Confidence" value="96%" icon={Brain} color="var(--verse-violet)" />
      </div>
      <div className="flex flex-col gap-3">
        {aiRecommendations.map((rec) => <AIRecommendationCard key={rec.id} rec={rec} onAction={onAIAction} />)}
      </div>
    </div>
  );
}

function NarrativeProgression() {
  const acts = [
    { label: "Act 1 — Setup", scenes: "Scenes 1–15", status: "Complete", completion: 100, color: "var(--verse-emerald)" },
    { label: "Act 2A — Conflict Begins", scenes: "Scenes 16–28", status: "In Progress", completion: 70, color: "var(--verse-violet)" },
    { label: "Act 2B — Rising Action", scenes: "Scenes 29–38", status: "Upcoming", completion: 0, color: "#CBD5E1" },
    { label: "Act 3 — Resolution", scenes: "Scenes 39–47", status: "Upcoming", completion: 0, color: "#CBD5E1" },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Narrative Progression" subtitle="Story structure and semantic progression analysis." />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Acts Completed" value="1/3" icon={BookOpen} color="var(--verse-midnight)" />
        <StatCard label="Scenes Filmed" value="34/47" icon={Film} color="var(--verse-emerald)" />
        <StatCard label="Story Progress" value="72%" icon={TrendingUp} color="var(--verse-violet)" />
        <StatCard label="Narrative Score" value="91%" icon={Star} color="var(--verse-gold)" />
      </div>
      <Card>
        <SectionTitle>Story Arc Completion</SectionTitle>
        <div className="flex flex-col gap-4">
          {acts.map((act) => (
            <div key={act.label}>
              <div className="flex items-center justify-between mb-1.5">
                <div>
                  <p className="text-sm font-bold text-foreground">{act.label}</p>
                  <p className="text-xs text-muted-foreground">{act.scenes}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge label={act.status} color={act.color} bg={`color-mix(in srgb, ${act.color} 12%, white)`} />
                  <span className="text-sm font-black" style={{ fontFamily: "var(--font-display)", color: act.color }}>{act.completion}%</span>
                </div>
              </div>
              <ProgressBar value={act.completion} color={act.color} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONTINUITY SUPERVISOR PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ContinuitySupervisorOverview({ productionName }: { productionName: string }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Supervisor" subtitle={`Asset continuity workspace for ${productionName}.`} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Costumes Tracked" value={24} icon={Eye} color="var(--verse-midnight)" />
        <StatCard label="Props Logged" value={47} icon={Layers} color="var(--verse-violet)" />
        <StatCard label="Verified Scenes" value="29/34" icon={CheckCircle} color="var(--verse-emerald)" />
        <StatCard label="Open Issues" value={3} icon={AlertTriangle} color="var(--verse-gold)" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle>Costume Continuity</SectionTitle>
          {characters.map((c) => (
            <div key={c.id} className="flex items-center gap-3 py-2 border-b last:border-0" style={{ borderColor: "var(--border)" }}>
              <div className="w-8 h-8 rounded-lg font-bold text-xs flex items-center justify-center" style={{ backgroundColor: "var(--verse-midnight-light)", color: "var(--verse-midnight)" }}>{c.name.split(" ").map((n: string) => n[0]).join("")}</div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-foreground">{c.name}</p>
                <p className="text-xs text-muted-foreground truncate">{c.lastCostume}</p>
              </div>
              <ScorePill value={c.continuityScore} />
            </div>
          ))}
        </Card>
        <Card>
          <SectionTitle>Recent Verifications</SectionTitle>
          <div className="flex flex-col gap-3">
            {[
              { item: "Elena's Navy Jacket", scene: "Scene 23", result: "✓ Verified", color: "var(--verse-emerald)" },
              { item: "Marcus's Watch", scene: "Scene 31", result: "⚠ Flagged", color: "var(--verse-gold)" },
              { item: "Lab Coat — Dr. Park", scene: "Scene 18", result: "✓ Verified", color: "var(--verse-emerald)" },
              { item: "Coffee Mug (hero prop)", scene: "Scene 17", result: "✓ Verified", color: "var(--verse-emerald)" },
            ].map((v) => (
              <div key={v.item} className="flex items-center gap-3 text-sm">
                <div className="flex-1">
                  <p className="font-medium text-foreground">{v.item}</p>
                  <p className="text-xs text-muted-foreground">{v.scene}</p>
                </div>
                <span className="text-xs font-bold" style={{ color: v.color }}>{v.result}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function CostumeTracking() {
  const costumes = [
    { id: "c1", name: "Navy Blazer", character: "Elena Chen", scenes: "17, 18, 23, 24", status: "Verified", continuity: 97 },
    { id: "c2", name: "Charcoal Suit", character: "Marcus Reyes", scenes: "17, 24, 31", status: "Issue", continuity: 89 },
    { id: "c3", name: "White Lab Coat", character: "Dr. Helena Park", scenes: "18, 19", status: "Verified", continuity: 100 },
    { id: "c4", name: "Casual — Blue Jeans", character: "Elena Chen", scenes: "20, 21", status: "Pending", continuity: 0 },
  ];
  const sc = { Verified: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Issue: { c: "var(--verse-red)", bg: "#FEF2F2" }, Pending: { c: "#64748B", bg: "#F1F3F7" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Costume Tracking" subtitle="Character costume continuity across all scenes." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New costume logged.")}>Log Costume</Btn>} />
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

function PropTracking() {
  const props = [
    { id: "p1", name: "Vintage Rolex Watch", category: "Jewelry", character: "Marcus Reyes", scenes: "31A, 31E", status: "Issue", note: "Absent in shots 31B–31D" },
    { id: "p2", name: "Hero Coffee Mug", category: "Prop", character: "Elena Chen", scenes: "17, 18", status: "Verified", note: "Consistent across all shots" },
    { id: "p3", name: "Police Badge #4821", category: "ID / Badge", character: "Elena Chen", scenes: "17–25", status: "Verified", note: "Visible in all applicable scenes" },
    { id: "p4", name: "Leather Briefcase", category: "Prop", character: "Marcus Reyes", scenes: "17, 24", status: "Pending", note: "Not yet logged for Scene 31" },
    { id: "p5", name: "Crime Board Photos", category: "Set Dressing", character: "—", scenes: "17, 18", status: "Verified", note: "Photo order confirmed consistent" },
  ];
  const sc = { Verified: { c: "var(--verse-emerald)", bg: "#ECFDF5" }, Issue: { c: "var(--verse-red)", bg: "#FEF2F2" }, Pending: { c: "var(--verse-gold)", bg: "var(--verse-gold-light)" } };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Prop Tracking" subtitle="Prop inventory and scene continuity verification." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New prop logged.")}>Log Prop</Btn>} />
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

function ContinuityVerification() {
  const [items, setItems] = useState([
    { id: "v1", scene: "Scene 17", check: "Costume verified against Scene 16 reference", done: true },
    { id: "v2", scene: "Scene 18", check: "Timeline logic reviewed and flagged", done: true },
    { id: "v3", scene: "Scene 23", check: "Costume colour inconsistency resolved", done: false },
    { id: "v4", scene: "Scene 24", check: "Prop inventory confirmed for exterior shoot", done: true },
    { id: "v5", scene: "Scene 31", check: "Marcus watch continuity resolved", done: false },
    { id: "v6", scene: "Scene 31", check: "Rooftop lighting continuity verified", done: false },
  ]);
  const toggle = (id: string) => { setItems((prev) => prev.map((i) => i.id === id ? { ...i, done: !i.done } : i)); toast.success("Verification updated."); };
  const done = items.filter((i) => i.done).length;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Verification" subtitle="Scene-by-scene verification checklist." actions={<Btn variant="primary" icon={Download} onClick={() => toast.info("Exporting verification report…")}>Export Report</Btn>} />
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

function ProductionMemory() {
  const events = [
    { time: "Dec 12, 10:45", event: "AI detected timeline inconsistency in Scene 18", type: "ai", color: "var(--verse-violet)" },
    { time: "Dec 12, 09:30", event: "Scene 17 fully verified and logged to production memory", type: "log", color: "var(--verse-emerald)" },
    { time: "Dec 11, 16:20", event: "Elena's costume reference photos uploaded — Scenes 23–25", type: "upload", color: "var(--verse-midnight)" },
    { time: "Dec 11, 14:05", event: "Marcus watch issue flagged by script supervisor", type: "flag", color: "var(--verse-red)" },
    { time: "Dec 10, 11:30", event: "Scene 24 logged with full prop manifest", type: "log", color: "var(--verse-emerald)" },
    { time: "Dec 9, 09:00", event: "Production memory snapshot created — Week 3", type: "snapshot", color: "var(--verse-gold)" },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title={<span><span style={{ color: "var(--verse-violet)" }}>Production</span> Memory</span>} subtitle="Complete history of logged continuity events." actions={<Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting memory log…")}>Export Log</Btn>} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Memory Entries" value={284} icon={Brain} color="var(--verse-violet)" />
        <StatCard label="Entities Tracked" value={127} icon={Layers} color="var(--verse-midnight)" />
        <StatCard label="AI Events" value={42} icon={Sparkles} color="var(--verse-gold)" />
        <StatCard label="Memory Coverage" value="72%" icon={TrendingUp} color="var(--verse-emerald)" />
      </div>
      <Card>
        <SectionTitle>Event Timeline</SectionTitle>
        <div className="flex flex-col gap-4">
          {events.map((e, i) => <ActivityItem key={i} icon={Brain} color={e.color} text={e.event} time={e.time} />)}
        </div>
      </Card>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRODUCTION MANAGER PAGES
// ═══════════════════════════════════════════════════════════════════════════════

function ProductionManagerOverview({ productionName }: { productionName: string }) {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Production Manager" subtitle={`Coordination workspace for ${productionName}.`} />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Team Members" value={12} icon={Users} color="var(--verse-midnight)" />
        <StatCard label="Active Tasks" value={18} icon={CheckCircle} color="var(--verse-violet)" />
        <StatCard label="Days on Schedule" value={22} icon={Calendar} color="var(--verse-emerald)" />
        <StatCard label="Budget Used" value="68%" icon={BarChart3} color="var(--verse-gold)" />
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
                <button className="text-xs text-primary hover:underline" onClick={() => toast.info(`Opening task: ${t.task}`)}>Open</button>
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
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Scheduling" subtitle="Production schedule and calendar management." actions={<><Btn variant="secondary" icon={Download} onClick={() => toast.info("Exporting schedule…")}>Export</Btn><Btn variant="primary" icon={Plus} onClick={() => toast.success("Event added.")}>Add Event</Btn></>} />
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
      <PageHeader title="My Tasks" subtitle="Your assigned tasks and deadlines." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New task created.")}>Add Task</Btn>} />
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

function ContinuityUpdates() {
  const updates = [
    { id: "u1", title: "AI flagged costume discrepancy — Scene 23", time: "11:42", type: "ai", body: "Elena's jacket colour changes from navy to black between shots 23A and 23C. Wardrobe team notified." },
    { id: "u2", title: "Marcus watch continuity issue logged", time: "09:30", type: "flag", body: "Watch absent in shots 31B–31D. Script supervisor requesting resolution before afternoon shoot." },
    { id: "u3", title: "Scene 17 fully verified", time: "Yesterday", type: "verified", body: "All costume, prop, and timeline elements confirmed. Continuity score: 100%." },
  ];
  const colors = { ai: "var(--verse-violet)", flag: "var(--verse-red)", verified: "var(--verse-emerald)" };
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Continuity Updates" subtitle="Latest continuity changes affecting your department." />
      <div className="flex flex-col gap-3">
        {updates.map((u) => {
          const c = colors[u.type as keyof typeof colors];
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
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function Discussions() {
  const threads = [
    { id: "d1", title: "Scene 31 — Rooftop continuity check", author: "Nina T.", replies: 4, time: "1h ago", tag: "Continuity" },
    { id: "d2", title: "Act 2 costume reference photos needed", author: "Sarah C.", replies: 2, time: "3h ago", tag: "Wardrobe" },
    { id: "d3", title: "Location change for Scene 35?", author: "Tom R.", replies: 7, time: "Yesterday", tag: "General" },
  ];
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Discussions" subtitle="Team discussion threads for the production." actions={<Btn variant="primary" icon={Plus} onClick={() => toast.success("New thread created.")}>New Thread</Btn>} />
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
  userRole, productionName, onAIAction, activeNav,
}: {
  userRole: UserRole; productionName: string;
  onAIAction: (id: string, action: "accept" | "dismiss") => void;
  activeNav: string;
}) {
  // Settings page is shared across all roles
  if (activeNav === "Settings") return <SettingsPage />;

  switch (userRole) {
    case "producer":
      switch (activeNav) {
        case "Productions": return <ProducerProductions />;
        case "Team": return <ProducerTeam />;
        case "Continuity Reports": return <ProducerContinuityReports />;
        case "Analytics": return <ProducerAnalytics />;
        case "AI Insights": return <ProducerAIInsights />;
        case "Workspace": return <ProducerWorkspace />;
        default: return <ProducerOverview productionName={productionName} onAIAction={onAIAction} />;
      }

    case "director":
      switch (activeNav) {
        case "Scene Tracking": return <DirectorSceneTracking />;
        case "Characters": return <DirectorCharacters />;
        case "Production Timeline": return <DirectorTimeline />;
        case "AI Recommendations": return <DirectorAIRecs onAIAction={onAIAction} />;
        case "Semantic Memory": return <DirectorSemanticMemory />;
        default: return <DirectorOverview productionName={productionName} onAIAction={onAIAction} />;
      }

    case "script-supervisor":
      switch (activeNav) {
        case "Continuity Tracking": return <ContinuityTracking />;
        case "Screenplay Analysis": return <ScreenplayAnalysis />;
        case "Scene Timeline": return <SceneTimeline />;
        case "AI Alerts": return <AIAlerts onAIAction={onAIAction} />;
        case "Narrative Progression": return <NarrativeProgression />;
        default: return <ScriptSupervisorOverview productionName={productionName} onAIAction={onAIAction} />;
      }

    case "continuity-supervisor":
      switch (activeNav) {
        case "Costume Tracking": return <CostumeTracking />;
        case "Prop Tracking": return <PropTracking />;
        case "Continuity Verification": return <ContinuityVerification />;
        case "Production Memory": return <ProductionMemory />;
        default: return <ContinuitySupervisorOverview productionName={productionName} />;
      }

    case "production-manager":
      switch (activeNav) {
        case "Team Collaboration": return <TeamCollaboration />;
        case "Scheduling": return <Scheduling />;
        case "Workspace Management": return <WorkspaceManagement />;
        case "Reports": return <ManagerReports />;
        default: return <ProductionManagerOverview productionName={productionName} />;
      }

    case "department-member":
      switch (activeNav) {
        case "My Tasks": return <MyTasks />;
        case "Notes": return <Notes />;
        case "Continuity Updates": return <ContinuityUpdates />;
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

  const handleAIAction = (id: string, action: "accept" | "dismiss") => {
    if (action === "accept") toast.success("AI recommendation accepted. Continuity log updated.");
    else toast.info("Recommendation dismissed.");
  };

  const handleSignOut = () => {
    toast.success("Signed out successfully. See you next production!");
    setTimeout(onSignOut, 700);
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <AIAnalysisModal isOpen={isAIModalOpen} onClose={() => setIsAIModalOpen(false)} />
      {isSidebarOpen && <div className="lg:hidden fixed inset-0 bg-foreground/25 backdrop-blur-sm z-30" onClick={() => setIsSidebarOpen(false)} />}

      <DashboardSidebar
        userRole={currentRole}
        productionName={productionName}
        userName={userName}
        isOpen={isSidebarOpen}
        activeNav={activeNav}
        onNavSelect={(label) => { setActiveNav(label); setIsSidebarOpen(false); }}
        onSignOut={handleSignOut}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <DashboardTopNav
          productionName={productionName}
          onMobileMenuToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          activeRole={currentRole}
          onRoleChange={(role) => { setCurrentRole(role); setActiveNav("Overview"); }}
          onRunAIAnalysis={() => setIsAIModalOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-5 md:p-6" style={{ background: "linear-gradient(180deg, #F0EEFF 0%, #F5F3FF 100%)" }}>
          <div className="max-w-6xl mx-auto">
            <DashboardContent
              userRole={currentRole}
              productionName={productionName}
              onAIAction={handleAIAction}
              activeNav={activeNav}
            />
          </div>
        </main>
      </div>
    </div>
  );
}
