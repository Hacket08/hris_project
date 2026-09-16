# HRIS System (Philippines MVP) — Repository

**Status: Phase 0 (Foundations) complete. Build stops here — see "Why the build stops here" below.**

This repository implements Phase 0 of the build sequence in
[`12_development_plan.md`](../ai_employees/deliverables/hris_system/12_development_plan.md) §10:
repo scaffold, CI pipeline, local Docker Compose environment, authentication with mandatory TOTP
MFA, and the base `users`/`audit_log` schema with database-grant-level append-only enforcement on
the audit log. It does **not** implement any business functionality (employee records, org
structure, attendance, leave, benefits, etc.) — that starts in Phase 1 and is explicitly out of
scope for this repo state.

Full specs live in `ai_employees/deliverables/hris_system/` (two levels up from this repo): start
with `12_development_plan.md`, then `09_module_design.md`, `11_mvp_design.md`, `05_data_model.md`,
`10_philippines_localization.md`, `06_acceptance_and_uat_criteria.md`, and
`08_open_questions_and_assumptions.md`.

This system is the HR counterpart to the sibling **Payroll System** (`../payroll-system/`), which
this Phase 0 build deliberately mirrors in stack, structure, and scope discipline.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 16, `pyjwt` + `bcrypt` +
  `pyotp` for auth/MFA, `cryptography` (Fernet) for application-level encryption.
- **Frontend:** Angular **18.2** (standalone components, signals) with the **CoreUI Angular Admin
  Template** (`@coreui/angular` + `@coreui/coreui` + `@coreui/icons-angular`) — a business
  decision confirmed 2026-09-16, applying to both this system and Payroll, replacing the earlier
  Angular Material recommendation.
- **Database:** PostgreSQL 16.

### Angular version — a judgment call, not a default

The dev plan flagged an unresolved compatibility question: the local CoreUI reference template
(`../coreui-free-angular-admin-template/`) is pinned to `@coreui/angular@5.7.28`, which requires
Angular `^22.1.0`. Before writing any code, this was checked against the real npm registry rather
than assumed:

- `@coreui/angular@5.2.25` — verified via `registry.npmjs.org` — peer-depends on
  `@angular/core ^18.2.0`, and its own README confirms it's the officially tagged `v5-ng18`
  release (not an unsupported downgrade hack).
- Payroll's actual installed frontend version (`../payroll-system/frontend/package.json`) is
  Angular **`^18.2.0`** with **no UI kit dependency yet** — contradicting
  `../payroll-system/README.md`'s claim of "Angular 21 + Angular Material," which is stale/
  aspirational and does not match Payroll's real committed code.

**Decision:** built this repo on Angular 18.2 + `@coreui/angular@5.2.25` (pinned to an *exact*
version, not a caret range — `^5.2.25` resolves to 5.7.28 today, which silently pulls in the
Angular 22 peer requirement; see `frontend/package.json`). This needs no Angular upgrade on either
system and keeps both frontends on the same major version, per the dev plan's own stated goal.

**Known trade-off, flagged rather than hidden:** Angular 18.2 has several disclosed high-severity
XSS advisories (`npm audit`), the same class of vulnerability Payroll's README cites as its reason
for wanting Angular 21+. Since Payroll's *actual* code is also on 18.2 (not 21 as documented),
**both systems currently carry this exposure**. Resolving it means upgrading both frontends to
Angular 22 + `@coreui/angular@5.7.28` together — a larger, cross-system change outside this
Phase 0 build's scope. Recommend the business owner/tech lead decide whether that upgrade happens
before or after Phase 1, rather than each system drifting independently.

## Repository layout

```
backend/             FastAPI app, Alembic migrations, tests, bootstrap CLI script
frontend/            Angular app (auth/MFA screens + authenticated shell only in Phase 0)
docker-compose.yml   Local dev: postgres + backend + frontend
.github/workflows/   CI (lint, unit tests, integration tests, build)
```

No Redis/Celery service in `docker-compose.yml` — unlike Payroll's actual compose file (which
includes both despite nothing using them yet), this Phase 0 has no background jobs (leave accrual,
probationary-deadline checks, and the Payroll CSV export job are all Phase 2+/5 per
`12_development_plan.md` §10). Add `redis` + a `celery-worker` service when the first async job is
actually built, not before.

## Running locally

```bash
cp backend/.env.example backend/.env
# edit backend/.env: set JWT_SECRET_KEY and FIELD_ENCRYPTION_KEY (generate with the
# commands in .env.example's comments), and the DB passwords if you changed them.

docker compose up --build
```

- Backend: http://localhost:8001 (OpenAPI docs at `/docs`)
- Frontend: http://localhost:4201

(Ports are offset from Payroll's 8000/4200/5432 so both systems' local stacks can run
side by side without colliding.)

There is no self-registration endpoint (internal staff tool in Phase 0 — employee self-service
lands in Phase 4). Bootstrap the first user directly against the DB:

```bash
docker compose exec backend python -m scripts.create_user \
  --username jane.hradmin --email jane@example.com --role hr_admin
```

Then sign in at http://localhost:4201/login — first login walks you through TOTP MFA
enrollment (scan the QR code / use the printed secret with any authenticator app).

## Running tests

**Backend** (from `backend/`, with a venv active — `pip install -e ".[dev]"`):

```bash
pytest -v            # unit tests always run; Postgres-backed integration tests
                      # auto-skip if DATABASE_URL isn't reachable
ruff check app tests scripts
black --check app tests scripts
```

**Frontend** (from `frontend/`, after `npm install`):

```bash
npm run lint
npm test                                          # interactive (Karma watch mode)
npx ng test --watch=false --browsers=ChromeHeadless  # headless, single run
npm run build                                     # dev config
npm run build -- --configuration production
```

## What was actually verified in this session

Everything below was run for real, not just written:

- **Backend:** `ruff check`, `black --check` — clean. `pytest` (unit only, no DB) — 7/7 pass.
  Then, against a real, disposable, locally-provisioned **PostgreSQL 17** instance (its own data
  directory under the system temp folder, port 55440, isolated from any other Postgres on this
  machine, provisioned and left for the business owner to tear down — no Docker available in this
  build sandbox): `alembic upgrade head` applied for real, then `pytest -v` — **14/14 pass**,
  including `test_audit_log_lockdown.py` connecting as the restricted `hris_app` role and
  confirming Postgres itself rejects `UPDATE`/`DELETE` on `audit_log` with a real permission-denied
  error (not just application-layer discipline). A real `uvicorn` process (not the in-process ASGI
  test client) was started and driven end-to-end with `curl`: bootstrap a user via the CLI →
  `POST /auth/login` → generate a real TOTP code with `pyotp` → `POST /auth/mfa/verify` →
  `GET /auth/me` with the access token (200) → `GET /auth/me` with no token (401, confirmed).
- **Frontend:** `npm install` (after fixing a real dependency-resolution bug — see below),
  `npx ng lint` — clean. `npx ng build` (development and production configurations) — both
  succeed; production initial bundle ≈611 KB raw / ≈110 KB estimated transfer. `npx ng test
  --watch=false --browsers=ChromeHeadless` against a **real, locally installed headless Chrome**
  — 1/1 pass.
- **Not run:** `docker compose up` itself (no Docker in this build sandbox) — `docker-compose.yml`
  and both Dockerfiles are written to the same conventions as everything that *was* verified, but
  treat "does `docker compose up` work end-to-end" as unverified until someone runs it with Docker
  available, exactly the same caveat Payroll's own README carries.

## Real bug caught during verification

`npm install` with `@coreui/angular: "^5.2.25"` (a caret range) resolved to `5.7.28` — the newest
version satisfying that range — which peer-depends on Angular `^22.1.0`, not 18. This produced an
`ERESOLVE` conflict against the pinned Angular 18 packages. Fixed by pinning `@coreui/angular`,
`@coreui/coreui`, and `@coreui/icons-angular` to their **exact** Angular-18-compatible versions in
`frontend/package.json` rather than caret ranges — CoreUI's own semver ranges span multiple Angular
majors within the same package major version, which is unusual enough to be worth calling out
explicitly for whoever bumps these dependencies later.

A second, smaller issue: `@coreui/icons-angular@5.2.25` (the Angular-18-targeted release) doesn't
export a `provideIcons()` function — that standalone-friendly API was added in a later CoreUI
major. Since Phase 0's auth screens don't render any icons yet, `app.config.ts` doesn't register
an icon set at all; wire up `IconSetService` (module-based API, documented in
`node_modules/@coreui/icons-angular/README.md`) when a Phase 1+ screen actually needs one.

## Known deviations / judgment calls from `12_development_plan.md`

- **Schema scope narrower than Payroll's own README claims for itself.** The dev plan's Phase 0
  row says "base schema migration"; this was read as *just* the `users`/`audit_log` tables needed
  for the stated exit criterion ("a user can log in with MFA"), not the full ~14-table schema from
  §4. This matches what Payroll's Phase 0 **actually** built (verified directly:
  `payroll-system/backend/alembic/versions/0001_phase0_foundations.py` creates 3 tables —
  `legal_entity`, `users`, `audit_log` — not the "18 tables" its own README and an earlier
  automated build-log claimed). Building the full HRIS schema now, based on the inflated
  description rather than the real precedent, would have been scope creep against what "Phase 0"
  actually means in this codebase family. The remaining §4 tables (employee, position,
  attendance_record, leave_request, benefit_plan, etc.) are Phase 1+ per the build sequence.
- **CoreUI Angular pinned to exact versions**, not caret ranges — see "Real bug caught" above.
- **No Redis/Celery in `docker-compose.yml`** — see "Repository layout" above.
- **`GET /auth/me` is the only protected route in Phase 0** (plus `require_role()` existing as
  infrastructure in `app/auth/deps.py` for Phase 1+ routers to use) — mirrors Payroll's own actual
  Phase 0 scope (its `router.py` has no `/users` GET/POST either, despite an earlier build log
  claiming otherwise).

## Why the build stops here (Phase 0 → Phase 1 boundary)

Per `08_open_questions_and_assumptions.md`, two must-answer questions block Phase 1:

| # | Question | Blocks |
|---|---|---|
| 6 | What is the current HR process (spreadsheets, paper 201 files, an existing legacy system)? | Sizes the actual gap and migration/data-entry effort for Phase 1's Employee Master |
| 7 | Which system is authoritative for government ID numbers (SSS/PhilHealth/Pag-IBIG/TIN) — this HRIS, Payroll, or both? | Changes what fields the Employee Master (Phase 1) and the Payroll CSV export (Phase 5) even contain |

Open questions #9–#12 (growth horizon, probationary lead time, CBA/special regimes, performance/DR
SLAs) matter before Phase 2/5, not Phase 0, per the dev plan's own sequencing notes — not chased
here. #8 (SSO vs. internal+MFA) doesn't block Phase 0 either: the dev plan already defaults to
internal+MFA for the MVP, which is exactly what got built, swappable later if SSO is confirmed.

Also unresolved, separate from the above: the **Angular 18 XSS exposure** described in the Stack
section — a decision for the business owner/tech lead, not something to silently pick a side on
here.
