# Voice UI (shadcn) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current inline-styled Next.js UI with a premium shadcn/ui dashboard shell (sidebar + header + content), while preserving the existing voice session logic and tests.

**Architecture:** Initialize Tailwind + shadcn/ui in `frontend/`, introduce an `AppShell` (sidebar/header/layout) in `src/components/app/`, then migrate existing feature components (`session-config`, `session-control`, `dashboard`) to compose shadcn primitives rather than raw HTML + inline styles.

**Tech Stack:** Next.js 14 App Router, React 18, TypeScript, TanStack Query, shadcn/ui, Tailwind CSS, Vitest + Testing Library.

---

## Scope Check

This plan covers one subsystem: **frontend UI polish + structure**. No backend or pipeline changes.

## Current Frontend Reality (as of now)

- No `components.json` → shadcn/ui not initialized yet.
- No CSS files under `frontend/src/**` → Tailwind not set up yet.
- Current pages use inline styles:
  - `frontend/src/app/page.tsx`
  - `frontend/src/app/error.tsx`

## Target File Structure (additions/changes)

**Create**
- `frontend/src/app/globals.css` (Tailwind + CSS variables; exact filename can follow shadcn init output)
- `frontend/components.json` (shadcn config)
- `frontend/postcss.config.js` (Tailwind pipeline)
- `frontend/tailwind.config.ts` (Tailwind config)
- `frontend/src/components/app/AppShell.tsx` (sidebar + header + layout slots)
- `frontend/src/components/app/AppSidebar.tsx` (nav model)
- `frontend/src/components/app/AppHeader.tsx` (title + session status slot)
- `frontend/src/components/app/PageContainer.tsx` (max-width + padding)
- `frontend/src/components/app/nav.ts` (nav items: Dashboard/Sessions/Settings)

**Modify**
- `frontend/src/app/layout.tsx` (wire global CSS + app shell wrapper)
- `frontend/src/app/page.tsx` (use AppShell + shadcn components; remove inline styles)
- `frontend/src/app/error.tsx` (use shadcn `Alert` + `Button`; remove inline styles)
- `frontend/src/features/session-config/SessionConfigForm.tsx` (use shadcn inputs)
- `frontend/src/features/session-control/SessionControlPanel.tsx` (use shadcn buttons/layout)
- `frontend/src/features/dashboard/BotStateBadge.tsx` (use shadcn `Badge` variants)
- `frontend/src/features/dashboard/LatencyPanel.tsx` (use shadcn `Card` or metric style)

**Test updates (expected minimal)**
- `frontend/src/features/session-config/__tests__/SessionConfigForm.test.tsx` (labels/buttons should remain stable)
- `frontend/src/features/session-control/__tests__/SessionControlPanel.test.tsx` (button names should remain stable)
- `frontend/src/features/dashboard/__tests__/Dashboard.test.tsx` (badge text should remain stable)

---

### Task 1: Add Tailwind CSS to `frontend/`

**Files:**
- Create: `frontend/src/app/globals.css`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Install Tailwind dependencies**

Run (from `frontend/`):

```bash
npm install -D tailwindcss postcss autoprefixer
```

- [ ] **Step 2: Initialize Tailwind config**

Run (from `frontend/`):

```bash
npx tailwindcss init -p
```

Expected: creates `tailwind.config.*` and `postcss.config.js` (or equivalent).

- [ ] **Step 3: Create global CSS with Tailwind layers**

Create `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Wire global CSS in App Router layout**

Update `frontend/src/app/layout.tsx` to import the global CSS:

```ts
import "./globals.css";
```

- [ ] **Step 5: Configure Tailwind content globs**

Update `frontend/tailwind.config.*` `content` to include:

```ts
content: ["./src/**/*.{ts,tsx}"]
```

- [ ] **Step 6: Verify build + tests still work**

Run (from `frontend/`):

```bash
npm run build
npm test
```

Expected: both succeed.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tailwind.config.* frontend/postcss.config.js frontend/src/app/globals.css frontend/src/app/layout.tsx
git commit -m "chore(frontend): add tailwind baseline"
```

---

### Task 2: Initialize shadcn/ui in `frontend/`

**Files:**
- Create: `frontend/components.json`
- Modify: `frontend/src/app/globals.css` (CSS variables/theme tokens)

- [ ] **Step 1: Run shadcn init**

Run (from `frontend/`):

```bash
npx shadcn@latest init
```

Choose:
- Framework: Next.js
- Directory: `src/`
- Import alias: `@/` (matches `tsconfig.json`)

Expected: creates `components.json` and updates `globals.css` with CSS variables.

- [ ] **Step 2: Confirm shadcn project info**

Run (from `frontend/`):

```bash
npx shadcn@latest info
```

Expected: prints resolved paths for `components/ui` and utils (e.g. `cn`).

- [ ] **Step 3: Commit**

```bash
git add frontend/components.json frontend/src/app/globals.css
git commit -m "chore(frontend): init shadcn ui"
```

---

### Task 3: Add core shadcn components needed for the shell

**Files:**
- Create/Modify: under `frontend/src/components/ui/*` (generated by shadcn)

- [ ] **Step 1: Add components**

Run (from `frontend/`):

```bash
npx shadcn@latest add button card badge alert separator sheet scroll-area
```

If available/needed for the sidebar block:

```bash
npx shadcn@latest add sidebar
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ui
git commit -m "chore(frontend): add shadcn primitives"
```

---

### Task 4: Introduce `AppShell` (sidebar + header + page container)

**Files:**
- Create: `frontend/src/components/app/AppShell.tsx`
- Create: `frontend/src/components/app/AppSidebar.tsx`
- Create: `frontend/src/components/app/AppHeader.tsx`
- Create: `frontend/src/components/app/PageContainer.tsx`
- Create: `frontend/src/components/app/nav.ts`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Write a failing test that the dashboard chrome renders**

Create `frontend/src/components/app/__tests__/AppShell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { AppShell } from "../AppShell";

test("renders primary navigation", () => {
  render(
    <AppShell title="Dashboard">
      <div>Body</div>
    </AppShell>
  );
  expect(screen.getByRole("navigation")).toBeInTheDocument();
  expect(screen.getByText(/Dashboard/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to confirm failure**

Run (from `frontend/`):

```bash
npm test -- AppShell.test.tsx
```

Expected: FAIL because `AppShell` doesn’t exist yet.

- [ ] **Step 3: Implement the minimal shell**

Implement:
- `AppShell` composes shadcn `Sidebar` (desktop) + `Sheet` (mobile) + `Separator`
- `AppHeader` shows page title and a right-side slot for status/actions
- `PageContainer` constrains width and provides padding

(Implementation will use semantic Tailwind classes for layout only; visuals are driven by shadcn tokens.)

- [ ] **Step 4: Wire shell at the root layout**

Update `frontend/src/app/layout.tsx` to wrap `children` with the shell **only if it doesn’t break Next metadata/layout constraints** (otherwise wrap in `page.tsx` initially and migrate later).

- [ ] **Step 5: Run unit tests**

```bash
npm test
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/app frontend/src/app/layout.tsx
git commit -m "feat(frontend): add dashboard app shell"
```

---

### Task 5: Restyle `/` page using shadcn cards and the new shell

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Write a failing test for the page headline and primary CTA**

Create `frontend/src/app/__tests__/page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import Page from "../page";

test("shows configure session headline", async () => {
  render(<Page />);
  expect(screen.getByText(/Configure Session/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to see failure (or snapshot mismatch)**

```bash
npm test -- page.test.tsx
```

- [ ] **Step 3: Refactor `page.tsx`**

Goals:
- Remove inline styles and headings in favor of shadcn layout components
- Keep the Pipecat client/provider logic unchanged
- Show errors using shadcn `Alert`
- Use consistent spacing with `flex` + `gap-*` (no `space-y-*`)

- [ ] **Step 4: Run tests and build**

```bash
npm test
npm run build
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/app/__tests__/page.test.tsx
git commit -m "feat(frontend): restyle dashboard page with shadcn"
```

---

### Task 6: Migrate feature components to shadcn primitives (keep labels stable)

**Files:**
- Modify: `frontend/src/features/session-config/SessionConfigForm.tsx`
- Modify: `frontend/src/features/session-control/SessionControlPanel.tsx`
- Modify: `frontend/src/features/dashboard/BotStateBadge.tsx`
- Modify: `frontend/src/features/dashboard/LatencyPanel.tsx`
- Test: existing feature tests

- [ ] **Step 1: Update `BotStateBadge` to use `Badge` variants**

Run:

```bash
npm test -- Dashboard.test.tsx
```

Expected: may fail if text changes; keep badge text identical (“Listening”, “Thinking”, “Speaking”).

- [ ] **Step 2: Update `LatencyPanel` to use `Card` styling**

Keep the visible text format `"<n> ms"` so tests remain stable.

- [ ] **Step 3: Update `SessionControlPanel` to use `Button`**

Keep accessible names **Start Session** / **Stop Session** so tests remain stable.

- [ ] **Step 4: Update `SessionConfigForm`**

Use shadcn `Input`/`Textarea` and keep labels:
- “System Prompt”
- “Interruptibility Percentage”

Then run:

```bash
npm test -- SessionConfigForm.test.tsx
```

- [ ] **Step 5: Full test + build**

```bash
npm test
npm run build
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/features
git commit -m "refactor(frontend): migrate feature ui to shadcn components"
```

---

### Task 7: Restyle the error boundary page

**Files:**
- Modify: `frontend/src/app/error.tsx`

- [ ] **Step 1: Implement shadcn `Alert` + `Button`**

Replace inline styles with shadcn components and sensible layout.

- [ ] **Step 2: Run build**

```bash
npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/error.tsx
git commit -m "feat(frontend): restyle error boundary page"
```

---

## Plan Self-Review

**1) Spec coverage:** The plan implements the sidebar shell + premium dashboard layout, migrates inline styles away, keeps bot state/latency visible, and preserves error visibility.  
**2) Placeholder scan:** No “TBD/TODO” steps; commands and file paths are explicit.  
**3) Type consistency:** No new shared types introduced; existing props/labels are preserved to keep tests stable.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-01-voice-ui-shadcn-implementation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration  
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

