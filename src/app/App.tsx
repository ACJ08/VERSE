// VERSE Application Root
// Manages global navigation state, simulated authentication, and renders the current page view.
// Includes sessionStorage persistence so the demo session survives page refreshes.
//
// User Flow:
//   Landing → Sign In / Sign Up → Email Verify → Role Select → Production Type → Create Workspace → Dashboard

import { useState, useEffect } from "react";
import { Toaster } from "sonner";
import LandingPage from "@/app/pages/LandingPage";
import { SignInPage, CreateAccountPage, ForgotPasswordPage, EmailVerificationPage } from "@/app/pages/AuthPages";
import { RoleSelectionPage, ProductionTypePage, CreateWorkspacePage } from "@/app/pages/OnboardingPages";
import DashboardPage from "@/app/pages/DashboardPage";
import { type UserRole, type ProductionType, userRoles } from "@/app/data/mockData";
import { TokenStore, UserStore } from "@/app/lib/api";

// ─── View Types ────────────────────────────────────────────────────────────────

type AppView =
  | "landing" | "sign-in" | "create-account" | "forgot-password"
  | "email-verification" | "role-selection" | "production-type"
  | "create-workspace" | "dashboard";

// ─── App State ─────────────────────────────────────────────────────────────────

interface AppState {
  currentView: AppView;
  userEmail: string;
  userName: string;
  selectedRole: UserRole | null;
  selectedProductionType: ProductionType | null;
  productionName: string;
}

// Maps demo role names (from AuthPages demo accounts) to UserRole IDs
function resolveRoleFromLabel(roleLabel?: string): UserRole | null {
  if (!roleLabel) return null;
  const normalized = roleLabel.toLowerCase().replace(/\s+/g, "-");
  const found = userRoles.find(
    (r) => r.id === normalized || r.title.toLowerCase() === roleLabel.toLowerCase()
  );
  return found?.id ?? null;
}

// ─── App Component ─────────────────────────────────────────────────────────────

export default function App() {
  // Attempt to restore session on first load.
  // Priority: real JWT user from localStorage → sessionStorage demo state → landing.
  const getInitialState = (): AppState => {
    // 1. Real authenticated user (JWT present + stored user object)
    const token = TokenStore.get();
    const apiUser = UserStore.get();
    if (token && apiUser) {
      const resolvedRole = resolveRoleFromLabel(apiUser.role) ?? "producer";
      // Try to restore sessionStorage position; else go to dashboard
      try {
        const stored = sessionStorage.getItem("verse_session");
        if (stored) {
          const parsed: AppState = JSON.parse(stored);
          // Only restore if still on dashboard/onboarding (not landing/auth)
          const restorableViews: AppView[] = ["dashboard", "role-selection", "production-type", "create-workspace"];
          if (restorableViews.includes(parsed.currentView)) {
            return { ...parsed, selectedRole: parsed.selectedRole ?? resolvedRole, userName: apiUser.name, userEmail: apiUser.email };
          }
        }
      } catch { /* ignore */ }
      return {
        currentView: "dashboard",
        userEmail: apiUser.email,
        userName: apiUser.name,
        selectedRole: resolvedRole,
        selectedProductionType: null,
        productionName: "The Last Scene",
      };
    }

    // 2. Demo/sessionStorage session
    try {
      const stored = sessionStorage.getItem("verse_session");
      if (stored) return JSON.parse(stored);
    } catch {
      // If parsing fails, fall through to the default state
    }
    return {
      currentView: "landing",
      userEmail: "alex@studioproductions.com",
      userName: "Alex Chen",
      selectedRole: null,
      selectedProductionType: null,
      productionName: "The Last Scene",
    };
  };

  const [appState, setAppState] = useState<AppState>(getInitialState);

  // Persists app state to sessionStorage after every change so refreshes don't lose position
  useEffect(() => {
    try {
      sessionStorage.setItem("verse_session", JSON.stringify(appState));
    } catch {
      // Silently ignore if sessionStorage is unavailable
    }
  }, [appState]);

  // Navigates to a new view and optionally applies state updates.
  // Scrolls to the top so every page starts fresh.
  const navigateTo = (view: AppView, updates?: Partial<AppState>) => {
    setAppState((prev) => ({ ...prev, currentView: view, ...updates }));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // ─── View Rendering ──────────────────────────────────────────────────────────

  const renderView = () => {
    switch (appState.currentView) {
      case "landing":
        return (
          <LandingPage
            onGetStarted={() => navigateTo("create-account")}
            onSignIn={() => navigateTo("sign-in")}
          />
        );

      case "sign-in":
        return (
          <SignInPage
            // When a demo role label is passed, resolve it and jump straight to the dashboard
            onSignIn={(roleLabel?: string) => {
              const resolvedRole = resolveRoleFromLabel(roleLabel);
              if (resolvedRole) {
                navigateTo("dashboard", {
                  selectedRole: resolvedRole,
                  userName: `${userRoles.find((r) => r.id === resolvedRole)?.title} Demo`,
                });
              } else {
                navigateTo("dashboard");
              }
            }}
            onCreateAccount={() => navigateTo("create-account")}
            onForgotPassword={() => navigateTo("forgot-password")}
            onBack={() => navigateTo("landing")}
          />
        );

      case "create-account":
        return (
          <CreateAccountPage
            onAccountCreated={() => navigateTo("email-verification")}
            onSignIn={() => navigateTo("sign-in")}
            onBack={() => navigateTo("landing")}
          />
        );

      case "forgot-password":
        return (
          <ForgotPasswordPage
            onBack={() => navigateTo("sign-in")}
            onEmailSent={() => navigateTo("sign-in")}
          />
        );

      case "email-verification":
        return (
          <EmailVerificationPage
            email={appState.userEmail}
            onVerified={() => navigateTo("role-selection")}
          />
        );

      case "role-selection":
        return (
          <RoleSelectionPage
            onRoleSelected={(role) => navigateTo("production-type", { selectedRole: role })}
            onBack={() => navigateTo("create-account")}
          />
        );

      case "production-type":
        return (
          <ProductionTypePage
            onTypeSelected={(type) => navigateTo("create-workspace", { selectedProductionType: type })}
            onBack={() => navigateTo("role-selection")}
          />
        );

      case "create-workspace":
        return (
          <CreateWorkspacePage
            selectedRole={appState.selectedRole}
            selectedProductionType={appState.selectedProductionType}
            onWorkspaceCreated={(name) => navigateTo("dashboard", { productionName: name })}
            onBack={() => navigateTo("production-type")}
          />
        );

      case "dashboard":
        return (
          <DashboardPage
            userRole={appState.selectedRole ?? "producer"}
            productionName={appState.productionName || "The Last Scene"}
            userName={appState.userName}
            onSignOut={() => {
              // Clear JWT token + stored user and the demo session
              TokenStore.clear();
              try { sessionStorage.removeItem("verse_session"); } catch {}
              navigateTo("landing", {
                selectedRole: null,
                selectedProductionType: null,
              });
            }}
          />
        );

      default:
        return (
          <div className="min-h-screen flex items-center justify-center">
            <p className="text-muted-foreground text-sm">Page not found.</p>
          </div>
        );
    }
  };

  return (
    <>
      {/* Global toast notification system from sonner */}
      <Toaster
        position="bottom-right"
        richColors
        toastOptions={{
          style: {
            fontFamily: "var(--font-body)",
            borderRadius: "12px",
            border: "1px solid var(--border)",
          },
        }}
      />
      {renderView()}
    </>
  );
}
