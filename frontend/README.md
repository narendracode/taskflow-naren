# TaskFlow Frontend

React single-page application for managing projects and tasks, built with Vite, TypeScript, and Tailwind CSS.

## Tech Stack

- **React 18** with TypeScript
- **Vite 5** — dev server & bundler
- **Redux Toolkit** + **RTK Query** — state management & API layer
- **React Router 6** — client-side routing
- **Tailwind CSS 3** — utility-first styling
- **Radix UI** — accessible headless primitives (Dialog, Select, Label)
- **React Hook Form** — form handling
- **Lucide React** — icons
- **date-fns** — date formatting

## Quick Start

```bash
cd frontend
cp .env.example .env    # adjust if needed
npm install
npm run dev
```

The app runs at [http://localhost:3000](http://localhost:3000).

API requests go directly to the backend at `http://localhost:8000` (configurable via `VITE_API_URL`).

> Make sure the backend is running (`make db-start && make migrate-run && make seed && make server` from the project root).

## Seed Login

| Email | Password |
|-------|----------|
| `test@example.com` | `password123` |
| `alice@example.com` | `Password123!` |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server (port 3000) |
| `npm run build` | Type-check + production build → `dist/` |
| `npm run preview` | Preview the production build locally |

Or from the project root: `make frontend`

## Environment Variables

See [.env.example](.env.example):

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |

## Pages & Routes

| Route | Page | Auth |
|-------|------|------|
| `/login` | Login form | Public |
| `/register` | Registration form | Public |
| `/projects` | Project list (owned & assigned) | Protected |
| `/projects/:id` | Project detail with tasks & stats | Protected |
| `*` | Redirects to `/projects` | — |

## Project Structure

```
frontend/
├── Dockerfile                  # Multi-stage: build → nginx
├── nginx.conf                  # Production reverse proxy + SPA fallback
├── index.html                  # Vite entry point
├── package.json
├── vite.config.ts              # Aliases, dev server config
├── tailwind.config.js          # Custom theme tokens (shadcn/ui style)
├── tsconfig.json
├── .env.example
├── public/
└── src/
    ├── main.tsx                # React root + Redux Provider
    ├── App.tsx                 # Router setup + AuthLayout
    ├── index.css               # Tailwind + CSS custom properties
    ├── app/
    │   └── store.ts            # Redux store, typed hooks
    ├── features/
    │   ├── api/
    │   │   └── baseApi.ts      # RTK Query base API (fetchBaseQuery)
    │   ├── auth/
    │   │   ├── authApi.ts      # Login/register endpoints
    │   │   └── authSlice.ts    # Auth state (token, user, persistence)
    │   ├── projects/
    │   │   └── projectsApi.ts  # Project CRUD endpoints
    │   └── tasks/
    │       └── tasksApi.ts     # Task CRUD endpoints
    ├── components/
    │   ├── Navbar.tsx           # Top nav with user avatar & logout
    │   ├── ProtectedRoute.tsx   # Auth guard (redirects to /login)
    │   ├── EmptyState.tsx       # Empty placeholder component
    │   ├── TaskModal.tsx        # Create/edit task dialog
    │   └── ui/                  # Reusable primitives (shadcn/ui style)
    │       ├── badge.tsx
    │       ├── button.tsx
    │       ├── card.tsx
    │       ├── dialog.tsx
    │       ├── input.tsx
    │       ├── label.tsx
    │       ├── select.tsx
    │       ├── spinner.tsx
    │       └── textarea.tsx
    ├── pages/
    │   ├── LoginPage.tsx
    │   ├── RegisterPage.tsx
    │   ├── ProjectsPage.tsx
    │   └── ProjectDetailPage.tsx
    ├── types/
    │   └── index.ts            # Shared TypeScript interfaces
    └── lib/
        └── utils.ts            # cn(), error extraction, formatDate
```

## API Integration

All API calls go through RTK Query with a base URL set via `VITE_API_URL` (defaults to `http://localhost:8000`).

The frontend calls the backend directly — there is no dev proxy. In production (Docker), set `VITE_API_URL` at build time to the appropriate backend URL.

Auth tokens are stored in Redux and attached via `prepareHeaders` in the base query. The auth slice persists the token to `localStorage` for session survival across page reloads.

## Docker / Production

The frontend Dockerfile is a multi-stage build:

1. **Build stage** — `node:20-alpine`, runs `npm ci` + `npm run build`
2. **Serve stage** — `nginx:1.27-alpine`, serves the static `dist/` with SPA fallback

```bash
# From backend/ directory (includes frontend in the compose stack)
docker compose up --build
```
