# Attributions

VERSE — Visual & Explainable Reasoning for Semantic Evolution  
Frontend Application — Third-Party Resources and Acknowledgements

---

## Frameworks & Core Runtime

### React
- **Version:** 18.3.1
- **Usage:** Core UI rendering library. All pages, components, and interactive elements are built as React functional components using hooks for state and side-effect management.
- **License:** MIT
- **Source:** https://github.com/facebook/react

### Vite
- **Version:** 6.3.5 / 6.4.3
- **Usage:** Build tool and development server. Handles module bundling, hot module replacement, TypeScript transpilation, and production optimisation.
- **License:** MIT
- **Source:** https://github.com/vitejs/vite

### TypeScript
- **Usage:** Statically typed superset of JavaScript used throughout the entire codebase for type-safe component props, state definitions, data models, and navigation types.
- **License:** Apache 2.0
- **Source:** https://github.com/microsoft/TypeScript

---

## Styling

### Tailwind CSS
- **Version:** 4.1.12
- **Usage:** Utility-first CSS framework used for all layout, spacing, typography, and responsive design across every page and component.
- **License:** MIT
- **Source:** https://github.com/tailwindlabs/tailwindcss

### tw-animate-css
- **Version:** 1.3.8
- **Usage:** Provides animation utilities imported into the Tailwind CSS layer for entrance and transition effects.
- **License:** MIT
- **Source:** https://github.com/aymanfarsi/tw-animate-css

### @tailwindcss/vite
- **Version:** 4.1.12
- **Usage:** Official Vite plugin that integrates Tailwind CSS v4 into the build pipeline.
- **License:** MIT
- **Source:** https://github.com/tailwindlabs/tailwindcss

---

## UI Component Libraries

### shadcn/ui
- **Usage:** Accessible, composable UI primitives installed as source components under `src/app/components/ui/`. Components used include accordion, alert-dialog, avatar, badge, button, calendar, card, carousel, checkbox, dialog, dropdown-menu, form, hover-card, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable panels, scroll-area, select, separator, sheet, sidebar, skeleton, slider, switch, tabs, textarea, toggle, toggle-group, and tooltip.
- **License:** MIT
- **Source:** https://ui.shadcn.com

### Radix UI Primitives
- **Usage:** Unstyled, accessible component primitives that underpin the shadcn/ui components. Individual packages used: accordion, alert-dialog, aspect-ratio, avatar, checkbox, collapsible, context-menu, dialog, dropdown-menu, hover-card, label, menubar, navigation-menu, popover, progress, radio-group, scroll-area, select, separator, slider, slot, switch, tabs, toggle, toggle-group, tooltip.
- **License:** MIT
- **Source:** https://www.radix-ui.com

### MUI (Material UI)
- **Version:** 7.3.5
- **Usage:** Supplemental component library providing additional UI elements. Emotion is used as the MUI styling engine.
- **License:** MIT
- **Source:** https://github.com/mui/material-ui

### @emotion/react & @emotion/styled
- **Version:** 11.14.0 / 11.14.1
- **Usage:** CSS-in-JS runtime required by MUI for component styling.
- **License:** MIT
- **Source:** https://github.com/emotion-js/emotion

---

## Icons

### Lucide React
- **Version:** 0.487.0
- **Usage:** Primary icon set used throughout the application — navigation, dashboard, feature sections, status indicators, and landing page. Icons include Film, Brain, Shield, Globe, Zap, Sparkles, ArrowRight, CheckCircle, AlertTriangle, and many others.
- **License:** ISC
- **Source:** https://github.com/lucide-icons/lucide

### MUI Icons Material
- **Version:** 7.3.5
- **Usage:** Supplemental Material Design icon set available via the MUI ecosystem.
- **License:** MIT
- **Source:** https://github.com/mui/material-ui/tree/master/packages/mui-icons-material

---

## Typography (Google Fonts)

### Manrope
- **Usage:** Display typeface used for all headings (h1–h4), brand headlines, and the primary Hero Section title. Applied via CSS variable `--font-display`.
- **Weights:** 400, 500, 600, 700, 800, 900
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/Manrope

### Inter
- **Usage:** Body typeface used for all paragraph text, navigation, labels, and UI copy. Applied via CSS variable `--font-body`.
- **Weights:** 300, 400, 500, 600, 700 (including italic variants)
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/Inter

### JetBrains Mono
- **Usage:** Monospace typeface used for data labels, numeric values, timestamps, and code-style display elements. Applied via CSS variable `--font-mono`.
- **Weights:** 400, 500
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/JetBrains+Mono

---

## Data Visualisation

### Recharts
- **Version:** 2.15.2
- **Usage:** Charting library used in the dashboard for the Continuity Health radar chart (RadarChart, Radar, PolarGrid, PolarAngleAxis) and the Scene Timeline bar chart (BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid) and a LineChart for analytics views.
- **License:** MIT
- **Source:** https://github.com/recharts/recharts

---

## Animation & Motion

### Motion (Framer Motion)
- **Version:** 12.23.24
- **Usage:** Animation library available in the project for advanced motion effects and transition orchestration.
- **License:** MIT
- **Source:** https://github.com/framer/motion

---

## Form Handling

### React Hook Form
- **Version:** 7.55.0
- **Usage:** Form state management and validation for the authentication pages (sign-in, create account, forgot password) and workspace creation flow.
- **License:** MIT
- **Source:** https://github.com/react-hook-form/react-hook-form

### input-otp
- **Version:** 1.4.2
- **Usage:** One-time password input component used on the email verification page.
- **License:** MIT
- **Source:** https://github.com/guilhermerodz/input-otp

---

## Drag and Drop

### React DnD
- **Version:** 16.0.1
- **Usage:** Drag-and-drop primitives available for interactive dashboard elements.
- **License:** MIT
- **Source:** https://github.com/react-dnd/react-dnd

### react-dnd-html5-backend
- **Version:** 16.0.1
- **Usage:** HTML5 backend driver for React DnD.
- **License:** MIT
- **Source:** https://github.com/react-dnd/react-dnd

---

## Notifications

### Sonner
- **Version:** 2.0.3
- **Usage:** Toast notification system used globally via the `<Toaster>` component in `App.tsx`. Provides real-time feedback for user actions including sign-in, workspace creation, and dashboard interactions.
- **License:** MIT
- **Source:** https://github.com/emilkowalski/sonner

---

## Routing

### React Router
- **Version:** 7.18.1
- **Usage:** Client-side routing library available in the project. The application currently uses a state-machine navigation pattern in `App.tsx` for its demo flow.
- **License:** MIT
- **Source:** https://github.com/remix-run/react-router

---

## Utility Libraries

### clsx
- **Version:** 2.1.1
- **Usage:** Utility for constructing className strings conditionally, used throughout component styling.
- **License:** MIT
- **Source:** https://github.com/lukeed/clsx

### class-variance-authority (CVA)
- **Version:** 0.7.1
- **Usage:** Variant-based class management for UI components, particularly in the shadcn/ui component layer.
- **License:** Apache 2.0
- **Source:** https://github.com/joe-bell/cva

### tailwind-merge
- **Version:** 3.2.0
- **Usage:** Intelligently merges Tailwind CSS class names, resolving conflicts when utility classes are combined dynamically.
- **License:** MIT
- **Source:** https://github.com/dcastil/tailwind-merge

### date-fns
- **Version:** 3.6.0
- **Usage:** Date utility library used for scheduling, production timeline formatting, and the calendar component.
- **License:** MIT
- **Source:** https://github.com/date-fns/date-fns

### canvas-confetti
- **Version:** 1.9.4
- **Usage:** Lightweight confetti animation effect triggered on workspace creation completion.
- **License:** ISC
- **Source:** https://github.com/catdad/canvas-confetti

### cmdk
- **Version:** 1.1.1
- **Usage:** Command palette component used for global search and command interfaces.
- **License:** MIT
- **Source:** https://github.com/pacocoursey/cmdk

### vaul
- **Version:** 1.1.2
- **Usage:** Drawer component primitive used for mobile-friendly slide-up panels.
- **License:** MIT
- **Source:** https://github.com/emilkowalski/vaul

### next-themes
- **Version:** 0.4.6
- **Usage:** Theme management utility available for light/dark mode toggling.
- **License:** MIT
- **Source:** https://github.com/pacocoursey/next-themes

---

## Carousel & Layout

### Embla Carousel React
- **Version:** 8.6.0
- **Usage:** Carousel/slider component used for multi-item scrollable layouts.
- **License:** MIT
- **Source:** https://github.com/davidjerleke/embla-carousel

### react-slick
- **Version:** 0.31.0
- **Usage:** Additional carousel/slider library available in the project.
- **License:** MIT
- **Source:** https://github.com/akiran/react-slick

### react-resizable-panels
- **Version:** 2.1.7
- **Usage:** Resizable panel layout component used in the dashboard workspace layout.
- **License:** MIT
- **Source:** https://github.com/bvaughn/react-resizable-panels

### react-responsive-masonry
- **Version:** 2.7.1
- **Usage:** Masonry grid layout component available for multi-column content layouts.
- **License:** MIT
- **Source:** https://github.com/cedricdelpoux/react-responsive-masonry

### @popperjs/core & react-popper
- **Version:** 2.11.8 / 2.3.0
- **Usage:** Positioning engine for tooltips, dropdowns, and floating UI elements.
- **License:** MIT
- **Source:** https://github.com/floating-ui/floating-ui

---

## Date Picker

### react-day-picker
- **Version:** 8.10.1
- **Usage:** Calendar date-picker component used in the scheduling and production timeline interfaces.
- **License:** MIT
- **Source:** https://github.com/gpbl/react-day-picker

---

## Image Assets

### Unsplash
- **Usage:** Sample production thumbnail images used in the mock data (`mockData.ts`) for the dashboard's production cards. Images are served directly via Unsplash CDN URLs for demonstration purposes only.
- **License:** Unsplash License
- **Source:** https://unsplash.com/license

### VERSE_LOGO_2.png
- **Usage:** Primary VERSE application logo used in the navigation bar, footer, authentication pages, and onboarding flow.
- **Classification:** Custom project asset created specifically for the VERSE application.

---

## AI Technology Integration

### IBM watsonx
- **Usage:** IBM's enterprise AI and data platform. VERSE is designed to integrate IBM watsonx for AI workflow orchestration, governance, and intelligent application development capabilities that power the semantic continuity analysis infrastructure.
- **Source:** https://www.ibm.com/watsonx

### IBM Granite Foundation Models
- **Usage:** IBM's family of open, performant foundation AI models. VERSE integrates IBM Granite models for advanced language understanding, semantic reasoning, and continuity intelligence — enabling the platform to analyse, reason over, and evolve with complex filmmaking knowledge and narrative relationships.
- **Source:** https://www.ibm.com/granite

---

## Build & Development Tooling

### @vitejs/plugin-react
- **Version:** 4.7.0
- **Usage:** Official Vite plugin enabling React Fast Refresh and JSX transformation during development.
- **License:** MIT
- **Source:** https://github.com/vitejs/vite-plugin-react

### PostCSS
- **Usage:** CSS post-processor integrated via Vite. Used alongside Tailwind CSS v4 for CSS transformation.
- **License:** MIT
- **Source:** https://github.com/postcss/postcss

---

*All trademarks and registered trademarks are the property of their respective owners.*  
*This project is a demonstration frontend application. All mock data is fictional and used for illustrative purposes only.*
