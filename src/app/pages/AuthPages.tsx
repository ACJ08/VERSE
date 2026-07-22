// Authentication Pages
// Sign In, Create Account, Forgot Password, Email Verification.
// Sign In includes a prominent Demo Accounts panel for one-click role-based access.

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { auth, TokenStore, UserStore } from "@/app/lib/api";
import {
  Eye, EyeOff, ArrowLeft, Mail, Lock, User, Building2,
  CheckCircle, ArrowRight, Zap, ChevronDown, ChevronUp,
} from "lucide-react";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import verseLogo from "@/imports/VERSE_LOGO_2.png";

// ─── Demo Account Definitions ──────────────────────────────────────────────────

// Each demo account represents a distinct VERSE user role.
// Users can click "Login as [Role]" to instantly autofill and sign in.
const demoAccounts = [
  {
    role: "Producer",
    email: "producer@verse.ai",
    password: "demo2024",
    icon: "🎬",
    color: "var(--verse-midnight)",
    bg: "var(--verse-midnight-light)",
    description: "Full production overview, team management, AI analytics",
  },
  {
    role: "Director",
    email: "director@verse.ai",
    password: "demo2024",
    icon: "🎭",
    color: "var(--verse-violet)",
    bg: "var(--verse-violet-light)",
    description: "Scene tracking, character continuity, AI recommendations",
  },
  {
    role: "Script Supervisor",
    email: "supervisor@verse.ai",
    password: "demo2024",
    icon: "📋",
    color: "#0F62FE",
    bg: "#EFF6FF",
    description: "Continuity tracking, screenplay analysis, AI alerts",
  },
  {
    role: "Continuity Supervisor",
    email: "continuity@verse.ai",
    password: "demo2024",
    icon: "🔍",
    color: "var(--verse-emerald)",
    bg: "#ECFDF5",
    description: "Costume, prop, and timeline continuity verification",
  },
  {
    role: "Production Manager",
    email: "manager@verse.ai",
    password: "demo2024",
    icon: "📊",
    color: "var(--verse-gold)",
    bg: "var(--verse-gold-light)",
    description: "Team collaboration, scheduling, workspace management",
  },
  {
    role: "Film Student",
    email: "student@verse.ai",
    password: "demo2024",
    icon: "🎓",
    color: "var(--verse-red)",
    bg: "#FEF2F2",
    description: "Demo workspace, tutorials, sample productions",
  },
];

// ─── Shared Auth Layout ────────────────────────────────────────────────────────

// Wraps all auth pages with a dark cinematic left panel and light form right panel.
function AuthLayout({
  children,
  headline,
  subtext,
}: {
  children: React.ReactNode;
  headline: string;
  subtext: string;
}) {
  return (
    <div className="min-h-screen flex">
      {/* Left panel — cinematic dark branding */}
      <div
        className="hidden lg:flex flex-col justify-between w-[440px] flex-shrink-0 p-12"
        style={{ background: "linear-gradient(160deg, #0D1B2E 0%, #1D3461 45%, #2D1B69 100%)" }}
      >
        <ImageWithFallback
          src={verseLogo}
          alt="VERSE"
          style={{ width: "240px", height: "auto", objectFit: "contain" }}
          className="brightness-0 invert"
        />

        <div>
          <h2
            className="text-3xl font-black text-white leading-tight mb-4"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {headline}
          </h2>
          <p className="text-white/60 leading-relaxed mb-8 text-sm">{subtext}</p>
          <div className="flex flex-col gap-4">
            {[
              { label: "Semantic Production Memory", desc: "Every scene remembered with full context." },
              { label: "AI Continuity Intelligence", desc: "Catch errors before they reach the edit." },
              { label: "Explainable AI Recommendations", desc: "Understand why, not just what." },
              { label: "Role-Based Collaboration", desc: "Every crew member in the right workspace." },
            ].map((f) => (
              <div key={f.label} className="flex items-start gap-3">
                <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5" style={{ backgroundColor: "rgba(196,149,18,0.25)", border: "1px solid rgba(196,149,18,0.5)" }}>
                  <CheckCircle size={11} style={{ color: "var(--verse-gold)" }} />
                </div>
                <div>
                  <p className="text-white/90 text-sm font-semibold leading-tight">{f.label}</p>
                  <p className="text-white/40 text-xs mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-white/10 pt-6">
          <p className="text-sm font-black italic" style={{ color: "var(--verse-gold)", fontFamily: "var(--font-display)" }}>
            "Every story lives in its own VERSE."
          </p>
          <p className="text-white/30 text-xs mt-1">The AI platform built for modern filmmakers.</p>
        </div>
      </div>

      {/* Right panel — form area */}
      <div className="flex-1 flex items-start justify-center p-8 overflow-y-auto" style={{ background: "linear-gradient(160deg, #F0EEFF 0%, #EDE9FE 50%, #F5F3FF 100%)" }}>
        <div className="w-full max-w-md py-6">
          <div className="bg-white/80 backdrop-blur-sm rounded-3xl p-8 shadow-lg border" style={{ borderColor: "var(--border)" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Form Input ────────────────────────────────────────────────────────────────

function FormInput({
  label, type = "text", placeholder, value, onChange,
  icon: Icon, rightElement, required = false,
}: {
  label: string; type?: string; placeholder?: string;
  value: string; onChange: (v: string) => void;
  icon?: React.ElementType; rightElement?: React.ReactNode; required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-semibold text-foreground">
        {label}{required && <span className="text-primary ml-1">*</span>}
      </label>
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <Icon size={15} />
          </div>
        )}
        <input
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full h-11 border border-border rounded-lg bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25 focus:border-primary transition-all text-sm ${Icon ? "pl-9" : "pl-4"} ${rightElement ? "pr-10" : "pr-4"}`}
        />
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">{rightElement}</div>
        )}
      </div>
    </div>
  );
}

// ─── Demo Accounts Panel ───────────────────────────────────────────────────────

// Demo Accounts Panel
// Displays all available demo role accounts with one-click autofill + login.
// Appears as a collapsible section below the sign-in form.
function DemoAccountsPanel({
  onDemoLogin,
}: {
  onDemoLogin: (email: string, password: string, role: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mt-6 border border-border rounded-2xl overflow-hidden">
      {/* Panel header — toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-5 py-4 bg-muted/50 hover:bg-muted transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--verse-violet-light)" }}>
            <Zap size={14} style={{ color: "var(--verse-violet)" }} />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-foreground">Demo Accounts</p>
            <p className="text-xs text-muted-foreground">One-click access to any role</p>
          </div>
        </div>
        {isExpanded ? <ChevronUp size={16} className="text-muted-foreground" /> : <ChevronDown size={16} className="text-muted-foreground" />}
      </button>

      {/* Demo account cards — collapsible */}
      {isExpanded && (
        <div className="p-4 grid grid-cols-1 gap-2.5">
          {demoAccounts.map((account) => (
            <div
              key={account.role}
              className="flex items-center gap-3 p-3 rounded-xl border hover:shadow-sm transition-all group" style={{ background: "linear-gradient(135deg, #F5F3FF 0%, #EDE9FE 100%)", borderColor: "rgba(209,205,242,0.8)" }}
            >
              {/* Role icon */}
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
                style={{ backgroundColor: account.bg }}
              >
                {account.icon}
              </div>

              {/* Role info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-foreground">{account.role}</p>
                <p className="text-xs text-muted-foreground truncate">{account.email}</p>
              </div>

              {/* One-click login button */}
              <button
                onClick={() => onDemoLogin(account.email, account.password, account.role)}
                className="flex-shrink-0 flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg transition-all hover:-translate-y-0.5"
                style={{ backgroundColor: account.bg, color: account.color }}
              >
                Login <ArrowRight size={11} />
              </button>
            </div>
          ))}

          {/* Shared password hint */}
          <p className="text-xs text-muted-foreground text-center mt-1 pb-1">
            All demo accounts use password:{" "}
            <span className="font-mono font-bold text-foreground">demo2024</span>
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Sign In Page ──────────────────────────────────────────────────────────────

export function SignInPage({
  onSignIn,
  onCreateAccount,
  onForgotPassword,
  onBack,
}: {
  onSignIn: (role?: string) => void;
  onCreateAccount: () => void;
  onForgotPassword: () => void;
  onBack: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Real sign-in — tries API first, falls back to demo flow if backend offline
  const handleSignIn = async () => {
    if (!email || !password) { toast.error("Please enter your email and password."); return; }
    setIsLoading(true);
    try {
      const res = await auth.login(email, password);
      TokenStore.set(res.access_token);
      UserStore.set(res.user);
      toast.success(`Welcome back, ${res.user.name}!`);
      onSignIn(res.user.role);
    } catch (err: unknown) {
      // Backend offline — fall through to demo mode
      if (err instanceof Error && err.message.includes("fetch")) {
        toast.success("Welcome back to VERSE! (demo mode)");
        onSignIn();
      } else {
        toast.error(err instanceof Error ? err.message : "Sign in failed.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // One-click demo login — tries real auth first, falls back gracefully
  const handleDemoLogin = async (demoEmail: string, demoPassword: string, role: string) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setIsLoading(true);
    toast.loading(`Signing in as ${role}…`);
    try {
      const res = await auth.login(demoEmail, demoPassword);
      TokenStore.set(res.access_token);
      UserStore.set(res.user);
      toast.dismiss();
      toast.success(`Welcome, ${res.user.name || role}! Your workspace is ready.`);
      onSignIn(res.user.role || role);
    } catch {
      // Backend not running — use demo flow
      toast.dismiss();
      toast.success(`Welcome, ${role}! Your demo workspace is ready.`);
      onSignIn(role);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      headline="Welcome back to your production workspace."
      subtext="Sign in to continue managing your film productions with AI-powered continuity intelligence."
    >
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-7 transition-colors"
      >
        <ArrowLeft size={15} /> Back to VERSE
      </button>

      {/* Mobile logo */}
      <div className="lg:hidden mb-6 flex justify-center">
        <ImageWithFallback src={verseLogo} alt="VERSE" style={{ width: "180px", height: "auto", objectFit: "contain" }} />
      </div>

      <div className="mb-7">
        <h1 className="text-3xl font-black text-foreground mb-1.5" style={{ fontFamily: "var(--font-display)" }}>
          Sign In
        </h1>
        <p className="text-muted-foreground text-sm">
          Don't have an account?{" "}
          <button onClick={onCreateAccount} className="text-primary font-semibold hover:underline">
            Create one
          </button>
        </p>
      </div>

      {/* Sign In Form */}
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => { e.preventDefault(); handleSignIn(); }}
      >
        <FormInput
          label="Email Address" type="email" placeholder="you@studio.com"
          value={email} onChange={setEmail} icon={Mail} required
        />
        <FormInput
          label="Password" type={showPassword ? "text" : "password"}
          placeholder="Enter your password" value={password} onChange={setPassword}
          icon={Lock} required
          rightElement={
            <button type="button" onClick={() => setShowPassword(!showPassword)}
              className="text-muted-foreground hover:text-foreground transition-colors">
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          }
        />

        <div className="flex justify-end">
          <button type="button" onClick={onForgotPassword}
            className="text-xs text-primary hover:underline font-medium">
            Forgot your password?
          </button>
        </div>

        <button
          type="submit" disabled={isLoading}
          className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Signing in…</>
          ) : (
            <>Sign In <ArrowRight size={15} /></>
          )}
        </button>
      </form>

      {/* SSO options */}
      <div className="flex items-center gap-3 my-5">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground">or</span>
        <div className="flex-1 h-px bg-border" />
      </div>
      <div className="grid grid-cols-2 gap-3 mb-1">
        {["Google", "Microsoft"].map((p) => (
          <button key={p}
            className="h-11 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-muted transition-colors"
            onClick={() => toast.info(`${p} SSO coming soon.`)}>
            {p}
          </button>
        ))}
      </div>

      {/* Demo Accounts Panel */}
      <DemoAccountsPanel onDemoLogin={handleDemoLogin} />

      <p className="text-xs text-muted-foreground text-center mt-5">
        By signing in you agree to our{" "}
        <a href="#" className="text-primary hover:underline">Terms</a> and{" "}
        <a href="#" className="text-primary hover:underline">Privacy Policy</a>.
      </p>
    </AuthLayout>
  );
}

// ─── Create Account Page ───────────────────────────────────────────────────────

export function CreateAccountPage({
  onAccountCreated,
  onSignIn,
  onBack,
}: {
  onAccountCreated: () => void;
  onSignIn: () => void;
  onBack: () => void;
}) {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [organizationName, setOrganizationName] = useState("");
  const [productionCompany, setProductionCompany] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateAccount = async () => {
    if (!firstName || !email || !password) { toast.error("Please fill in all required fields."); return; }
    if (password !== confirmPassword) { toast.error("Passwords do not match."); return; }
    setIsLoading(true);
    try {
      const res = await auth.register({
        email,
        password,
        name: [firstName, lastName].filter(Boolean).join(" "),
        organization: organizationName || productionCompany,
      });
      TokenStore.set(res.access_token);
      UserStore.set(res.user);
      toast.success("Account created! Please verify your email.");
      onAccountCreated();
    } catch (err: unknown) {
      if (err instanceof Error && err.message.includes("fetch")) {
        // Backend not running — demo mode
        toast.success("Account created! Please verify your email.");
        onAccountCreated();
      } else {
        toast.error(err instanceof Error ? err.message : "Registration failed.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      headline="Intelligence-driven filmmaking begins here."
      subtext="Create your VERSE workspace and bring semantic AI continuity to every frame of your production."
    >
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-6 transition-colors">
        <ArrowLeft size={15} /> Back to VERSE
      </button>

      <div className="lg:hidden mb-6 flex justify-center">
        <ImageWithFallback src={verseLogo} alt="VERSE" style={{ width: "180px", height: "auto", objectFit: "contain" }} />
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-black text-foreground mb-1.5" style={{ fontFamily: "var(--font-display)" }}>
          Create Account
        </h1>
        <p className="text-muted-foreground text-sm">
          Already have an account?{" "}
          <button onClick={onSignIn} className="text-primary font-semibold hover:underline">Sign in</button>
        </p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); handleCreateAccount(); }}>
        <p className="text-xs font-bold tracking-widest uppercase text-muted-foreground">Personal Information</p>

        <div className="grid grid-cols-2 gap-3">
          <FormInput label="First Name" placeholder="Alex" value={firstName} onChange={setFirstName} icon={User} required />
          <FormInput label="Last Name" placeholder="Chen" value={lastName} onChange={setLastName} required />
        </div>

        <FormInput label="Email Address" type="email" placeholder="you@studio.com" value={email} onChange={setEmail} icon={Mail} required />

        <FormInput
          label="Password" type={showPassword ? "text" : "password"}
          placeholder="Create a strong password" value={password} onChange={setPassword} icon={Lock} required
          rightElement={
            <button type="button" onClick={() => setShowPassword(!showPassword)}
              className="text-muted-foreground hover:text-foreground transition-colors">
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          }
        />

        <FormInput label="Confirm Password" type="password" placeholder="Confirm your password" value={confirmPassword} onChange={setConfirmPassword} icon={Lock} required />

        <p className="text-xs font-bold tracking-widest uppercase text-muted-foreground mt-1">Professional Information</p>

        <FormInput label="Organization Name" placeholder="Warner Bros. Studios" value={organizationName} onChange={setOrganizationName} icon={Building2} />
        <FormInput label="Production Company" placeholder="Your Production Company" value={productionCompany} onChange={setProductionCompany} icon={Building2} />

        <label className="flex items-start gap-3 cursor-pointer mt-1">
          <input type="checkbox" className="mt-0.5 rounded border-border accent-primary" required />
          <span className="text-xs text-muted-foreground leading-relaxed">
            I agree to VERSE's{" "}
            <a href="#" className="text-primary hover:underline">Terms of Service</a> and{" "}
            <a href="#" className="text-primary hover:underline">Privacy Policy</a>.
          </span>
        </label>

        <button
          type="submit" disabled={isLoading}
          className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-all flex items-center justify-center gap-2 mt-1"
        >
          {isLoading ? (
            <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Creating your account…</>
          ) : (
            <>Create Account <ArrowRight size={15} /></>
          )}
        </button>
      </form>
    </AuthLayout>
  );
}

// ─── Forgot Password Page ──────────────────────────────────────────────────────
// Two-step flow: (1) send OTP to email, (2) submit OTP + new password.

export function ForgotPasswordPage({
  onBack,
  onEmailSent,
}: {
  onBack: () => void;
  onEmailSent: () => void;
}) {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<"request" | "reset">("request");
  const [isLoading, setIsLoading] = useState(false);

  // Step 1 — request OTP
  const handleSendReset = async () => {
    if (!email) { toast.error("Please enter your email address."); return; }
    setIsLoading(true);
    try {
      const res = await auth.forgotPassword(email);
      if (res.dev_token) {
        setOtp(res.dev_token);
        toast.info(`Dev mode: OTP pre-filled (${res.dev_token})`);
      } else {
        toast.success("Reset code sent! Check your inbox.");
      }
      setStep("reset");
    } catch {
      // Backend offline — demo mode
      toast.success("Reset code sent! (demo mode)");
      setStep("reset");
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2 — submit OTP + new password
  const handleResetPassword = async () => {
    if (!otp || !newPassword) { toast.error("Please enter the reset code and your new password."); return; }
    setIsLoading(true);
    try {
      await auth.resetPassword(email, otp, newPassword);
      toast.success("Password updated! Please sign in.");
      onEmailSent();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reset failed. Check your code and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      headline="Reset your password."
      subtext="Enter your email to receive a 6-digit reset code, then set a new password."
    >
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors">
        <ArrowLeft size={15} /> Back to Sign In
      </button>

      <div className="lg:hidden mb-6 flex justify-center">
        <ImageWithFallback src={verseLogo} alt="VERSE" style={{ width: "180px", height: "auto", objectFit: "contain" }} />
      </div>

      <div className="mb-7">
        <h1 className="text-3xl font-black text-foreground mb-1.5" style={{ fontFamily: "var(--font-display)" }}>
          Forgot Password
        </h1>
        <p className="text-muted-foreground text-sm">
          {step === "request"
            ? "Enter your email and we'll send you a 6-digit reset code."
            : "Enter the code you received and choose a new password."}
        </p>
      </div>

      {step === "request" ? (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); handleSendReset(); }}>
          <FormInput label="Email Address" type="email" placeholder="you@studio.com" value={email} onChange={setEmail} icon={Mail} required />
          <button
            type="submit" disabled={isLoading}
            className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
          >
            {isLoading
              ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Sending…</>
              : <>Send Reset Code <ArrowRight size={15} /></>}
          </button>
        </form>
      ) : (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); handleResetPassword(); }}>
          <FormInput label="Reset Code" placeholder="6-digit code" value={otp} onChange={setOtp} icon={CheckCircle} required />
          <FormInput label="New Password" type="password" placeholder="New password (min 6 chars)" value={newPassword} onChange={setNewPassword} icon={Lock} required />
          <button
            type="submit" disabled={isLoading}
            className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
          >
            {isLoading
              ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Updating…</>
              : <>Reset Password <ArrowRight size={15} /></>}
          </button>
          <button type="button" onClick={() => setStep("request")}
            className="text-xs text-muted-foreground hover:text-foreground text-center transition-colors">
            ← Send a new code
          </button>
        </form>
      )}
    </AuthLayout>
  );
}

// ─── Email Verification Page ───────────────────────────────────────────────────
// Requests an OTP on mount, then accepts a 6-digit code to verify the account.

export function EmailVerificationPage({
  email,
  onVerified,
}: {
  email?: string;
  onVerified: () => void;
}) {
  const [otp, setOtp] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Request OTP as soon as the page mounts (and on resend)
  const requestOtp = async () => {
    setIsSending(true);
    try {
      const res = await auth.requestEmailVerification();
      if (res.dev_token) {
        setOtp(res.dev_token);
        toast.info(`Dev mode: OTP pre-filled (${res.dev_token})`);
      } else {
        toast.success("Verification code sent! Check your inbox.");
      }
    } catch {
      // Backend offline — skip silently; demo mode bypasses verification
    } finally {
      setIsSending(false);
    }
  };

  // Request OTP on first mount
  useEffect(() => { requestOtp(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleVerify = async () => {
    if (!otp) { toast.error("Please enter the verification code."); return; }
    setIsLoading(true);
    try {
      await auth.verifyEmail(otp);
      toast.success("Email verified! Let's set up your workspace.");
      onVerified();
    } catch (err) {
      // Backend offline → demo mode continues
      if (err instanceof Error && err.message.includes("fetch")) {
        toast.success("Email verified! Let's set up your workspace.");
        onVerified();
      } else {
        toast.error(err instanceof Error ? err.message : "Invalid code. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout
      headline="One last step before your production begins."
      subtext="Verify your email to unlock the full power of VERSE's production intelligence platform."
    >
      <div className="w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-8"
        style={{ backgroundColor: "var(--verse-midnight-light)" }}>
        <Mail size={38} style={{ color: "var(--verse-midnight)" }} />
      </div>

      <div className="text-center mb-8">
        <h1 className="text-3xl font-black text-foreground mb-3" style={{ fontFamily: "var(--font-display)" }}>
          Check your email
        </h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          We sent a 6-digit verification code to{" "}
          <span className="font-semibold text-foreground">{email || "your email address"}</span>.
          Enter it below to verify your account.
        </p>
      </div>

      <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); handleVerify(); }}>
        <FormInput
          label="Verification Code"
          placeholder="6-digit code"
          value={otp}
          onChange={setOtp}
          icon={CheckCircle}
          required
        />
        <button
          type="submit" disabled={isLoading}
          className="w-full h-11 bg-primary text-primary-foreground font-semibold rounded-lg hover:bg-primary/90 disabled:opacity-60 transition-all flex items-center justify-center gap-2"
        >
          {isLoading
            ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Verifying…</>
            : <>Verify Email <ArrowRight size={15} /></>}
        </button>
      </form>

      <p className="text-xs text-muted-foreground text-center mt-5">
        Didn't receive it?{" "}
        <button
          onClick={requestOtp}
          disabled={isSending}
          className="text-primary hover:underline font-medium disabled:opacity-50"
        >
          {isSending ? "Sending…" : "Resend code"}
        </button>
      </p>
    </AuthLayout>
  );
}
