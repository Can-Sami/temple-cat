# Voice UI (shadcn) — Premium Dashboard Shell

## Goal

Make the Next.js frontend look like a **premium product dashboard** using **shadcn/ui** components, while keeping the underlying voice-session logic intact and the codebase structure clean and scalable.

## Users & Use Cases

- **Primary user**: Evaluators / builders running and iterating on a real-time voice agent.
- **Primary jobs**:
  - Configure a new voice session (LLM/STT/TTS/interruptibility).
  - Start/stop a session reliably.
  - Observe live session state (“Listening/Thinking/Speaking”) and latency.
  - Understand errors quickly (API vs transport vs session lifecycle).

## Product Tone / Brand Direction

- **Tone**: Premium, calm, “real product” dashboard.
- **Visual style**: Light-first, refined neutrals, subtle borders, minimal gradients, restrained accent color.
- **Accessibility**: Clear focus rings, proper labels, semantic structure; no color-only signaling.

## Information Architecture

Use a **sidebar dashboard shell** to future-proof navigation as features grow.

### Top-level routes

- `/` — **Dashboard**
  - “Configure session” (default when disconnected)
  - “Live session” panel (when connected)
  - “System status” and key metrics (latency, bot state)
- `/sessions` — **Sessions** (placeholder for future: history, transcripts, recordings)
- `/settings` — **Settings** (placeholder for future: defaults, env info)

Routing can start minimal (only `/` implemented) but the shell must be built to support additional routes cleanly.

## Layout / Shell

### App shell

- **Sidebar**: brand header + nav items + footer (build info / links).
- **Top header**: page title + session connection indicator + primary action area (e.g., Start/Stop).
- **Main content**: centered container with comfortable max width; responsive padding.

### Responsive behavior

- Desktop: sidebar pinned, content in main.
- Mobile: sidebar collapses into a sheet/drawer; primary actions remain easily reachable; forms use single-column layout.

## Core UI Modules (on `/`)

### 1) Status Row (always visible on dashboard)

- **Bot state**: Badge/pill indicating Listening / Thinking / Speaking.
- **Latency**: Stat card or compact metric block showing ms.
- **Connection**: small indicator (Connected / Disconnected / Error).

### 2) Configure Session (when disconnected)

Displayed as a structured card with grouped sections:

- **LLM**: system prompt (textarea), temperature (input), max tokens (input)
- **STT**: temperature (input)
- **TTS**: voice (select), speed (input), temperature (input)
- **Interruptibility**: percentage (slider or numeric input with bounds)

Primary CTA: **Start session** (disabled while submitting). Errors appear as an Alert at top of the form.

### 3) Live Session (when connected)

- **Live status**: the status row remains and updates instantly.
- **Controls**: prominent **Stop session** action; start is irrelevant while connected.
- **Errors**: transport disconnects or API issues shown as Alerts; user can recover by stopping/resetting.

## Component Inventory (shadcn/ui)

Use shadcn/ui components as building blocks, composing rather than reinventing:

- Layout: `Sidebar`, `Sheet` (mobile), `Separator`, `ScrollArea`
- Content: `Card`, `Badge`, `Alert`, `Skeleton`
- Form: `Form` (or equivalent shadcn patterns), `Input`, `Textarea`, `Select`, `Switch`, `Slider`, `Button`
- Feedback: `sonner` toasts (optional for non-blocking success/failure)

## Clean Code Structure (Frontend)

Keep a clear separation between:

- **App shell & routing** (layout, navigation, chrome)
- **Feature modules** (session-config, session-control, dashboard panels)
- **API & hooks** (already present via TanStack Query + `useVoiceSession`)
- **UI primitives** (`components/ui/*` from shadcn)

Proposed structure (additions only; keep existing features):

- `frontend/src/components/app/` — app shell components (Sidebar, Header, PageLayout)
- `frontend/src/app/(dashboard)/layout.tsx` — route group layout (optional; can evolve)
- `frontend/src/features/dashboard/` — keep existing panels; restyle using shadcn components
- `frontend/src/features/session-config/` — migrate form markup to shadcn forms + inputs
- `frontend/src/features/session-control/` — migrate buttons/layout to shadcn

## Non-Goals (for this UI pass)

- No new backend capabilities.
- No redesign of voice session state machine logic.
- No transcript viewer, recordings UI, or advanced logs (leave placeholders if helpful).

## Acceptance Criteria

- Dashboard feels like a **premium SaaS product** (not a raw demo page).
- Inline styles on `/` are removed; layout uses shadcn + Tailwind semantics.
- UI remains deterministic and responsive to bot events (Listening/Thinking/Speaking updates correctly).
- Errors are visible, actionable, and don’t break layout.
- Code structure remains clean and extensible for future routes.

