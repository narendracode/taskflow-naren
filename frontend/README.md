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

# Or from the project root:
make frontend-install
make frontend
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

From the project root:

| Command | Description |
|---------|-------------|
| `make frontend` | Start the React dev server (port 3000) |
| `make frontend-install` | Install frontend npm dependencies |

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
    │   ├── tasks/
    │   │   └── tasksApi.ts     # Task CRUD endpoints
    │   └── users/
    │       └── usersApi.ts     # User list & profile endpoints
    ├── hooks/
    │   └── useProjectSSE.ts    # SSE hook — real-time task event subscription
    ├── components/
    │   ├── Navbar.tsx           # Top nav with user avatar & logout
    │   ├── ProtectedRoute.tsx   # Auth guard (redirects to /login)
    │   ├── ConfirmDialog.tsx    # Reusable confirmation dialog
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

## Real-Time Updates (SSE)

The frontend receives real-time task updates via **Server-Sent Events** so that all open tabs and devices stay in sync without polling.

### How It Works

1. **Connection** — The `useProjectSSE` hook (in `src/hooks/useProjectSSE.ts`) opens an `EventSource` to `GET /projects/{id}/events?token=<jwt>` when a user views a project detail page. Since the browser `EventSource` API cannot set HTTP headers, the JWT is passed as a query parameter.

2. **Event Handling** — The hook listens for three named SSE events and patches the **RTK Query cache** directly using `tasksApi.util.updateQueryData()`:

   | SSE Event | Cache Action |
   |-----------|-------------|
   | `task_created` | Inserts the new task at the top of the list (with dedup check) |
   | `task_updated` | Replaces the task in-place, or inserts if not present |
   | `task_deleted` | Removes the task from the list |

   Each event also invalidates the `ProjectStats` tag so dashboard counters refresh.

3. **Cache Patching Strategy** — The hook iterates over _all_ cached `getProjectTasks` queries matching the current `projectId` (regardless of active filters) and applies the update to each. This ensures every filter view stays consistent.

4. **Deduplication** — When the current tab creates a task, RTK Query's own `invalidatesTags` already adds it to the cache. The SSE `task_created` handler checks `draft.data.some(t => t.id === task.id)` to avoid duplicates.

5. **Cleanup** — When the component unmounts or the `projectId`/`token` changes, the `EventSource` is closed. The backend detects the disconnection and cleans up the subscription.

### What Is `EventSource`?

`EventSource` is a **built-in browser Web API** (part of the HTML Living Standard) that provides a client-side interface for receiving Server-Sent Events over HTTP.

- **Protocol** — Opens a long-lived HTTP GET connection to a server endpoint that responds with `Content-Type: text/event-stream`. The server keeps the connection open and pushes text-formatted events down the stream.
- **Transport format** — Messages are plain text with a simple line-based protocol:
  ```
  event: task_created
  data: {"id": "abc", "title": "Fix bug"}
  ```
  Each message has an optional `event:` name and a `data:` payload, terminated by a blank line.
- **Unidirectional** — Data flows only from server → client (unlike WebSockets which are bidirectional). The client can only receive; to send data back it uses regular HTTP requests (REST calls).
- **Auto-reconnect** — If the connection drops, `EventSource` automatically reconnects after a few seconds without any custom code.
- **Named events** — You can listen for specific event types using `es.addEventListener("task_created", handler)`, which maps to the `event:` field in the stream.
- **Limitation** — Cannot set custom HTTP headers (like `Authorization: Bearer ...`), which is why the backend accepts the JWT as a query parameter (`?token=`).

Usage in this project:

```typescript
const es = new EventSource(url);              // opens the SSE connection
es.addEventListener("task_created", (e) => {  // listen for named events
  const task = JSON.parse(e.data);
});
es.close();                                   // tear down on cleanup
```

#### EventSource vs WebSocket

| | EventSource (SSE) | WebSocket |
|---|---|---|
| Direction | Server → Client only | Bidirectional |
| Protocol | HTTP | `ws://` / `wss://` |
| Reconnect | Automatic | Manual |
| Data format | Text only | Text + binary |
| Complexity | Simple | More complex |

SSE is the simpler choice when you only need server-to-client push (like broadcasting task updates), which is exactly this project's use case.

### Key Files

| File | Role |
|------|------|
| `src/hooks/useProjectSSE.ts` | SSE connection, event listeners, RTK Query cache patching |
| `src/pages/ProjectDetailPage.tsx` | Activates SSE via `useProjectSSE(projectId)` |
| `src/features/tasks/tasksApi.ts` | RTK Query task endpoints (cache structure that SSE patches) |
| `src/features/api/baseApi.ts` | Base API with `tagTypes` used for invalidation |

## Docker / Production

The frontend Dockerfile is a multi-stage build:

1. **Build stage** — `node:20-alpine`, runs `npm ci` + `npm run build`
2. **Serve stage** — `nginx:1.27-alpine`, serves the static `dist/` with SPA fallback

```bash
# From the project root (docker-compose.yml includes the frontend service)
docker compose up --build
```
