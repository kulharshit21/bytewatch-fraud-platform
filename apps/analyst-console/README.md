# Analyst Console

Next.js analyst operations UI for the fraud platform.

## Routes

- `/overview`
- `/cases`
- `/cases/[caseId]`
- `/models`
- `/monitoring`

## Local Development

```bash
npm install
npm run build
npm test
npm run dev
```

The console expects the API at:

- `API_INTERNAL_BASE_URL` for server-side fetches
- `API_PUBLIC_BASE_URL` for local browser-facing references

No queue rows or overview numbers are hardcoded. If there is no data yet, the console intentionally renders empty states instead of fake content.
