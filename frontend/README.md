# Frontend

React 19 + TypeScript + Vite UI for the Speech to Text app. See the [root README](../README.md) for
setup, architecture and deployment.

```bash
npm install
DEV_API_TARGET=http://127.0.0.1:8000 npm run dev   # proxies /api (incl. WebSocket) to the backend
npm run lint && npx tsc -b && npm test             # quality gates
npm run build                                      # outputs dist/, served by the backend in production
```

Layout: `src/api` (typed client), `src/audio` (mic capture and 16 kHz PCM resampling),
`src/hooks` (live session reducer, history, languages, quota), `src/components` (Recorder, History,
EntryDialog). The AudioWorklet processor lives in `public/pcm-worklet.js`.
