# Xplore frontend (Person A)

Vite 6 + React 19 + TypeScript + Tailwind 4. Talks to the API described in `../shared/` (contract v1.0).

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (mock mode by default)
npm run build        # type check + production build
```

## Modes

Copy `.env.example` to `.env.local` and set:

| Variable | Meaning |
| --- | --- |
| `VITE_API_MODE` | `mock` (default): in-browser fixtures, everything labelled illustrative. `live`: Person B's API. |
| `VITE_API_BASE_URL` | Live API base URL, e.g. the Modal FastAPI URL. Default `http://localhost:8000`. |
| `VITE_EXAMPLE_EXPERIMENT_ID` | Genuine saved experiment shown by "Open saved example". |

In live mode the backend must allow CORS from the frontend origin.

## Mock-mode test hooks

- `?experiment=fixture-completed` / `?experiment=fixture-partial` open the shared fixtures.
- `?mock_fail=firm` before clicking **Run comparison** makes that candidate fail (parent becomes `partial`).
- `?mock_fail=all` makes every candidate fail (`failed`).
- Re-running the same candidates and load completes instantly, mirroring the backend cache.

## Rules the UI follows (plan §5, §7, §13)

- Missing measurements render as "—"; no sample numbers are substituted.
- Fixtures and mock mode always show the illustrative label; evidence status, engine and live/cached label stay visible.
- Progress is "N of M runs completed", never an invented percentage.
- The shortlist comes from the backend's `selection`; the explanation is a fixed template over the record (no AI).
- Polling every 2 s stops at `completed` / `partial` / `failed`; the experiment ID lives in the URL so refresh restores it.

## Layout

```text
src/
  api/        client.ts (mode switch), live.ts (fetch), mock.ts (fixtures), errors.ts, types.ts
  types/      contract.ts (mirror of shared/experiment.schema.json)
  hooks/      useCatalog, useExperiment (polling)
  lib/        explain.ts (deterministic explanation), format.ts, colors.ts, recent.ts
  components/ SetupForm, ExperimentStatusBar, CandidateResults, DeformationChart, ComparisonTable,
              ExplanationPanel, AssumptionsPanel, ui
```
