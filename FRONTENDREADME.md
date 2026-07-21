# VERSE — Frontend Documentation

**Visual & Explainable Reasoning for Semantic Evolution**

An AI-powered semantic continuity and production intelligence platform built for filmmakers — from screenplay to final cut.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Installation and Setup](#installation-and-setup)
6. [Running the Application](#running-the-application)
7. [Git Setup](#git-setup)
8. [Environment Variables](#environment-variables)
9. [UI/UX Design System](#uiux-design-system)
10. [Application Architecture](#application-architecture)
11. [Pages and Components](#pages-and-components)
12. [Data Layer](#data-layer)
13. [Deployment](#deployment)
14. [Development Notes](#development-notes)
15. [Future Improvements](#future-improvements)

---

## Project Overview

VERSE is a frontend demonstration of an enterprise AI filmmaking platform. It presents a complete product experience — from a cinematic marketing landing page through authenticated onboarding into a fully interactive role-based production dashboard.

The acronym **VERSE** stands for:

> **V**isual & **E**xplainable **R**easoning for **S**emantic **E**volution

The platform communicates the integration of **IBM watsonx** enterprise AI and **IBM Granite** foundation models to deliver:

- Semantic continuity intelligence for film productions
- Explainable AI recommendations with confidence scoring
- Role-based production management workflows
- Real-time continuity analysis and alerting

This is a complete frontend application demonstrating the user interface, navigation flows, and dashboard experience. All backend data is mocked in `src/app/data/mockData.ts`.

---

## Features

### Landing Page
- Cinematic dark-themed Hero Section with animated stat cards
- IBM watsonx + IBM Granite technology partnership badge
- VERSE acronym definition card
- Three-tier CTA button system (Get Started Free, Watch Demo, Explore Features)
- Four AI capability stat cards (10,000+ Scenes Analyzed, 99.2% Accuracy, 500+ Productions, <50ms Response)
- "What is VERSE?" section with four AI pillar cards
- Problems Section highlighting production pain points
- Features Section showcasing core AI capabilities
- How It Works Section with step-by-step process
- User Roles Section for different production team members
- Benefits Section with quantified production value
- Future Vision Section with testimonials
- Footer with social links and navigation

### Navbar
- Adaptive theme system — 6 distinct visual themes that change as the user scrolls between sections
- Intersection Observer-based active section detection
- Animated active link indicator
- Responsive mobile menu with full navigation
- Logo scaling with hover state

### Authentication Flow
- **Sign In** — email/password form with demo accounts panel (6 role shortcuts for instant dashboard access)
- **Create Account** — full registration form with form validation
- **Forgot Password** — email recovery flow
- **Email Verification** — OTP-style verification step

### Onboarding Flow
- **Role Selection** — 7 user role options (Producer, Director, Script Supervisor, Continuity Supervisor, Production Manager, Department Member, Film Student)
- **Production Type Selection** — 8 production types (Feature Film, TV Series, Documentary, Short Film, Independent, Commercial, Student Film, Animation)
- **Create Workspace** — workspace naming and configuration with confetti celebration on completion
- Progress indicator across all three onboarding steps

### Dashboard
Role-based navigation adapts the entire sidebar and page content to the authenticated user's role. All 7 roles have distinct navigation sets and dashboard pages.

**Producer Dashboard** includes:
- Production overview with continuity health radar chart
- Productions list with status, continuity scores, and team info
- Team management
- Continuity reports
- Analytics with bar and line charts
- AI Insights panel
- Workspace settings

**Director Dashboard** includes:
- Scene Tracking
- Character continuity management
- Production Timeline
- AI Recommendations with severity levels (critical, warning, info)
- Semantic Memory view

**Script Supervisor Dashboard** includes:
- Continuity Tracking
- Screenplay Analysis
- Scene Timeline
- AI Alerts panel
- Narrative Progression view

**Continuity Supervisor Dashboard** includes:
- Costume Tracking
- Prop Tracking
- Continuity Verification
- Production Memory

**Production Manager Dashboard** includes:
- Team Collaboration
- Scheduling
- Workspace Management
- Reports

**Department Member Dashboard** includes:
- My Tasks
- Notes
- Continuity Updates
- Discussions

**Film Student Dashboard** includes:
- Demo Workspace
- Tutorials
- Sample Productions
- Interactive Learning

### Session Persistence
- `sessionStorage` preserves the user's navigation state across page refreshes during a demo session
- Sign Out clears the session and returns to the landing page

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Framework | React | 18.3.1 |
| Language | TypeScript | — |
| Build Tool | Vite | 6.3.5 |
| Styling | Tailwind CSS v4 | 4.1.12 |
| UI Primitives | shadcn/ui + Radix UI | various |
| Icons | Lucide React | 0.487.0 |
| Charts | Recharts | 2.15.2 |
| Animations | Motion (Framer Motion) | 12.23.24 |
| Forms | React Hook Form | 7.55.0 |
| Notifications | Sonner | 2.0.3 |
| Drag & Drop | React DnD | 16.0.1 |
| Date Utilities | date-fns | 3.6.0 |
| Routing | React Router | 7.18.1 |
| Class Utilities | clsx, tailwind-merge, CVA | — |
| Fonts | Manrope, Inter, JetBrains Mono (Google Fonts) | — |
| Package Manager | pnpm | — |

---

## Project Structure

```
VERSE/
├── index.html                    # Application entry point HTML
├── package.json                  # Dependencies and scripts
├── vite.config.ts                # Vite + Tailwind + path alias configuration
├── postcss.config.mjs            # PostCSS configuration
├── pnpm-workspace.yaml           # pnpm workspace configuration
├── FRONTENDREADME.md             # This file
├── ATTRIBUTIONS.md               # Third-party resource acknowledgements
├── .gitignore                    # Git ignore rules
│
└── src/
    ├── main.tsx                  # React DOM entry point
    ├── styles/
    │   ├── index.css             # CSS entry — imports fonts, tailwind, theme
    │   ├── fonts.css             # Google Fonts import + CSS font variables
    │   ├── tailwind.css          # Tailwind v4 source directive + tw-animate-css
    │   ├── theme.css             # VERSE brand design token system (CSS variables)
    │   └── globals.css           # Global base styles
    │
    └── app/
        ├── App.tsx               # Root component — navigation state machine
        │
        ├── pages/
        │   ├── LandingPage.tsx   # Marketing landing page (all sections)
        │   ├── AuthPages.tsx     # Sign In, Create Account, Forgot Password, Email Verification
        │   ├── OnboardingPages.tsx # Role Selection, Production Type, Create Workspace
        │   └── DashboardPage.tsx # Full role-based production dashboard
        │
        ├── components/
        │   ├── figma/
        │   │   └── ImageWithFallback.tsx  # Image component with graceful error fallback
        │   └── ui/               # shadcn/ui components (accordion, button, card, etc.)
        │
        ├── data/
        │   └── mockData.ts       # All application mock data, types, and configurations
        │
        └── imports/
            ├── VERSE_LOGO_2.png  # Primary VERSE brand logo
            └── IBM_Hackathon.pdf # Project reference document
```

### Key Directory Purposes

| Directory | Purpose |
|---|---|
| `src/app/pages/` | Full-page view components. Each file is a self-contained page. |
| `src/app/components/ui/` | Reusable shadcn/ui primitives. Edit here to change component appearance globally. |
| `src/app/components/figma/` | Utility components for asset handling. |
| `src/app/data/` | All mock data, TypeScript types, and role/production configurations. |
| `src/styles/` | All styling — theme tokens, fonts, and Tailwind setup. |
| `src/imports/` | Static assets (images, documents) imported directly by components. |

---

## Installation and Setup

### Prerequisites

- **Node.js** 18.0 or higher
- **pnpm** (recommended) — or npm/yarn

### Install pnpm (if not already installed)

```bash
npm install -g pnpm
```

### Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd VERSE

# Install all dependencies
pnpm install
```

> The `node_modules/` directory is excluded from the repository via `.gitignore`. Running `pnpm install` restores all dependencies from `package.json` and `pnpm-lock.yaml`.

### Verify Installation

```bash
# Confirm the dev server starts without errors
pnpm run dev
```

---

## Running the Application

### Development Server

```bash
pnpm run dev
```

Starts the Vite development server with hot module replacement. Open [http://localhost:5173](http://localhost:5173) in your browser.

### Production Build

```bash
pnpm run build
```

Compiles and bundles the application into the `dist/` directory. TypeScript is type-checked and all assets are optimised.

### Preview Production Build

```bash
pnpm run preview
```

Serves the production build locally for verification before deployment.

---

## Git Setup

After cloning the repository, install dependencies:

```bash
pnpm install
```

The `node_modules/` folder is intentionally excluded from the repository via `.gitignore`. All required packages are declared in `package.json` and locked in `pnpm-lock.yaml`, ensuring reproducible installs.

### First-Time Repository Setup

If you are initialising a new Git repository for this project:

```bash
git init
git add .
git commit -m "Initial commit"
```

### If node_modules Was Previously Committed

If `node_modules` was accidentally committed, remove it from tracking without deleting local files:

```bash
git rm -r --cached node_modules
git commit -m "Remove node_modules from tracking"
```

---

## Environment Variables

This frontend application does not currently require environment variables for local development. All data is served from `src/app/data/mockData.ts`.

When connecting to a real backend API, create a `.env.local` file in the project root:

```env
# API base URL for the VERSE backend
VITE_API_URL=https://api.your-verse-instance.com

# IBM watsonx API endpoint (when integrating directly)
VITE_WATSONX_API_URL=

# IBM Granite model endpoint
VITE_GRANITE_API_URL=

# Authentication service URL
VITE_AUTH_URL=
```

> **Important:** `.env` and `.env.local` files are excluded from the repository via `.gitignore`. Never commit API keys or credentials.

All Vite environment variables must be prefixed with `VITE_` to be accessible in the frontend code via `import.meta.env.VITE_VARIABLE_NAME`.

---

## UI/UX Design System

### Brand Identity

VERSE uses a three-colour brand system defined as CSS custom properties in `src/styles/theme.css`:

| Token | Colour | Role |
|---|---|---|
| `--verse-midnight` | `#1D3461` | Trust, enterprise, authority |
| `--verse-violet` | `#7C3AED` | AI intelligence, innovation, reasoning |
| `--verse-gold` | `#C49512` | Story insights, continuity, premium value |
| `--verse-emerald` | `#059669` | Success, verified continuity |
| `--verse-red` | `#DC2626` | Errors, critical alerts |

### Typography

| Variable | Font | Use |
|---|---|---|
| `--font-display` | Manrope | All headings, brand text, stat values |
| `--font-body` | Inter | All body copy, navigation, forms |
| `--font-mono` | JetBrains Mono | Data labels, scores, timestamps |

### Component Variants

The dashboard uses a `CardVariant` system (`default`, `ai`, `analytics`, `continuity`, `production`, `workspace`, `dark`) that maps to predefined gradient backgrounds and border colours, enabling consistent card styling across all role dashboards.

### Responsive Behaviour

- Mobile-first Tailwind utility classes throughout
- Navbar collapses to a hamburger menu on screens below `md` (768px)
- Dashboard sidebar collapses with a toggle button on small screens
- Stat cards switch from 4-column to 2-column grid on mobile
- Hero headline uses `clamp()` for fluid typography scaling

### Landing Page Sections

The landing page background transitions across sections:
- **Hero:** Deep cinematic dark (`#0A0F1E → #130E28`)
- **About / Features:** Light periwinkle-lavender (`#F0EEFF → #F5F3FF`)
- **Roles:** Deep midnight blue to violet
- **Future / CTA:** Dark midnight gradient

The Navbar dynamically adapts its colours, link styles, and button colours based on which section is currently most visible, using `IntersectionObserver`.

---

## Application Architecture

### Navigation State Machine

VERSE uses a single-page state machine in `src/app/App.tsx` rather than URL-based routing for its demo flow. The `AppView` union type defines all possible views:

```
landing → sign-in ──────────────────────────────────────────→ dashboard
        → create-account → email-verification → role-selection
                                              → production-type
                                              → create-workspace → dashboard
        → forgot-password → sign-in
```

The `navigateTo(view, updates?)` function transitions between views and optionally applies state updates (e.g., storing the selected role).

### Session Persistence

`sessionStorage` is used to persist the full `AppState` object across page refreshes. On mount, `App.tsx` attempts to restore from `verse_session`. On sign-out, the key is removed.

### Role-Based Rendering

The `DashboardPage` component accepts a `userRole: UserRole` prop and uses it to:
1. Select the correct navigation configuration from `navigationConfigByRole`
2. Render the appropriate page content when a nav item is selected
3. Display role-specific data, charts, and AI recommendations

### Mock Data

`src/app/data/mockData.ts` is the single source of truth for all demo content:
- `userRoles` — role definitions with features and responsibilities
- `productionTypes` — production category options
- `mockProductions` — sample production records
- `continuityHealthData` — radar chart data
- `sceneTimelineData` — bar chart data
- `aiRecommendations` — AI-generated continuity alerts
- `teamMembers` — team roster data
- `characters` — character tracking data

---

## Pages and Components

### `LandingPage.tsx`

The marketing landing page. All sections are self-contained functions:

| Function | Section |
|---|---|
| `Navbar` | Fixed navigation with section-aware theming |
| `HeroSection` | Cinematic hero with IBM badges, headline, CTAs, stat cards |
| `WhatIsVerseSection` | Four AI pillar cards explaining the product |
| `ProblemsSection` | Three production pain points VERSE solves |
| `FeaturesSection` | Core AI feature showcase |
| `HowItWorksSection` | Step-by-step process explanation |
| `UserRolesSection` | Role-specific value propositions |
| `BenefitsSection` | Quantified production benefits |
| `FutureSection` | Vision statement and user testimonials |
| `Footer` | Site map, social links, and legal text |

Inline colour helper components (`VI`, `Gold`, `Mid`) apply brand colours to inline text without additional CSS classes.

### `AuthPages.tsx`

Four exported page components for the authentication flow. The Sign In page includes a demo accounts panel that maps role labels to `UserRole` IDs, enabling one-click dashboard access for evaluators.

### `OnboardingPages.tsx`

Three exported page components wrapped in a shared `OnboardingLayout` that provides the progress indicator, step counter, and back navigation.

### `DashboardPage.tsx`

A single large component that renders the full dashboard experience. Shared utility components (`PageHeader`, `Btn`, `Card`, `SectionTitle`, `SearchBox`, `StatusBadge`, score pills) are defined at the top of the file and reused across all role-specific page renderers.

### `ImageWithFallback.tsx`

A wrapper around `<img>` that renders a placeholder SVG if the image URL fails to load. Used for all logo instances and production thumbnails.

---

## Deployment

### Static Site Deployment

The application builds to a static `dist/` directory and can be deployed to any static hosting service.

**Build for production:**

```bash
pnpm run build
```

The output in `dist/` contains:
- `index.html` — application shell
- `assets/` — hashed JS bundle, CSS bundle, and image assets

### Recommended Hosting Platforms

- **Vercel** — connect the Git repository and set build command to `pnpm run build`, output directory to `dist`
- **Netlify** — same configuration; add a `_redirects` file (`/* /index.html 200`) if using client-side routing
- **GitHub Pages** — deploy the `dist/` folder contents using `gh-pages` or a GitHub Actions workflow
- **IBM Cloud Static Web Apps** — deploy via IBM Cloud Object Storage static hosting

### Build Configuration Notes

- There is no server-side rendering; this is a pure client-side SPA
- The `vite.config.ts` sets `@` as an alias for `src/` — this is resolved at build time and requires no runtime configuration
- Asset file names are content-hashed for cache invalidation

---

## Development Notes

### Known Constraints

- **No real backend.** All data in the dashboard is static mock data from `mockData.ts`. Connecting to a real API requires replacing mock imports with API calls and managing loading/error states.
- **No real authentication.** The sign-in form accepts any email/password and uses `sessionStorage` for state persistence. A real implementation would require an auth provider (e.g., IBM AppID, Auth0, Firebase).
- **Font loading depends on network.** Fonts are loaded from Google Fonts CDN. Offline use or restricted network environments may fall back to system fonts.
- **Unsplash images require network.** Production thumbnail images in mock data are fetched from Unsplash CDN URLs.

### Architecture Decisions

- **State machine navigation over URL routing** was chosen to keep the demo flow self-contained and avoid browser history complexity during presentation. React Router is installed if URL-based routing is needed in a production build.
- **Single-file page components** keep all section logic co-located. For a production codebase, each section of the landing page and each dashboard page would be split into its own file.
- **Inline styles alongside Tailwind** are used for dynamic values (colours from CSS variables, computed gradients, per-card glow colours). Static layout classes use Tailwind utilities.
- **pnpm** is the package manager. `pnpm-lock.yaml` should be committed to ensure reproducible installs. Do not mix with `npm` or `yarn` lockfiles.

### Coding Conventions

- All components are typed TypeScript functional components with explicit prop interfaces
- CSS custom properties (design tokens) are used for all brand colours — never hardcode colour values that exist as tokens
- Component state is local (`useState`) — no global state management library is used
- The `sonner` `toast()` function is used for all user feedback notifications

---

## Future Improvements

Based on the current implementation, the following enhancements would be the natural next steps:

### Backend Integration
- Replace `mockData.ts` with real API calls to a VERSE backend service
- Implement genuine IBM watsonx API integration for live AI recommendations
- Connect IBM Granite models for real-time semantic analysis of screenplay content

### Authentication
- Integrate a production auth provider (IBM AppID, Auth0, or similar)
- Implement JWT token management and refresh logic
- Add OAuth2 social sign-in options

### Real-Time Features
- WebSocket connection for live continuity alerts during production
- Real-time collaboration indicators showing which team members are viewing a scene
- Push notifications for critical continuity issues

### Enhanced Dashboard
- Export functionality for continuity reports (PDF, CSV)
- File upload for screenplay analysis (PDF/FDX parsing)
- Scene image upload and comparison for visual continuity checking
- Advanced filtering and search across all productions

### Performance
- Route-based code splitting using React Router and `React.lazy()`
- Image optimisation pipeline for production thumbnails
- Service Worker for offline dashboard access

### Accessibility
- Full WCAG 2.1 AA audit and remediation
- Keyboard navigation testing for all interactive elements
- Screen reader testing with VoiceOver and NVDA

### Testing
- Unit tests for utility functions and mock data transformations
- Component tests using React Testing Library
- End-to-end flow tests using Playwright or Cypress

---

*VERSE is an AI-powered semantic continuity and production intelligence platform.*  
*Powered by IBM watsonx enterprise AI and IBM Granite foundation models.*
