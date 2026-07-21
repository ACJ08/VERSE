// VERSE Application Mock Data
// Contains all sample data used throughout the frontend for demonstration purposes.
// In a real application, this data would come from the VERSE backend API.

// ─── Type Definitions ─────────────────────────────────────────────────────────

export type UserRole =
  | "producer"
  | "director"
  | "script-supervisor"
  | "continuity-supervisor"
  | "production-manager"
  | "department-member"
  | "film-student";

export type ProductionType =
  | "feature-film"
  | "tv-series"
  | "documentary"
  | "short-film"
  | "independent-film"
  | "commercial"
  | "student-film"
  | "animation";

export type ProductionStatus = "In Production" | "Pre-Production" | "Post-Production" | "Completed";

// ─── Role Configuration ────────────────────────────────────────────────────────

// Defines each user role's display name, description, responsibilities, and accessible features.
export const userRoles = [
  {
    id: "producer" as UserRole,
    title: "Producer",
    icon: "🎬",
    description: "Oversee production workflows, team management, and strategic decisions.",
    responsibilities: [
      "Manage production timelines",
      "Oversee team collaboration",
      "Review continuity reports",
      "Approve production decisions",
    ],
    features: ["Production Overview", "Team Management", "Reports", "Analytics", "Workspace Management"],
    color: "#5B4BFF",
  },
  {
    id: "director" as UserRole,
    title: "Director",
    icon: "🎭",
    description: "Lead creative and production decisions across all scenes and characters.",
    responsibilities: [
      "Direct scene execution",
      "Manage character consistency",
      "Review AI recommendations",
      "Approve narrative decisions",
    ],
    features: ["Scene Tracking", "Production Timeline", "Character Tracking", "AI Recommendations", "Semantic Memory"],
    color: "#4F46E5",
  },
  {
    id: "script-supervisor" as UserRole,
    title: "Script Supervisor",
    icon: "📋",
    description: "Track continuity and manage screenplay consistency across all productions.",
    responsibilities: [
      "Monitor script continuity",
      "Track scene-by-scene changes",
      "Document AI continuity alerts",
      "Verify narrative progression",
    ],
    features: ["Continuity Tracking", "Screenplay Analysis", "Scene Timeline", "AI Alerts", "Narrative Progression"],
    color: "#0F62FE",
  },
  {
    id: "continuity-supervisor" as UserRole,
    title: "Continuity Supervisor",
    icon: "🔍",
    description: "Ensure physical and visual continuity across costume, props, and set details.",
    responsibilities: [
      "Track costume continuity",
      "Monitor prop consistency",
      "Verify scene timelines",
      "Manage production memory",
    ],
    features: ["Costume Tracking", "Prop Tracking", "Timeline Tracking", "Continuity Verification", "Production Memory"],
    color: "#10B981",
  },
  {
    id: "production-manager" as UserRole,
    title: "Production Manager",
    icon: "📊",
    description: "Coordinate schedules, teams, and workspace management for smooth production flow.",
    responsibilities: [
      "Manage production schedules",
      "Coordinate team collaboration",
      "Oversee workspace settings",
      "Generate production reports",
    ],
    features: ["Team Collaboration", "Production Scheduling", "Workspace Management", "Reports"],
    color: "#F59E0B",
  },
  {
    id: "department-member" as UserRole,
    title: "Department Member",
    icon: "👤",
    description: "Complete assigned tasks and contribute to continuity updates within your department.",
    responsibilities: [
      "Complete assigned tasks",
      "Submit continuity updates",
      "Participate in discussions",
      "Review department notes",
    ],
    features: ["Assigned Tasks", "Notes", "Continuity Updates", "Production Discussions"],
    color: "#6B7280",
  },
  {
    id: "film-student" as UserRole,
    title: "Film Student",
    icon: "🎓",
    description: "Learn and experiment with VERSE using demo workspaces and educational resources.",
    responsibilities: [
      "Explore demo workspaces",
      "Complete interactive tutorials",
      "Analyze sample productions",
      "Practice continuity tracking",
    ],
    features: ["Demo Workspace", "Educational Features", "Sample Productions", "Interactive Tutorials"],
    color: "#EF4444",
  },
];

// ─── Production Types ──────────────────────────────────────────────────────────

export const productionTypes = [
  { id: "feature-film" as ProductionType, label: "Feature Film", icon: "🎬", description: "Full-length theatrical release (75–180 min)" },
  { id: "tv-series" as ProductionType, label: "TV Series", icon: "📺", description: "Multi-episode television production" },
  { id: "documentary" as ProductionType, label: "Documentary", icon: "🎥", description: "Non-fiction investigative or narrative film" },
  { id: "short-film" as ProductionType, label: "Short Film", icon: "🎞️", description: "Short-format narrative (under 40 min)" },
  { id: "independent-film" as ProductionType, label: "Independent Film", icon: "🌟", description: "Self-financed or indie studio production" },
  { id: "commercial" as ProductionType, label: "Commercial", icon: "📢", description: "Advertising and branded content production" },
  { id: "student-film" as ProductionType, label: "Student Film", icon: "🎓", description: "Academic or film school project" },
  { id: "animation" as ProductionType, label: "Animation Project", icon: "✨", description: "Animated feature or short production" },
];

// ─── Sample Productions ────────────────────────────────────────────────────────

// Mock production data simulating what a Producer would see in their dashboard.
export const mockProductions = [
  {
    id: "prod-001",
    title: "The Last Scene",
    type: "Feature Film",
    status: "In Production" as ProductionStatus,
    continuityScore: 94,
    scenesTotal: 47,
    scenesLogged: 34,
    continuityIssues: 4,
    startDate: "2024-03-15",
    endDate: "2024-09-30",
    director: "James Kovacs",
    producer: "Sarah Chen",
    teamSize: 12,
    thumbnail: "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=120&h=80&fit=crop&auto=format",
  },
  {
    id: "prod-002",
    title: "Midnight Horizon",
    type: "TV Series",
    status: "Pre-Production" as ProductionStatus,
    continuityScore: 87,
    scenesTotal: 128,
    scenesLogged: 12,
    continuityIssues: 1,
    startDate: "2024-06-01",
    endDate: "2025-02-28",
    director: "Nina Torres",
    producer: "Marcus Webb",
    teamSize: 8,
    thumbnail: "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=120&h=80&fit=crop&auto=format",
  },
  {
    id: "prod-003",
    title: "Echoes of Tomorrow",
    type: "Documentary",
    status: "Post-Production" as ProductionStatus,
    continuityScore: 99,
    scenesTotal: 32,
    scenesLogged: 32,
    continuityIssues: 0,
    startDate: "2024-01-10",
    endDate: "2024-05-20",
    director: "Amara Osei",
    producer: "Lena Park",
    teamSize: 5,
    thumbnail: "https://images.unsplash.com/photo-1496715976403-7e36dc43f17b?w=120&h=80&fit=crop&auto=format",
  },
];

// ─── Continuity Health Chart Data ──────────────────────────────────────────────

// Data used by the Recharts RadarChart on the Producer dashboard.
export const continuityHealthData = [
  { subject: "Costume", score: 92, fullMark: 100 },
  { subject: "Props", score: 88, fullMark: 100 },
  { subject: "Lighting", score: 95, fullMark: 100 },
  { subject: "Dialogue", score: 97, fullMark: 100 },
  { subject: "Timeline", score: 84, fullMark: 100 },
  { subject: "Character", score: 90, fullMark: 100 },
];

// ─── Scene Timeline Data ───────────────────────────────────────────────────────

// Data for the scene logging progress bar chart.
export const sceneTimelineData = [
  { week: "Wk 1", logged: 4, total: 6 },
  { week: "Wk 2", logged: 8, total: 10 },
  { week: "Wk 3", logged: 6, total: 8 },
  { week: "Wk 4", logged: 10, total: 12 },
  { week: "Wk 5", logged: 6, total: 11 },
];

// ─── AI Recommendations ────────────────────────────────────────────────────────

// Mock AI recommendations generated by the VERSE continuity intelligence engine.
export const aiRecommendations = [
  {
    id: "rec-001",
    severity: "warning" as const,
    scene: "Scene 23 — INT. DINER - DAY",
    issue: "Elena's jacket color changes from navy to black between shots 23A and 23C.",
    confidence: 96,
    suggestion: "Cross-reference wardrobe log for 2024-04-12. Confirm costume continuity with script supervisor.",
    timestamp: "2 hours ago",
  },
  {
    id: "rec-002",
    severity: "info" as const,
    scene: "Scene 31 — EXT. ROOFTOP - NIGHT",
    issue: "Marcus appears without his watch in shots 31B–31D, but wears it in 31A and 31E.",
    confidence: 89,
    suggestion: "Verify prop continuity for the rooftop sequence. Check prop master logs.",
    timestamp: "5 hours ago",
  },
  {
    id: "rec-003",
    severity: "critical" as const,
    scene: "Scene 18 — INT. OFFICE - DAY",
    issue: "Timeline inconsistency detected: Scene 18 references 'Tuesday morning' but Scene 17 established it as 'Monday evening'.",
    confidence: 99,
    suggestion: "Review screenplay pages 43–48. Correct narrative timeline or adjust dialogue in Scene 17.",
    timestamp: "Yesterday",
  },
];

// ─── Team Members ──────────────────────────────────────────────────────────────

export const teamMembers = [
  { id: "tm-001", name: "Sarah Chen", role: "Producer", avatar: "SC", status: "online", lastActive: "Now" },
  { id: "tm-002", name: "James Kovacs", role: "Director", avatar: "JK", status: "online", lastActive: "5 min ago" },
  { id: "tm-003", name: "Nina Torres", role: "Script Supervisor", avatar: "NT", status: "away", lastActive: "1 hr ago" },
  { id: "tm-004", name: "Marcus Webb", role: "Continuity Supervisor", avatar: "MW", status: "offline", lastActive: "3 hrs ago" },
  { id: "tm-005", name: "Amara Osei", role: "Production Manager", avatar: "AO", status: "online", lastActive: "12 min ago" },
];

// ─── Characters ────────────────────────────────────────────────────────────────

export const characters = [
  {
    id: "char-001",
    name: "Elena Chen",
    type: "Lead",
    actor: "Isabella Voss",
    scenesIn: 38,
    continuityScore: 91,
    lastCostume: "Navy blazer, white blouse, dark jeans",
    lastScene: "Scene 23",
    notes: "Hair worn down in all interior scenes.",
  },
  {
    id: "char-002",
    name: "Marcus Webb",
    type: "Supporting",
    actor: "Daniel Park",
    scenesIn: 24,
    continuityScore: 87,
    lastCostume: "Charcoal suit, silver watch, black tie",
    lastScene: "Scene 31",
    notes: "Watch continuity issue flagged by AI (Scene 31).",
  },
  {
    id: "char-003",
    name: "Dr. Lena Park",
    type: "Supporting",
    actor: "Yuki Tanaka",
    scenesIn: 15,
    continuityScore: 98,
    lastCostume: "White lab coat, glasses, minimal accessories",
    lastScene: "Scene 19",
    notes: "Glasses continuity: consistent across all scenes.",
  },
];
