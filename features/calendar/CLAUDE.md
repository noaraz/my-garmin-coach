# Calendar — CLAUDE

## UI Design

- **Tone**: Athletic, utilitarian, clean — Strava meets Notion
- **Colors**: Dark sidebar, light main. Zone colors: blue (z1) → red (z5)
- **Typography**: Clean sans-serif. Monospace for pace/time values.
- **Cards**: Colored blocks showing zone distribution, name, duration, sync icon.

## Frontend Scaffold (First Time Only)

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss @tailwindcss/vite
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Also add `Dockerfile.dev` and update `docker-compose.yml` to include frontend service.

## Card Click → Builder Navigation

`WorkoutCard` navigates to `/builder?id={workout_template_id}` on click:
- `onClick` on the card container — skipped when `workout_template_id` is null
- `cursor: pointer` only when template ID exists
- Remove button uses `e.stopPropagation()` to avoid triggering card navigation
- `BuilderPage` already reads `searchParams.get('id')` — no route change needed

## Testing: `useNavigate` Requires a Router

Any component using `useNavigate()` (including `WorkoutCard`) will crash tests with
*"useNavigate() may be used only in the context of a Router component."*

Fix — wrap renders in `MemoryRouter`:

```typescript
import { MemoryRouter } from 'react-router-dom'

const renderPage = (props: { initialDate?: Date } = {}) =>
  render(<MemoryRouter><CalendarPage {...props} /></MemoryRouter>)
```

Apply this wrapper whenever any child component uses `useNavigate`, `useParams`, `useLocation`, etc.
