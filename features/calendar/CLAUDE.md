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
