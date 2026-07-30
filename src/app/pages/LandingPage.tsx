// Landing Page
// Cinematic marketing page for VERSE — AI-powered semantic continuity platform for filmmakers.
// Sections: Navbar → Hero → What is VERSE → Problems → Features → How It Works → Roles → Benefits → Future → Footer

import { useState, useEffect, useRef } from "react";
import {
  Film, Brain, Layers, Users, ArrowRight, ChevronRight, Play,
  CheckCircle, Zap, Eye, MessageSquare, GitBranch, Star,
  BarChart3, Shield, Sparkles, BookOpen, Globe,
  Twitter, Linkedin, Github, Menu, X, Clock, AlertTriangle,
} from "lucide-react";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import verseLogo from "@/imports/VERSE_LOGO_2.png";

// ─── Colour helpers ─────────────────────────────────────────────────────────────

// Inline brand-colour highlight spans — keeps text accessible and visually rich.
const VI = ({ children }: { children: React.ReactNode }) => (
  <span style={{ color: "var(--verse-violet)" }}>{children}</span>
);
const Gold = ({ children }: { children: React.ReactNode }) => (
  <span style={{ color: "var(--verse-gold)" }}>{children}</span>
);
const Mid = ({ children }: { children: React.ReactNode }) => (
  <span style={{ color: "var(--verse-midnight)" }}>{children}</span>
);

// ─── Types ─────────────────────────────────────────────────────────────────────

interface LandingPageProps {
  onGetStarted: () => void;
  onSignIn: () => void;
}

// ─── Navbar ────────────────────────────────────────────────────────────────────

// Per-section navbar themes — each maps to a distinct visual personality
const SECTION_THEMES: Record<string, {
  bg: string; border: string; shadow: string;
  linkColor: string; linkActive: string; linkHoverBg: string; linkActiveBg: string;
  indicatorGradient: string; signInColor: string; signInHoverBg: string;
  ctaBg: string; ctaShadow: string; mobileBg: string; mobileBorder: string;
  mobileLabel: string; logoFilter?: string;
}> = {
  hero: {
    bg: "linear-gradient(135deg, rgba(232,228,255,0.75) 0%, rgba(237,233,254,0.65) 60%, rgba(240,238,255,0.72) 100%)",
    border: "rgba(217,213,242,0.4)",
    shadow: "none",
    linkColor: "rgba(13,27,46,0.55)",
    linkActive: "#1D3461",
    linkHoverBg: "rgba(124,58,237,0.07)",
    linkActiveBg: "rgba(29,52,97,0.07)",
    indicatorGradient: "linear-gradient(90deg, #7C3AED, #1D3461)",
    signInColor: "#1D3461",
    signInHoverBg: "rgba(29,52,97,0.08)",
    ctaBg: "linear-gradient(135deg, #1D3461 0%, #2D1B69 100%)",
    ctaShadow: "0 2px 14px rgba(29,52,97,0.28)",
    mobileBg: "linear-gradient(160deg, rgba(240,238,255,0.98) 0%, rgba(237,233,254,0.98) 100%)",
    mobileBorder: "rgba(217,213,242,0.6)",
    mobileLabel: "#7C3AED",
  },
  about: {
    bg: "linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(248,246,255,0.96) 100%)",
    border: "rgba(196,149,18,0.12)",
    shadow: "0 4px 24px rgba(29,52,97,0.07)",
    linkColor: "rgba(13,27,46,0.55)",
    linkActive: "#1D3461",
    linkHoverBg: "rgba(196,149,18,0.07)",
    linkActiveBg: "rgba(196,149,18,0.09)",
    indicatorGradient: "linear-gradient(90deg, #C49512, #1D3461)",
    signInColor: "#1D3461",
    signInHoverBg: "rgba(29,52,97,0.07)",
    ctaBg: "linear-gradient(135deg, #1D3461 0%, #2D1B69 100%)",
    ctaShadow: "0 2px 14px rgba(29,52,97,0.25)",
    mobileBg: "linear-gradient(160deg, rgba(255,255,255,0.98) 0%, rgba(248,246,255,0.98) 100%)",
    mobileBorder: "rgba(196,149,18,0.2)",
    mobileLabel: "#C49512",
  },
  features: {
    bg: "linear-gradient(135deg, rgba(237,233,254,0.96) 0%, rgba(240,238,255,0.96) 100%)",
    border: "rgba(124,58,237,0.15)",
    shadow: "0 4px 24px rgba(124,58,237,0.08)",
    linkColor: "rgba(45,27,105,0.55)",
    linkActive: "#7C3AED",
    linkHoverBg: "rgba(124,58,237,0.08)",
    linkActiveBg: "rgba(124,58,237,0.1)",
    indicatorGradient: "linear-gradient(90deg, #7C3AED, #1D3461)",
    signInColor: "#7C3AED",
    signInHoverBg: "rgba(124,58,237,0.08)",
    ctaBg: "linear-gradient(135deg, #7C3AED 0%, #1D3461 100%)",
    ctaShadow: "0 2px 14px rgba(124,58,237,0.3)",
    mobileBg: "linear-gradient(160deg, rgba(237,233,254,0.98) 0%, rgba(240,238,255,0.98) 100%)",
    mobileBorder: "rgba(124,58,237,0.2)",
    mobileLabel: "#7C3AED",
  },
  "how-it-works": {
    bg: "linear-gradient(135deg, rgba(248,246,255,0.96) 0%, rgba(240,238,255,0.96) 100%)",
    border: "rgba(124,58,237,0.12)",
    shadow: "0 4px 20px rgba(124,58,237,0.07)",
    linkColor: "rgba(13,27,46,0.55)",
    linkActive: "#1D3461",
    linkHoverBg: "rgba(124,58,237,0.07)",
    linkActiveBg: "rgba(29,52,97,0.07)",
    indicatorGradient: "linear-gradient(90deg, #7C3AED, #1D3461)",
    signInColor: "#1D3461",
    signInHoverBg: "rgba(29,52,97,0.07)",
    ctaBg: "linear-gradient(135deg, #1D3461 0%, #2D1B69 100%)",
    ctaShadow: "0 2px 14px rgba(29,52,97,0.25)",
    mobileBg: "linear-gradient(160deg, rgba(248,246,255,0.98) 0%, rgba(240,238,255,0.98) 100%)",
    mobileBorder: "rgba(217,213,242,0.5)",
    mobileLabel: "#7C3AED",
  },
  roles: {
    bg: "linear-gradient(135deg, rgba(29,52,97,0.96) 0%, rgba(45,27,105,0.94) 100%)",
    border: "rgba(196,149,18,0.2)",
    shadow: "0 4px 28px rgba(0,0,0,0.18)",
    linkColor: "rgba(255,255,255,0.6)",
    linkActive: "rgba(255,255,255,0.95)",
    linkHoverBg: "rgba(255,255,255,0.08)",
    linkActiveBg: "rgba(255,255,255,0.1)",
    indicatorGradient: "linear-gradient(90deg, #C49512, rgba(255,255,255,0.8))",
    signInColor: "rgba(255,255,255,0.75)",
    signInHoverBg: "rgba(255,255,255,0.08)",
    ctaBg: "linear-gradient(135deg, #C49512 0%, #9A7200 100%)",
    ctaShadow: "0 2px 14px rgba(196,149,18,0.35)",
    mobileBg: "linear-gradient(160deg, rgba(29,52,97,0.98) 0%, rgba(45,27,105,0.98) 100%)",
    mobileBorder: "rgba(196,149,18,0.2)",
    mobileLabel: "#C49512",
  },
  future: {
    bg: "linear-gradient(135deg, rgba(13,27,46,0.97) 0%, rgba(29,52,97,0.97) 60%, rgba(45,27,105,0.97) 100%)",
    border: "rgba(196,149,18,0.18)",
    shadow: "0 4px 28px rgba(0,0,0,0.25)",
    linkColor: "rgba(255,255,255,0.55)",
    linkActive: "rgba(255,255,255,0.95)",
    linkHoverBg: "rgba(196,149,18,0.12)",
    linkActiveBg: "rgba(196,149,18,0.14)",
    indicatorGradient: "linear-gradient(90deg, #C49512, #E8C84A)",
    signInColor: "rgba(255,255,255,0.7)",
    signInHoverBg: "rgba(255,255,255,0.08)",
    ctaBg: "linear-gradient(135deg, #C49512 0%, #9A7200 100%)",
    ctaShadow: "0 2px 14px rgba(196,149,18,0.4)",
    mobileBg: "linear-gradient(160deg, rgba(13,27,46,0.98) 0%, rgba(45,27,105,0.98) 100%)",
    mobileBorder: "rgba(196,149,18,0.2)",
    mobileLabel: "#C49512",
  },
};

// Section → nav link label mapping
const SECTION_TO_NAV: Record<string, string> = {
  hero: "Home",
  about: "About",
  features: "Features",
  "how-it-works": "Features",
  roles: "Solutions",
  future: "Solutions",
};

function Navbar({ onGetStarted, onSignIn }: LandingPageProps) {
  const [activeSection, setActiveSection] = useState("hero");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // IntersectionObserver — watches all tagged sections, picks most visible
  useEffect(() => {
    const sectionIds = ["hero", "about", "features", "how-it-works", "roles", "future"];
    const ratios: Record<string, number> = {};

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          ratios[entry.target.id] = entry.intersectionRatio;
        });
        // Pick section with highest intersection ratio
        const top = Object.entries(ratios).sort((a, b) => b[1] - a[1])[0];
        if (top && top[1] > 0) setActiveSection(top[0]);
      },
      { threshold: [0, 0.1, 0.25, 0.5, 0.75, 1] }
    );

    sectionIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observerRef.current!.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  const theme = SECTION_THEMES[activeSection] ?? SECTION_THEMES.hero;
  const activeNavLabel = SECTION_TO_NAV[activeSection] ?? "Home";

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
    setIsMobileMenuOpen(false);
  };

  const navLinks = [
    { label: "Home", action: () => { window.scrollTo({ top: 0, behavior: "smooth" }); setIsMobileMenuOpen(false); } },
    { label: "Features", action: () => scrollTo("features") },
    { label: "Solutions", action: () => scrollTo("roles") },
    { label: "AI Technology", action: () => scrollTo("about") },
    { label: "About", action: () => scrollTo("about") },
  ];

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50"
      style={{
        background: theme.bg,
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderBottom: `1px solid ${theme.border}`,
        boxShadow: theme.shadow,
        transition: "background 0.6s ease, border-color 0.6s ease, box-shadow 0.6s ease",
      }}
    >
      {/* Top accent line — brand gradient, always visible */}
      <div
        className="h-[2px] w-full"
        style={{ background: "linear-gradient(90deg, #1D3461 0%, #7C3AED 50%, #C49512 100%)" }}
      />

      <div
        className="max-w-7xl mx-auto px-6 flex items-center justify-between gap-6"
        style={{ height: "108px", overflow: "visible" }}
      >
        {/* VERSE Logo — aggressively enlarged, dominant brand anchor */}
        <button
          onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); setIsMobileMenuOpen(false); }}
          className="flex items-center flex-shrink-0 group focus:outline-none overflow-visible"
          aria-label="VERSE — Home"
          style={{
            filter: activeSection === "roles" || activeSection === "future" ? "brightness(0) invert(1)" : "none",
            transition: "filter 0.5s ease",
            overflow: "visible",
          }}
        >
          <ImageWithFallback
            src={verseLogo}
            alt="VERSE"
            style={{
              height: "96px",
              width: "auto",
              objectFit: "contain",
              transform: "scale(1.58)",
              transformOrigin: "left center",
              transition: "transform 0.25s ease",
            }}
            className="group-hover:!scale-[1.66]"
          />
        </button>

        {/* Desktop Nav Links */}
        <div className="hidden md:flex items-center gap-0.5 flex-1 justify-center">
          {navLinks.map((link) => {
            const isActive = activeNavLabel === link.label;
            return (
              <button
                key={link.label}
                onClick={link.action}
                className="relative px-4 py-2.5 rounded-xl text-sm font-semibold whitespace-nowrap focus:outline-none"
                style={{
                  color: isActive ? theme.linkActive : theme.linkColor,
                  background: isActive ? theme.linkActiveBg : "transparent",
                  letterSpacing: "0.012em",
                  transition: "color 0.5s ease, background 0.3s ease",
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.color = theme.linkActive;
                    (e.currentTarget as HTMLElement).style.background = theme.linkHoverBg;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    (e.currentTarget as HTMLElement).style.color = theme.linkColor;
                    (e.currentTarget as HTMLElement).style.background = "transparent";
                  }
                }}
              >
                {link.label}
                {isActive && (
                  <span
                    className="absolute bottom-1 left-4 right-4 h-[2px] rounded-full"
                    style={{ background: theme.indicatorGradient, transition: "background 0.5s ease" }}
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* Desktop Auth */}
        <div className="hidden md:flex items-center gap-2.5 flex-shrink-0">
          <button
            onClick={onSignIn}
            className="text-sm font-semibold px-4 py-2.5 rounded-xl focus:outline-none"
            style={{ color: theme.signInColor, transition: "color 0.5s ease, background 0.3s ease" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = theme.signInHoverBg; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
          >
            Sign In
          </button>
          <button
            onClick={onGetStarted}
            className="text-sm font-bold px-6 py-2.5 rounded-xl text-white focus:outline-none flex items-center gap-1.5 hover:-translate-y-px"
            style={{
              background: theme.ctaBg,
              boxShadow: theme.ctaShadow,
              transition: "background 0.5s ease, box-shadow 0.3s ease, transform 0.2s ease",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = theme.ctaShadow.replace("0.28", "0.45").replace("0.25", "0.4").replace("0.3)", "0.45)").replace("0.35", "0.5").replace("0.4)", "0.55)"); }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.boxShadow = theme.ctaShadow; }}
          >
            Get Started <ArrowRight size={13} />
          </button>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden w-10 h-10 rounded-xl flex items-center justify-center focus:outline-none transition-all"
          style={{ color: theme.linkActive, background: theme.linkActiveBg }}
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div
          className="md:hidden border-t"
          style={{
            background: theme.mobileBg,
            backdropFilter: "blur(24px)",
            borderColor: theme.mobileBorder,
            transition: "background 0.5s ease",
          }}
        >
          <div className="px-5 pt-4 pb-1.5">
            <p className="text-[10px] font-black tracking-[0.15em] uppercase" style={{ color: theme.mobileLabel, opacity: 0.7 }}>Navigation</p>
          </div>
          <div className="px-3 pb-3 flex flex-col gap-0.5">
            {navLinks.map((link) => {
              const isActive = activeNavLabel === link.label;
              return (
                <button
                  key={link.label}
                  onClick={link.action}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl text-sm font-semibold text-left transition-all"
                  style={{
                    color: isActive ? theme.linkActive : theme.linkColor,
                    background: isActive ? theme.linkActiveBg : "transparent",
                  }}
                >
                  {link.label}
                  {isActive && <ChevronRight size={14} style={{ color: theme.mobileLabel }} />}
                </button>
              );
            })}
          </div>
          <div className="px-4 pt-2 pb-5 flex flex-col gap-3 border-t" style={{ borderColor: theme.mobileBorder }}>
            <button
              onClick={onSignIn}
              className="w-full h-11 text-sm font-semibold rounded-xl border transition-all"
              style={{ color: theme.signInColor, borderColor: theme.mobileBorder, background: theme.signInHoverBg }}
            >
              Sign In
            </button>
            <button
              onClick={onGetStarted}
              className="w-full h-11 text-sm font-bold rounded-xl text-white flex items-center justify-center gap-2 transition-all"
              style={{ background: theme.ctaBg, boxShadow: theme.ctaShadow }}
            >
              Get Started <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}

// ─── Hero Section ──────────────────────────────────────────────────────────────

function HeroSection({ onGetStarted }: { onGetStarted: () => void }) {
  const stats = [
    {
      value: "10,000+", label: "Scenes Analyzed",      sublabel: "AI Continuity Engine",
      icon: Film,   color: "#A78BFA", glowColor: "rgba(167,139,250,0.25)",
      description: "Frames analyzed and indexed",
    },
    {
      value: "99.2%",  label: "Continuity Accuracy",  sublabel: "Semantic Precision",
      icon: Shield, color: "#E8C84A", glowColor: "rgba(232,200,74,0.22)",
      description: "AI-verified scene consistency",
    },
    {
      value: "500+",   label: "Productions Worldwide", sublabel: "Global Studios",
      icon: Globe,  color: "#60A5FA", glowColor: "rgba(96,165,250,0.22)",
      description: "Features, series & campaigns",
    },
    {
      value: "<50ms",  label: "Avg. Response Time",    sublabel: "Real-Time Analysis",
      icon: Zap,    color: "#34D399", glowColor: "rgba(52,211,153,0.20)",
      description: "Live on-set continuity checks",
    },
  ];

  return (
    <section
      id="hero"
      className="relative overflow-hidden"
      style={{
        background: "linear-gradient(170deg, #0A0F1E 0%, #0D1B2E 30%, #111830 60%, #130E28 100%)",
        paddingTop: "140px",
        paddingBottom: "96px",
      }}
    >
      {/* ── Layered cinematic background atmosphere ── */}

      {/* Base noise / film grain */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true" style={{
        backgroundImage:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
        opacity: 0.6,
      }} />

      {/* Primary radial glows — midnight blue anchor left, violet AI glow right */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true" style={{
        background:
          "radial-gradient(ellipse 80% 60% at 0% 0%,   rgba(29,52,97,0.55)  0%, transparent 55%)," +
          "radial-gradient(ellipse 70% 55% at 100% 90%, rgba(124,58,237,0.40) 0%, transparent 50%)," +
          "radial-gradient(ellipse 60% 45% at 50%  0%,  rgba(45,27,105,0.30) 0%, transparent 55%)," +
          "radial-gradient(ellipse 50% 35% at 50% 100%, rgba(196,149,18,0.12) 0%, transparent 50%)",
      }} />

      {/* Fine dot grid */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true" style={{
        backgroundImage: "radial-gradient(circle, rgba(124,58,237,0.18) 1px, transparent 1px)",
        backgroundSize: "32px 32px",
        opacity: 0.5,
      }} />

      {/* Subtle horizontal scan-line texture */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true" style={{
        backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(124,58,237,0.025) 3px, rgba(124,58,237,0.025) 4px)",
      }} />

      {/* Left cinematic edge accent */}
      <div className="absolute left-0 top-0 bottom-0 w-[3px] pointer-events-none" aria-hidden="true" style={{
        background: "linear-gradient(180deg, transparent 0%, rgba(124,58,237,0.6) 30%, rgba(196,149,18,0.4) 70%, transparent 100%)",
      }} />

      {/* ── Main content ── */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">

        {/* ── IBM Technology Partnership Badge ── */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-10">

          {/* IBM partnership — segmented pill */}
          <div
            className="inline-flex items-stretch rounded-xl border overflow-hidden"
            style={{
              background: "linear-gradient(135deg, rgba(8,14,30,0.98) 0%, rgba(20,36,70,0.96) 50%, rgba(35,20,75,0.95) 100%)",
              borderColor: "rgba(124,58,237,0.45)",
              boxShadow:
                "0 0 0 1px rgba(255,255,255,0.04), " +
                "0 4px 24px rgba(0,0,0,0.5), " +
                "0 0 32px rgba(124,58,237,0.12), " +
                "inset 0 1px 0 rgba(255,255,255,0.07)",
              backdropFilter: "blur(16px)",
            }}
          >
            {/* "Powered by" */}
            <div
              className="flex items-center gap-1.5 px-3.5 py-2.5 border-r"
              style={{ borderColor: "rgba(124,58,237,0.22)" }}
            >
              <Sparkles size={9} style={{ color: "#A78BFA" }} />
              <span
                className="text-[8.5px] font-black tracking-[0.22em] uppercase"
                style={{ color: "rgba(167,139,250,0.55)" }}
              >
                Powered by
              </span>
            </div>

            {/* IBM watsonx */}
            <div
              className="flex items-center gap-2 px-3.5 py-2.5 border-r"
              style={{ borderColor: "rgba(124,58,237,0.22)" }}
            >
              <div
                className="w-4 h-4 rounded-[4px] flex items-center justify-center flex-shrink-0"
                style={{
                  background: "linear-gradient(135deg, #1D3461 0%, #4C3BAB 100%)",
                  boxShadow: "0 0 6px rgba(76,59,171,0.5)",
                }}
              >
                <Brain size={9} className="text-white" />
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-[8px] font-bold tracking-[0.12em] uppercase" style={{ color: "rgba(196,181,253,0.45)" }}>IBM</span>
                <span className="text-[11px] font-black tracking-tight" style={{ color: "#C4B5FD" }}>watsonx</span>
              </div>
            </div>

            {/* + connector */}
            <div className="flex items-center px-2.5 py-2.5">
              <span className="text-[11px] font-black" style={{ color: "rgba(167,139,250,0.35)" }}>+</span>
            </div>

            {/* IBM Granite */}
            <div className="flex items-center gap-2 px-3.5 py-2.5">
              <div
                className="w-4 h-4 rounded-[4px] flex items-center justify-center flex-shrink-0"
                style={{
                  background: "linear-gradient(135deg, #6D28D9 0%, #B45309 100%)",
                  boxShadow: "0 0 6px rgba(196,149,18,0.4)",
                }}
              >
                <Layers size={9} className="text-white" />
              </div>
              <div className="flex flex-col leading-none">
                <span className="text-[8px] font-bold tracking-[0.12em] uppercase" style={{ color: "rgba(232,200,74,0.45)" }}>IBM</span>
                <span className="text-[11px] font-black tracking-tight" style={{ color: "#E8C84A" }}>Granite</span>
              </div>
            </div>
          </div>

          {/* Film production badge */}
          <div
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2.5 border"
            style={{
              background: "linear-gradient(135deg, rgba(196,149,18,0.12) 0%, rgba(196,149,18,0.06) 100%)",
              borderColor: "rgba(196,149,18,0.35)",
              backdropFilter: "blur(10px)",
              boxShadow: "0 0 16px rgba(196,149,18,0.08), inset 0 1px 0 rgba(255,255,255,0.05)",
            }}
          >
            <Film size={11} style={{ color: "#E8C84A" }} />
            <span
              className="text-[10px] font-black tracking-[0.2em] uppercase"
              style={{ color: "#E8C84A" }}
            >
              Built for Film Production
            </span>
          </div>
        </div>

        {/* ── VERSE acronym card ── */}
        <div
          className="inline-flex items-center gap-3 rounded-2xl px-6 py-3.5 mb-8 border"
          style={{
            background: "linear-gradient(135deg, rgba(13,27,46,0.90) 0%, rgba(29,52,97,0.82) 45%, rgba(45,27,105,0.80) 100%)",
            backdropFilter: "blur(20px)",
            borderColor: "rgba(124,58,237,0.40)",
            boxShadow:
              "0 0 0 1px rgba(255,255,255,0.04), " +
              "0 4px 24px rgba(0,0,0,0.4), " +
              "0 0 40px rgba(124,58,237,0.15), " +
              "inset 0 1px 0 rgba(255,255,255,0.06)",
          }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background: "linear-gradient(135deg, #1D3461 0%, #7C3AED 100%)",
              boxShadow: "0 0 12px rgba(124,58,237,0.4)",
            }}
          >
            <Brain size={14} className="text-white" />
          </div>
          <p className="text-sm font-medium tracking-wide" style={{ color: "rgba(196,181,253,0.80)" }}>
            <span className="font-black text-base" style={{ color: "#A78BFA" }}>V</span>isual {"&"}{" "}
            <span className="font-black text-base" style={{ color: "#A78BFA" }}>E</span>xplainable{" "}
            <span className="font-black text-base" style={{ color: "#A78BFA" }}>R</span>easoning for{" "}
            <span className="font-black text-base" style={{ color: "#E8C84A" }}>S</span>emantic{" "}
            <span className="font-black text-base" style={{ color: "#E8C84A" }}>E</span>volution
          </p>
        </div>

        {/* ── Primary headline ── */}
        <h1
          className="font-black tracking-tight leading-[0.95] mb-6"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(3.2rem, 8vw, 5.75rem)",
          }}
        >
          <span style={{ color: "rgba(240,238,255,0.95)" }}>Every story lives in</span>
          <br />
          <span style={{
            background: "linear-gradient(135deg, #7C9FE0 0%, #A78BFA 35%, #C4B5FD 55%, #E8C84A 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            filter: "drop-shadow(0 0 32px rgba(167,139,250,0.35))",
          }}>
            its own VERSE.
          </span>
        </h1>

        {/* ── AI capability tags row ── */}
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-1.5 mb-7">
          {[
            { label: "AI-Powered Semantic Continuity", color: "#A78BFA" },
            { label: "Production Intelligence",        color: "#E8C84A" },
            { label: "Intelligent Filmmaking",         color: "#60A5FA" },
          ].map((tag, i) => (
            <div key={tag.label} className="flex items-center gap-2">
              {i > 0 && (
                <span className="text-[11px]" style={{ color: "rgba(167,139,250,0.25)" }}>·</span>
              )}
              <span
                className="text-[11px] font-bold tracking-[0.16em] uppercase"
                style={{ color: tag.color, opacity: 0.8 }}
              >
                {tag.label}
              </span>
            </div>
          ))}
        </div>

        {/* ── Supporting description ── */}
        <p
          className="text-base sm:text-lg max-w-2xl mx-auto mb-10 leading-relaxed"
          style={{ color: "rgba(196,181,253,0.65)" }}
        >
          An AI system built to{" "}
          <span className="font-semibold" style={{ color: "#A78BFA" }}>understand, reason, and evolve</span>{" "}
          with the visual and narrative complexity of film production —
          preserving{" "}
          <span className="font-semibold" style={{ color: "#E8C84A" }}>story integrity</span>{" "}
          from screenplay to final cut.
        </p>

        {/* ── CTA button row ── */}
        <div className="flex flex-wrap items-center justify-center gap-3 mb-14">

          {/* Primary CTA */}
          <button
            onClick={onGetStarted}
            className="group relative flex items-center gap-2.5 text-white font-bold px-9 py-4 rounded-xl overflow-hidden transition-all duration-300 hover:-translate-y-1"
            style={{
              background: "linear-gradient(135deg, #1D3461 0%, #4C3BAB 50%, #7C3AED 100%)",
              boxShadow: "0 4px 24px rgba(124,58,237,0.40), 0 0 0 1px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.15)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.boxShadow =
                "0 10px 40px rgba(124,58,237,0.60), 0 0 0 1px rgba(255,255,255,0.12), inset 0 1px 0 rgba(255,255,255,0.2)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.boxShadow =
                "0 4px 24px rgba(124,58,237,0.40), 0 0 0 1px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.15)";
            }}
          >
            {/* Shine overlay */}
            <div
              className="absolute inset-0 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.10) 0%, transparent 60%)" }}
            />
            <span className="relative">Get Started Free</span>
            <ArrowRight size={17} className="relative group-hover:translate-x-1 transition-transform duration-200" />
          </button>

          {/* Secondary — Watch Demo */}
          <button
            className="group flex items-center gap-2.5 font-semibold px-8 py-4 rounded-xl transition-all duration-200 border hover:-translate-y-1"
            style={{
              background: "rgba(124,58,237,0.10)",
              borderColor: "rgba(124,58,237,0.40)",
              color: "#C4B5FD",
              backdropFilter: "blur(10px)",
              boxShadow: "0 0 0 1px rgba(255,255,255,0.04), inset 0 1px 0 rgba(255,255,255,0.06)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(124,58,237,0.18)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(124,58,237,0.65)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(124,58,237,0.10)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(124,58,237,0.40)";
            }}
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 transition-all group-hover:scale-110"
              style={{
                background: "linear-gradient(135deg, rgba(124,58,237,0.3) 0%, rgba(124,58,237,0.15) 100%)",
                border: "1px solid rgba(124,58,237,0.5)",
              }}
            >
              <Play size={10} style={{ color: "#C4B5FD" }} className="ml-0.5" />
            </div>
            Watch Demo
          </button>

          {/* Tertiary — Explore Features */}
          <button
            onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })}
            className="flex items-center gap-1.5 text-sm font-semibold py-4 px-5 transition-all hover:-translate-y-0.5 rounded-xl"
            style={{ color: "rgba(196,181,253,0.55)" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "rgba(196,181,253,0.9)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "rgba(196,181,253,0.55)"; }}
          >
            Explore Features <ChevronRight size={15} className="mt-px" />
          </button>
        </div>

        {/* ── Divider with trust label ── */}
        <div className="flex items-center gap-4 mb-9 max-w-sm mx-auto">
          <div className="flex-1 h-px" style={{ background: "linear-gradient(to right, transparent, rgba(124,58,237,0.30))" }} />
          <span
            className="text-[9px] font-bold tracking-[0.22em] uppercase whitespace-nowrap"
            style={{ color: "rgba(167,139,250,0.35)" }}
          >
            Trusted by Productions Worldwide
          </span>
          <div className="flex-1 h-px" style={{ background: "linear-gradient(to left, transparent, rgba(124,58,237,0.30))" }} />
        </div>

        {/* ── AI Capability stat cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.label}
                className="group relative rounded-2xl p-5 border text-left overflow-hidden cursor-default"
                style={{
                  background: "linear-gradient(150deg, rgba(10,16,34,0.98) 0%, rgba(18,30,60,0.95) 50%, rgba(28,16,58,0.92) 100%)",
                  borderColor: `${stat.color}28`,
                  backdropFilter: "blur(20px)",
                  boxShadow: `0 4px 24px rgba(0,0,0,0.40), 0 0 0 1px rgba(255,255,255,0.03), inset 0 1px 0 rgba(255,255,255,0.05)`,
                  transition: "transform 0.28s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.28s ease, border-color 0.28s ease",
                }}
                onMouseEnter={(e) => {
                  const el = e.currentTarget as HTMLDivElement;
                  el.style.transform = "translateY(-8px)";
                  el.style.boxShadow = `0 20px 48px rgba(0,0,0,0.5), 0 0 32px ${stat.glowColor}, inset 0 1px 0 rgba(255,255,255,0.08)`;
                  el.style.borderColor = `${stat.color}55`;
                }}
                onMouseLeave={(e) => {
                  const el = e.currentTarget as HTMLDivElement;
                  el.style.transform = "translateY(0)";
                  el.style.boxShadow = `0 4px 24px rgba(0,0,0,0.40), 0 0 0 1px rgba(255,255,255,0.03), inset 0 1px 0 rgba(255,255,255,0.05)`;
                  el.style.borderColor = `${stat.color}28`;
                }}
              >
                {/* Ambient glow layer — always on at low opacity */}
                <div
                  className="absolute inset-0 pointer-events-none rounded-2xl opacity-30 group-hover:opacity-60 transition-opacity duration-400"
                  style={{ background: `radial-gradient(ellipse 80% 70% at 10% 10%, ${stat.glowColor} 0%, transparent 65%)` }}
                />

                {/* Top accent line — always partially visible */}
                <div
                  className="absolute top-0 left-0 right-0 h-[1.5px] pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity duration-300"
                  style={{ background: `linear-gradient(90deg, transparent 5%, ${stat.color} 40%, ${stat.color} 60%, transparent 95%)` }}
                />

                {/* Side accent line */}
                <div
                  className="absolute top-4 bottom-4 left-0 w-[1.5px] pointer-events-none opacity-0 group-hover:opacity-70 transition-opacity duration-400"
                  style={{ background: `linear-gradient(180deg, transparent, ${stat.color}, transparent)` }}
                />

                <div className="relative z-10">
                  {/* Icon + sublabel */}
                  <div className="flex items-start justify-between mb-5">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{
                        background: `linear-gradient(135deg, ${stat.color}25 0%, ${stat.color}12 100%)`,
                        border: `1px solid ${stat.color}40`,
                        boxShadow: `0 0 12px ${stat.glowColor}`,
                      }}
                    >
                      <Icon size={16} style={{ color: stat.color }} />
                    </div>
                    <div className="text-right">
                      <span
                        className="block text-[8.5px] font-black tracking-[0.18em] uppercase leading-tight"
                        style={{ color: stat.color }}
                      >
                        {stat.sublabel}
                      </span>
                    </div>
                  </div>

                  {/* Big value */}
                  <p
                    className="font-black leading-none mb-1.5"
                    style={{
                      fontFamily: "var(--font-display)",
                      fontSize: "clamp(1.6rem, 4vw, 2.2rem)",
                      color: "#F0EEFF",
                      letterSpacing: "-0.02em",
                    }}
                  >
                    {stat.value}
                  </p>

                  {/* Label */}
                  <p
                    className="text-[11px] font-semibold leading-snug mb-1"
                    style={{ color: "rgba(196,181,253,0.70)" }}
                  >
                    {stat.label}
                  </p>

                  {/* Description micro-text */}
                  <p
                    className="text-[9.5px] leading-snug opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    style={{ color: "rgba(196,181,253,0.40)" }}
                  >
                    {stat.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}

// ─── What is VERSE ─────────────────────────────────────────────────────────────

function WhatIsVerseSection() {
  const pillars = [
    {
      icon: Brain,
      color: "var(--verse-midnight)",
      bg: "var(--verse-midnight-light)",
      title: "Semantic Production Memory",
      description:
        "VERSE builds a rich, queryable memory of your entire production — every character state, costume, prop, and timeline event — so nothing is ever lost or forgotten.",
      highlight: "semantic production memory",
    },
    {
      icon: Eye,
      color: "var(--verse-violet)",
      bg: "var(--verse-violet-light)",
      title: "Explainable AI",
      description:
        "Every AI recommendation includes a plain-language explanation and confidence score. No black boxes. Full transparency in every decision.",
      highlight: "explainable AI",
    },
    {
      icon: GitBranch,
      color: "var(--verse-gold)",
      bg: "var(--verse-gold-light)",
      title: "AI Continuity Intelligence",
      description:
        "VERSE's continuity engine cross-references scenes, shots, and characters in real time, catching inconsistencies before they become costly on-set problems.",
      highlight: "continuity intelligence",
    },
    {
      icon: Users,
      color: "var(--verse-emerald)",
      bg: "#ECFDF5",
      title: "Human-AI Collaboration",
      description:
        "VERSE is not a replacement — it's your most attentive team member. AI surfaces insights; humans make the final call. Always.",
      highlight: "human-AI collaboration",
    },
  ];

  return (
    <section id="about" className="py-20 px-6" style={{ background: "linear-gradient(180deg, #F0EEFF 0%, #F5F3FF 100%)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="max-w-2xl mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>What is VERSE?</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            The <VI>intelligent memory system</VI> your production has always needed.
          </h2>
          <p className="text-base leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
            VERSE is a purpose-built <VI>semantic production intelligence</VI> platform — powered by{" "}
            <Mid>IBM watsonx</Mid> enterprise AI and <Mid>IBM Granite</Mid> foundation models — that understands filmmaking from screenplay to final cut.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {pillars.map((pillar) => {
            const Icon = pillar.icon;
            return (
              <div
                key={pillar.title}
                className="group p-7 rounded-2xl border transition-all duration-300 hover:shadow-lg"
                style={{
                  background: `linear-gradient(135deg, color-mix(in srgb, ${pillar.color} 6%, #F5F3FF) 0%, color-mix(in srgb, ${pillar.color} 13%, #EDE9FE) 100%)`,
                  borderColor: `color-mix(in srgb, ${pillar.color} 22%, #D9D5F2)`,
                }}
              >
                <div
                  className="w-11 h-11 rounded-xl flex items-center justify-center mb-5"
                  style={{ backgroundColor: pillar.bg }}
                >
                  <Icon size={22} style={{ color: pillar.color }} />
                </div>
                <h3
                  className="text-lg font-bold text-foreground mb-2.5"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {pillar.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
                  {pillar.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── Problems We Solve ─────────────────────────────────────────────────────────

function ProblemsSection() {
  const problems = [
    {
      icon: AlertTriangle,
      color: "var(--verse-red)",
      title: "Continuity Errors",
      description:
        "A character's coffee cup switches hands between cuts. Her earrings disappear in the next scene. These small errors destroy audience immersion and cost studios millions in reshoots.",
    },
    {
      icon: MessageSquare,
      color: "var(--verse-gold)",
      title: "Narrative Inconsistencies",
      description:
        "A character references an event that hasn't happened yet in the story. A timeline contradiction buried in 120 pages of screenplay goes unnoticed until post-production.",
    },
    {
      icon: Layers,
      color: "var(--verse-midnight)",
      title: "Fragmented Production Knowledge",
      description:
        "Costume logs live in one spreadsheet. Prop inventories in another. Scene notes in a physical binder. Critical continuity knowledge is scattered, siloed, and inaccessible.",
    },
    {
      icon: Clock,
      color: "var(--verse-violet)",
      title: "Manual Continuity Tracking",
      description:
        "Script supervisors manually cross-reference hundreds of scenes with handwritten notes. Human error is inevitable. The process is slow, exhausting, and unsustainable at scale.",
    },
    {
      icon: Users,
      color: "var(--verse-emerald)",
      title: "Departmental Silos",
      description:
        "Costume, props, lighting, and production departments work in isolation. Critical continuity context never reaches the people who need it — until it's too late.",
    },
  ];

  return (
    <section
      className="py-20 px-6"
      style={{ background: "linear-gradient(180deg, #F5F3FF 0%, #EDE9FE 100%)" }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>Problems We Solve</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            <Gold>Production continuity</Gold> is broken. VERSE fixes it.
          </h2>
          <p className="text-base" style={{ color: "var(--muted-foreground)" }}>
            The film industry loses hundreds of millions annually to continuity errors, reshoots, and fragmented workflows.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {problems.map((problem) => {
            const Icon = problem.icon;
            return (
              <div
                key={problem.title}
                className="p-6 rounded-2xl border hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${problem.color} 7%, #F5F3FF) 0%, color-mix(in srgb, ${problem.color} 13%, #EDE9FE) 100%)`, borderColor: `color-mix(in srgb, ${problem.color} 22%, #D9D5F2)` }}
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                  style={{ backgroundColor: `color-mix(in srgb, ${problem.color} 12%, white)` }}
                >
                  <Icon size={20} style={{ color: problem.color }} />
                </div>
                <h3 className="text-base font-bold text-foreground mb-2" style={{ fontFamily: "var(--font-display)" }}>
                  {problem.title}
                </h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>{problem.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── Core Features ─────────────────────────────────────────────────────────────

function FeaturesSection() {
  const features = [
    { icon: BookOpen, badge: "AI Core", badgeColor: "var(--verse-violet)", title: "Screenplay Understanding Engine", description: "Deep semantic parsing of your screenplay — characters, timelines, locations, props, and relationships all extracted automatically." },
    { icon: Brain, badge: "Memory", badgeColor: "var(--verse-midnight)", title: "Semantic Production Memory", description: "A persistent, queryable memory of every production detail across scenes, shots, and departments." },
    { icon: Zap, badge: "Intelligence", badgeColor: "var(--verse-violet)", title: "Continuity Intelligence Engine", description: "Real-time continuity analysis with AI-powered anomaly detection and scene-by-scene cross-referencing." },
    { icon: Eye, badge: "Transparency", badgeColor: "var(--verse-gold)", title: "Explainable AI Recommendations", description: "Every AI insight comes with a plain-language explanation and confidence score — no black boxes." },
    { icon: GitBranch, badge: "Graph AI", badgeColor: "var(--verse-violet)", title: "Knowledge Graph Intelligence", description: "A dynamic semantic knowledge graph connecting characters, locations, costumes, props, and events." },
    { icon: Users, badge: "Collaboration", badgeColor: "var(--verse-midnight)", title: "Collaborative Workspace", description: "Role-based access for producers, directors, script supervisors, and department heads — all in one unified workspace." },
    { icon: Film, badge: "Tracking", badgeColor: "var(--verse-gold)", title: "Character Tracking", description: "Comprehensive character state tracking across every scene — costumes, props, emotional state, and physical continuity." },
    { icon: BarChart3, badge: "Analytics", badgeColor: "var(--verse-midnight)", title: "Production Insights", description: "Actionable analytics on continuity health, scene completion, and AI recommendation adoption." },
    { icon: Shield, badge: "Risk AI", badgeColor: "var(--verse-violet)", title: "Production Risk Detection", description: "Proactive identification of narrative, visual, and timeline risks before they become expensive on-set problems." },
  ];

  return (
    <section id="features" className="py-20 px-6" style={{ background: "linear-gradient(180deg, #EDE9FE 0%, #F0EEFF 100%)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>Core Features</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            <VI>Intelligence</VI> built for the <Gold>film production</Gold> workflow.
          </h2>
          <p className="text-base" style={{ color: "var(--muted-foreground)" }}>
            VERSE brings together <VI>semantic AI</VI>, <Gold>production memory</Gold>, and{" "}
            <Mid>collaborative tools</Mid> into one unified platform — powered by IBM watsonx.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group p-6 rounded-2xl border hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 cursor-default"
                style={{
                  background: `linear-gradient(135deg, color-mix(in srgb, ${feature.badgeColor} 6%, #F5F3FF) 0%, color-mix(in srgb, ${feature.badgeColor} 12%, #EDE9FE) 100%)`,
                  borderColor: `color-mix(in srgb, ${feature.badgeColor} 20%, #D9D5F2)`,
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `color-mix(in srgb, ${feature.badgeColor} 16%, white)`, border: `1px solid color-mix(in srgb, ${feature.badgeColor} 22%, transparent)` }}
                  >
                    <Icon size={19} style={{ color: feature.badgeColor }} />
                  </div>
                  <span
                    className="text-xs font-bold tracking-wide uppercase px-2 py-1 rounded-md"
                    style={{
                      backgroundColor: `color-mix(in srgb, ${feature.badgeColor} 12%, white)`,
                      color: feature.badgeColor,
                    }}
                  >
                    {feature.badge}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-foreground mb-2" style={{ fontFamily: "var(--font-display)" }}>
                  {feature.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: "var(--muted-foreground)" }}>{feature.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── How It Works ──────────────────────────────────────────────────────────────

function HowItWorksSection() {
  const steps = [
    { number: "01", title: "Screenplay Upload", description: "Upload your screenplay in any format. VERSE extracts semantic meaning, character relationships, timelines, and production details automatically.", color: "var(--verse-midnight)" },
    { number: "02", title: "AI Semantic Analysis", description: "VERSE's AI engine performs deep semantic analysis — understanding narrative structure, character arcs, and scene dependencies across the entire screenplay.", color: "var(--verse-violet)" },
    { number: "03", title: "Production Memory Construction", description: "A dynamic semantic knowledge graph is built, capturing every detail of your production — costumes, props, character states, locations, and timelines.", color: "var(--verse-violet)" },
    { number: "04", title: "Continuity Verification", description: "As scenes are filmed, VERSE continuously cross-references logged data against the production memory, detecting continuity anomalies in real time.", color: "var(--verse-gold)" },
    { number: "05", title: "AI Recommendations", description: "VERSE generates explainable AI recommendations with confidence scores and clear reasoning — actionable, transparent insights your team can trust.", color: "var(--verse-gold)" },
    { number: "06", title: "Human Verification", description: "Your team reviews, accepts, or rejects AI recommendations. VERSE learns from every decision, continuously improving its understanding of your production.", color: "var(--verse-emerald)" },
    { number: "07", title: "Production Dashboard", description: "A role-based production workspace gives every team member exactly the information they need — tailored to their responsibilities and access level.", color: "var(--verse-midnight)" },
  ];

  return (
    <section
      id="how-it-works"
      className="py-20 px-6"
      style={{ background: "linear-gradient(180deg, #EDE9FE 0%, #F0EEFF 50%, #FDF8EC 100%)" }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>How VERSE Works</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            From <Gold>screenplay</Gold> to <VI>intelligent production workspace</VI>.
          </h2>
        </div>

        <div className="relative max-w-3xl mx-auto">
          <div className="absolute left-8 top-0 bottom-0 w-px hidden md:block" style={{ background: "linear-gradient(to bottom, rgba(29,52,97,0.3), rgba(124,58,237,0.15), transparent)" }} />

          <div className="flex flex-col gap-5">
            {steps.map((step) => (
              <div key={step.number} className="relative flex gap-5 group">
                <div
                  className="relative z-10 flex-shrink-0 w-16 h-16 rounded-2xl flex items-center justify-center shadow-sm"
                  style={{ backgroundColor: step.color }}
                >
                  <span className="text-white font-black text-sm" style={{ fontFamily: "var(--font-mono)" }}>
                    {step.number}
                  </span>
                </div>
                <div
                  className="flex-1 rounded-2xl border p-5 transition-all group-hover:shadow-sm"
                  style={{
                    background: `linear-gradient(135deg, color-mix(in srgb, ${step.color} 8%, #F5F3FF) 0%, color-mix(in srgb, ${step.color} 15%, #EDE9FE) 100%)`,
                    borderColor: `color-mix(in srgb, ${step.color} 25%, #D9D5F2)`,
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <h3 className="text-base font-bold text-foreground mb-1.5" style={{ fontFamily: "var(--font-display)" }}>
                    {step.title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── User Roles ────────────────────────────────────────────────────────────────

function UserRolesSection() {
  const roles = [
    { icon: "🎬", title: "Producer", color: "var(--verse-midnight)", tagline: "Command the production.", features: ["Production overview", "Team management", "Continuity reports", "AI analytics"] },
    { icon: "🎭", title: "Director", color: "var(--verse-violet)", tagline: "Drive creative vision.", features: ["Scene tracking", "Character states", "AI recommendations", "Timeline view"] },
    { icon: "📋", title: "Script Supervisor", color: "#0F62FE", tagline: "Own continuity.", features: ["Continuity tracking", "Screenplay analysis", "AI alerts", "Scene timeline"] },
    { icon: "🔍", title: "Continuity Supervisor", color: "var(--verse-emerald)", tagline: "Verify every detail.", features: ["Costume tracking", "Prop continuity", "Timeline verification", "Production memory"] },
    { icon: "📊", title: "Production Manager", color: "var(--verse-gold)", tagline: "Coordinate everything.", features: ["Team collaboration", "Scheduling", "Workspace management", "Reports"] },
    { icon: "🎓", title: "Film Student", color: "var(--verse-red)", tagline: "Learn and experiment.", features: ["Demo workspace", "Tutorials", "Sample productions", "Educational tools"] },
  ];

  return (
    <section id="roles" className="py-20 px-6" style={{ background: "linear-gradient(180deg, #F0EEFF 0%, #EDE9FE 50%, #E8E3FD 100%)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>Built for Every Role</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Every team member. <VI>One intelligent workspace.</VI>
          </h2>
          <p className="text-base" style={{ color: "var(--muted-foreground)" }}>
            VERSE adapts to the unique needs of every role in your production.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {roles.map((role) => (
            <div
              key={role.title}
              className="group p-6 rounded-2xl border hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
              style={{
                background: `linear-gradient(135deg, color-mix(in srgb, ${role.color} 6%, #F5F3FF) 0%, color-mix(in srgb, ${role.color} 14%, #EDE9FE) 100%)`,
                borderColor: `color-mix(in srgb, ${role.color} 22%, #D9D5F2)`,
              }}
            >
              <div
                className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl mb-5"
                style={{ backgroundColor: `color-mix(in srgb, ${role.color} 14%, white)` }}
              >
                {role.icon}
              </div>
              <h3 className="text-lg font-black text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                {role.title}
              </h3>
              <p className="text-sm font-semibold mb-4 mt-0.5" style={{ color: role.color }}>
                {role.tagline}
              </p>
              <ul className="flex flex-col gap-2">
                {role.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm" style={{ color: "var(--muted-foreground)" }}>
                    <CheckCircle size={13} style={{ color: "var(--primary)" }} className="flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Benefits ──────────────────────────────────────────────────────────────────

function BenefitsSection() {
  const benefits = [
    { icon: Zap, title: "Faster Production Workflows", description: "Eliminate manual continuity tracking. VERSE automates the mundane so your team focuses on the creative." },
    { icon: Shield, title: "Better Continuity Management", description: "Catch continuity errors before they happen. VERSE's AI monitors every scene in real time." },
    { icon: Users, title: "Improved Team Collaboration", description: "Break down departmental silos. Every team member gets a unified view of production continuity." },
    { icon: Eye, title: "Explainable AI Insights", description: "No black boxes. Every recommendation includes a confidence score, reasoning, and suggested action." },
    { icon: Brain, title: "Semantic Production Memory", description: "Your production's entire history, instantly searchable. Ask VERSE anything in plain language." },
    { icon: Star, title: "Human-Centered AI", description: "VERSE augments your team's expertise — never replaces it. Human verification keeps your team in control." },
  ];

  return (
    <section
      className="py-20 px-6"
      style={{ background: "linear-gradient(180deg, #F5F3FF 0%, #EDE9FE 60%, #FDF6E3 100%)" }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--primary)" }}>Why VERSE</p>
          <h2
            className="text-3xl md:text-4xl lg:text-5xl font-black text-foreground leading-tight mb-5"
            style={{ fontFamily: "var(--font-display)" }}
          >
            The <Gold>competitive edge</Gold> your production deserves.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {benefits.map((b) => {
            const Icon = b.icon;
            return (
              <div
                key={b.title}
                className="flex flex-col gap-3 p-6 rounded-2xl border hover:shadow-md transition-all"
                style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.8)" }}
              >
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ background: "linear-gradient(135deg, rgba(124,58,237,0.15) 0%, rgba(29,52,97,0.1) 100%)", border: "1px solid rgba(124,58,237,0.15)" }}
                >
                  <Icon size={19} style={{ color: "var(--verse-violet)" }} />
                </div>
                <h3 className="text-base font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>{b.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: "var(--muted-foreground)" }}>{b.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─── Future Section ────────────────────────────────────────────────────────────

function FutureSection({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <section
      id="future"
      className="py-20 px-6"
      style={{
        background: "linear-gradient(135deg, #0D1B2E 0%, #1D3461 40%, #2D1B69 100%)",
      }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-xs font-bold tracking-widest uppercase mb-4" style={{ color: "var(--verse-gold)" }}>
              The Future of Filmmaking
            </p>
            <h2
              className="text-3xl md:text-4xl lg:text-5xl font-black text-white leading-tight mb-6"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Intelligent films. Human souls.
            </h2>
            <p className="text-base leading-relaxed mb-8" style={{ color: "rgba(255,255,255,0.65)" }}>
              The future of filmmaking is not about replacing human creativity with AI. It's about giving storytellers
              the <span style={{ color: "rgba(124,58,237,0.9)" }}>intelligence infrastructure</span> they need to bring
              their most ambitious visions to life — powered by <span style={{ color: "rgba(154,111,0,0.9)" }}>IBM watsonx</span>.
            </p>
            <div className="flex flex-col gap-3 mb-10">
              {[
                "AI-assisted production that preserves human creative control",
                "Semantic continuity intelligence that learns your story",
                "Responsible AI recommendations with full transparency",
                "Production intelligence built for global creative teams",
              ].map((point) => (
                <div key={point} className="flex items-start gap-3">
                  <CheckCircle size={17} className="mt-0.5 flex-shrink-0" style={{ color: "var(--verse-gold)" }} />
                  <span className="text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.7)" }}>{point}</span>
                </div>
              ))}
            </div>
            <button
              onClick={onGetStarted}
              className="flex items-center gap-2 font-semibold px-7 py-3.5 rounded-xl transition-all text-white hover:-translate-y-0.5 shadow-lg"
              style={{ background: "linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)" }}
            >
              Start Your Production <ArrowRight size={17} />
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {[
              { quote: "VERSE caught 3 major continuity errors in our feature's first act that would have required expensive reshoots.", author: "James K., Feature Film Director" },
              { quote: "Finally, a tool that understands film production continuity at the level of a seasoned script supervisor.", author: "Nina T., Script Supervisor" },
              { quote: "The semantic memory system is unlike anything I've used in 15 years of production management.", author: "Sarah C., Executive Producer" },
            ].map((t) => (
              <div
                key={t.author}
                className="rounded-2xl p-5 border"
                style={{ background: "rgba(255,255,255,0.06)", borderColor: "rgba(255,255,255,0.12)" }}
              >
                <p className="text-sm leading-relaxed mb-3 italic" style={{ color: "rgba(255,255,255,0.78)" }}>"{t.quote}"</p>
                <p className="text-xs font-medium" style={{ color: "rgba(255,255,255,0.4)" }}>{t.author}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────────────────────────────

function Footer({ onGetStarted }: { onGetStarted: () => void }) {
  return (
    <footer className="border-t py-14 px-6" style={{ background: "white", borderColor: "var(--border)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10 mb-12">
          <div className="md:col-span-2">
            {/* Footer logo — larger than before */}
            <ImageWithFallback src={verseLogo} alt="VERSE" style={{ width: "220px", height: "auto", objectFit: "contain", marginBottom: "20px" }} />
            <p className="text-sm leading-relaxed mb-5 max-w-xs" style={{ color: "var(--muted-foreground)" }}>
              <VI>AI-powered semantic continuity</VI> and <Gold>production intelligence</Gold> for intelligent filmmaking.
            </p>
            <p className="text-xs font-bold tracking-widest uppercase" style={{ color: "rgba(13,27,46,0.3)" }}>
              "Every story lives in its own VERSE."
            </p>
            <div className="flex items-center gap-3 mt-5">
              {[Twitter, Linkedin, Github, Globe].map((Icon, i) => (
                <button
                  key={i}
                  className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors hover:bg-muted"
                  style={{ background: "var(--muted)" }}
                >
                  <Icon size={15} style={{ color: "var(--muted-foreground)" }} />
                </button>
              ))}
            </div>
          </div>

          {[
            { title: "Product", links: ["Features", "How It Works", "Pricing", "Documentation", "Changelog"] },
            { title: "Company", links: ["About VERSE", "Careers", "Contact", "Press", "Blog"] },
            { title: "Legal", links: ["Privacy Policy", "Terms of Service", "Cookie Policy", "IBM watsonx"] },
          ].map((col) => (
            <div key={col.title}>
              <h4 className="text-xs font-bold tracking-widest uppercase text-foreground mb-4">{col.title}</h4>
              <ul className="flex flex-col gap-3">
                {col.links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-sm transition-colors hover:text-foreground"
                      style={{ color: "var(--muted-foreground)" }}
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div
          className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t"
          style={{ borderColor: "var(--border)" }}
        >
          <p className="text-xs" style={{ color: "var(--muted-foreground)" }}>
            © 2026 VERSE — <Mid>Visual & Explainable Reasoning for Semantic Evolution</Mid>. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-xs" style={{ color: "var(--muted-foreground)" }}>
            <a href="#" className="hover:text-foreground transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-foreground transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─── Main Landing Page ─────────────────────────────────────────────────────────

export default function LandingPage({ onGetStarted, onSignIn }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-background">
      <Navbar onGetStarted={onGetStarted} onSignIn={onSignIn} />
      <HeroSection onGetStarted={onGetStarted} />
      <WhatIsVerseSection />
      <ProblemsSection />
      <FeaturesSection />
      <HowItWorksSection />
      <UserRolesSection />
      <BenefitsSection />
      <FutureSection onGetStarted={onGetStarted} />
      <Footer onGetStarted={onGetStarted} />
    </div>
  );
}
