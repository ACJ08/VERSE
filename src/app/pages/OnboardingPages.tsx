// Onboarding Pages
// Contains the Role Selection, Production Type, and Create Workspace pages.
// These pages guide new users through the setup process after account creation.

import { useState } from "react";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, CheckCircle, Film, Calendar, Users, Hash } from "lucide-react";
import { ImageWithFallback } from "@/app/components/figma/ImageWithFallback";
import verseLogo from "@/imports/VERSE_LOGO_2.png";
import { userRoles, productionTypes, type UserRole, type ProductionType } from "@/app/data/mockData";
import { projects } from "@/app/lib/api";

// ─── Onboarding Layout ────────────────────────────────────────────────────────

// Onboarding Layout
// Wraps all onboarding pages with a centered card layout, progress indicator, and top navigation.
function OnboardingLayout({
  children,
  currentStep,
  totalSteps,
  onBack,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  currentStep: number;
  totalSteps: number;
  onBack?: () => void;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top navigation bar */}
      <div className="h-16 border-b px-6 flex items-center justify-between" style={{ background: "linear-gradient(135deg, #FFFFFF 0%, #F5F3FF 100%)", borderColor: "var(--border)" }}>
        <ImageWithFallback
          src={verseLogo}
          alt="VERSE"
          style={{ width: "140px", height: "auto", objectFit: "contain" }}
        />

        {/* Step progress indicator */}
        <div className="flex items-center gap-2">
          {Array.from({ length: totalSteps }).map((_, index) => (
            <div
              key={index}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                index < currentStep
                  ? "bg-primary w-6"
                  : index === currentStep - 1
                  ? "bg-primary w-8"
                  : "bg-muted w-4"
              }`}
            />
          ))}
        </div>

        {/* Step counter */}
        <span
          className="text-xs font-bold text-muted-foreground"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {currentStep} / {totalSteps}
        </span>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col items-center px-6 py-12">
        <div className="w-full max-w-4xl">
          {/* Back button */}
          {onBack && (
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-8 transition-colors"
            >
              <ArrowLeft size={16} /> Back
            </button>
          )}

          {/* Page heading */}
          <div className="mb-8">
            <h1
              className="text-4xl font-black text-foreground mb-3"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {title}
            </h1>
            {subtitle && (
              <p className="text-muted-foreground text-lg leading-relaxed">{subtitle}</p>
            )}
          </div>

          {children}
        </div>
      </div>
    </div>
  );
}

// ─── Role Selection Page ──────────────────────────────────────────────────────

// Role Selection Page
// Interactive card-based interface for selecting the user's production role.
// The selected role determines the dashboard layout and accessible features.
export function RoleSelectionPage({
  onRoleSelected,
  onBack,
}: {
  onRoleSelected: (role: UserRole) => void;
  onBack: () => void;
}) {
  const [selectedRole, setSelectedRole] = useState<UserRole | null>(null);

  return (
    <OnboardingLayout
      currentStep={1}
      totalSteps={3}
      onBack={onBack}
      title="What is your role?"
      subtitle="Select your primary role in the production. This determines your personalized dashboard, features, and access level within VERSE."
    >
      {/* Role cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {userRoles.map((role) => {
          const isSelected = selectedRole === role.id;

          return (
            <button
              key={role.id}
              onClick={() => setSelectedRole(role.id)}
              className={`group text-left p-6 rounded-2xl border-2 transition-all duration-200 ${
                isSelected
                  ? "border-primary bg-primary/5 shadow-md shadow-primary/10"
                  : "border-border bg-white hover:border-primary/30 hover:shadow-sm"
              }`}
            >
              {/* Role header */}
              <div className="flex items-start justify-between mb-4">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
                  style={{ backgroundColor: `${role.color}15` }}
                >
                  {role.icon}
                </div>
                {isSelected && (
                  <CheckCircle size={20} className="text-primary" />
                )}
              </div>

              {/* Role info */}
              <h3
                className="text-lg font-black text-foreground mb-1"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {role.title}
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                {role.description}
              </p>

              {/* Key features accessible for this role */}
              <div className="flex flex-col gap-1.5">
                {role.features.slice(0, 3).map((feature) => (
                  <div key={feature} className="flex items-center gap-2">
                    <div
                      className="w-1 h-1 rounded-full flex-shrink-0"
                      style={{ backgroundColor: role.color }}
                    />
                    <span className="text-xs text-muted-foreground">{feature}</span>
                  </div>
                ))}
                {role.features.length > 3 && (
                  <span className="text-xs text-muted-foreground pl-3">
                    +{role.features.length - 3} more
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {/* Continue button */}
      <button
        onClick={() => selectedRole && onRoleSelected(selectedRole)}
        disabled={!selectedRole}
        className="flex items-center gap-2 bg-primary text-primary-foreground font-semibold px-8 py-4 rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
      >
        Continue <ArrowRight size={18} />
      </button>
    </OnboardingLayout>
  );
}

// ─── Production Type Page ─────────────────────────────────────────────────────

// Production Type Page
// Card-based selection of the type of production the user is working on.
export function ProductionTypePage({
  onTypeSelected,
  onBack,
}: {
  onTypeSelected: (type: ProductionType) => void;
  onBack: () => void;
}) {
  const [selectedType, setSelectedType] = useState<ProductionType | null>(null);

  return (
    <OnboardingLayout
      currentStep={2}
      totalSteps={3}
      onBack={onBack}
      title="What type of production?"
      subtitle="Select the type of project you're creating. VERSE will tailor the continuity tracking and AI tools to match your specific production format."
    >
      {/* Production type cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {productionTypes.map((prodType) => {
          const isSelected = selectedType === prodType.id;

          return (
            <button
              key={prodType.id}
              onClick={() => setSelectedType(prodType.id)}
              className={`group text-left p-5 rounded-2xl border-2 transition-all duration-200 ${
                isSelected
                  ? "border-primary bg-primary/5 shadow-md shadow-primary/10"
                  : "border-border bg-white hover:border-primary/30 hover:shadow-sm"
              }`}
            >
              {/* Production type icon */}
              <div className="text-3xl mb-3">{prodType.icon}</div>

              <div className="flex items-start justify-between gap-1">
                <h3
                  className="text-sm font-bold text-foreground leading-tight"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {prodType.label}
                </h3>
                {isSelected && <CheckCircle size={14} className="text-primary flex-shrink-0 mt-0.5" />}
              </div>

              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {prodType.description}
              </p>
            </button>
          );
        })}
      </div>

      {/* Continue button */}
      <button
        onClick={() => selectedType && onTypeSelected(selectedType)}
        disabled={!selectedType}
        className="flex items-center gap-2 bg-primary text-primary-foreground font-semibold px-8 py-4 rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20"
      >
        Continue <ArrowRight size={18} />
      </button>
    </OnboardingLayout>
  );
}

// ─── Create Workspace Page ────────────────────────────────────────────────────

// Create Workspace Page
// Form for setting up the user's first VERSE production workspace.
// Collects production name, description, dates, and team information.
export function CreateWorkspacePage({
  selectedRole,
  selectedProductionType,
  onWorkspaceCreated,
  onBack,
}: {
  selectedRole: UserRole | null;
  selectedProductionType: ProductionType | null;
  onWorkspaceCreated: (productionName: string) => void;
  onBack: () => void;
}) {
  // Workspace form fields
  const [productionName, setProductionName] = useState("The Last Scene");
  const [productionDescription, setProductionDescription] = useState(
    "A neo-noir feature film following Detective Elena Chen as she investigates a series of mysterious disappearances in a rain-soaked city."
  );
  const [workspaceName, setWorkspaceName] = useState("VERSE — The Last Scene");
  const [startDate, setStartDate] = useState("2024-06-01");
  const [endDate, setEndDate] = useState("2024-12-15");
  const [teamSize, setTeamSize] = useState("12");
  const [isLoading, setIsLoading] = useState(false);

  // Auto-updates the workspace name whenever the production name changes
  const handleProductionNameChange = (value: string) => {
    setProductionName(value);
    setWorkspaceName(`VERSE — ${value}`);
  };

  // Creates workspace via the backend API; falls back gracefully if offline
  const handleCreateWorkspace = async () => {
    if (!productionName.trim()) return;
    setIsLoading(true);
    try {
      await projects.create({
        name: productionName,
        workspace_name: workspaceName,
        production_type: selectedProductionType ?? "feature-film",
        description: productionDescription,
        start_date: startDate,
        end_date: endDate,
        team_size: parseInt(teamSize, 10) || 1,
      });
      toast.success(`Workspace "${productionName}" created! Welcome to VERSE.`);
      onWorkspaceCreated(productionName);
    } catch {
      // Backend offline — proceed in demo mode
      toast.success(`Workspace "${productionName}" created! Welcome to VERSE.`);
      onWorkspaceCreated(productionName);
    } finally {
      setIsLoading(false);
    }
  };

  // Helper component for styled form inputs in this page
  function WorkspaceInput({
    label,
    value,
    onChange,
    placeholder,
    type = "text",
    icon: Icon,
    hint,
  }: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    placeholder?: string;
    type?: string;
    icon?: React.ElementType;
    hint?: string;
  }) {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-semibold text-foreground flex items-center gap-2">
          {Icon && <Icon size={14} className="text-muted-foreground" />}
          {label}
        </label>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="h-11 border border-border rounded-lg bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all text-sm px-4"
        />
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
    );
  }

  return (
    <OnboardingLayout
      currentStep={3}
      totalSteps={3}
      onBack={onBack}
      title="Create your production workspace."
      subtitle="Set up your first VERSE workspace. You can invite team members and add more details once your workspace is created."
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left column — main form */}
        <div className="lg:col-span-2 flex flex-col gap-5">
          <WorkspaceInput
            label="Production Name"
            value={productionName}
            onChange={handleProductionNameChange}
            placeholder="The Last Scene"
            icon={Film}
            hint="This is the name of your film, show, or project."
          />

          {/* Description textarea */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-semibold text-foreground">Production Description</label>
            <textarea
              value={productionDescription}
              onChange={(e) => setProductionDescription(e.target.value)}
              placeholder="Describe your production…"
              rows={3}
              className="border border-border rounded-lg bg-white text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all text-sm px-4 py-3 resize-none"
            />
          </div>

          <WorkspaceInput
            label="Workspace Name"
            value={workspaceName}
            onChange={setWorkspaceName}
            icon={Hash}
            hint="Auto-generated from your production name. You can customize this."
          />

          <div className="grid grid-cols-2 gap-4">
            <WorkspaceInput
              label="Start Date"
              type="date"
              value={startDate}
              onChange={setStartDate}
              icon={Calendar}
            />
            <WorkspaceInput
              label="End Date"
              type="date"
              value={endDate}
              onChange={setEndDate}
              icon={Calendar}
            />
          </div>

          <WorkspaceInput
            label="Team Size (estimated)"
            type="number"
            value={teamSize}
            onChange={setTeamSize}
            icon={Users}
            placeholder="12"
          />

          {/* Create Workspace button */}
          <button
            onClick={handleCreateWorkspace}
            disabled={isLoading || !productionName}
            className="flex items-center justify-center gap-2 bg-primary text-primary-foreground font-semibold px-8 py-4 rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-all shadow-lg shadow-primary/20 mt-2"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Creating your workspace…
              </>
            ) : (
              <>Create Workspace <ArrowRight size={18} /></>
            )}
          </button>
        </div>

        {/* Right column — summary card */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-border rounded-2xl p-6 sticky top-6">
            <p className="text-xs font-bold tracking-widest uppercase text-muted-foreground mb-4">
              Workspace Summary
            </p>

            {/* Production name */}
            <div className="mb-4 pb-4 border-b border-border">
              <p className="text-xs text-muted-foreground mb-1">Production</p>
              <p className="font-bold text-foreground" style={{ fontFamily: "var(--font-display)" }}>
                {productionName || "—"}
              </p>
            </div>

            {/* Selected role */}
            <div className="flex flex-col gap-3">
              {[
                {
                  label: "Your Role",
                  value: selectedRole
                    ? userRoles.find((r) => r.id === selectedRole)?.title
                    : "—",
                },
                {
                  label: "Production Type",
                  value: selectedProductionType
                    ? productionTypes.find((t) => t.id === selectedProductionType)?.label
                    : "—",
                },
                { label: "Team Size", value: teamSize ? `${teamSize} members` : "—" },
                {
                  label: "Timeline",
                  value: startDate && endDate ? `${startDate} → ${endDate}` : "—",
                },
              ].map((item) => (
                <div key={item.label} className="flex flex-col gap-0.5">
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="text-sm font-semibold text-foreground">{item.value}</p>
                </div>
              ))}
            </div>

            {/* AI feature hints */}
            <div className="mt-6 pt-4 border-t border-border">
              <p className="text-xs font-bold text-foreground mb-3">VERSE will set up:</p>
              <div className="flex flex-col gap-2">
                {[
                  "Semantic production memory",
                  "Continuity tracking workspace",
                  "Role-based team access",
                  "AI continuity engine",
                ].map((feature) => (
                  <div key={feature} className="flex items-center gap-2">
                    <CheckCircle size={12} className="text-primary flex-shrink-0" />
                    <span className="text-xs text-muted-foreground">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </OnboardingLayout>
  );
}
