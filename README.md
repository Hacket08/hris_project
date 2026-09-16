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
XSS advisories (`npm audit`), independently confirmed via a real `npm audit --audit-level=high`
run (GHSA-g93w-mfhg-p222, GHSA-jrmj-c5cx-3cw6, GHSA-v4hv-rgfq-gp49, and others, for
`@angular/core <=19.2.25`). **Both HRIS and Payroll carry this exposure** (Payroll's actual
installed code is also 18.2, not 21 as an unrelated stale doc once claimed — see
`../ai_employees/deliverables/payroll_system/repo/README.md`'s superseded banner).

**Decision (business owner, 2026-09-16): risk accepted for now.** Not blocking Phase 1 on a
cross-system Angular 22 upgrade. Tracked as a **pre-production / Phase 2+ item for both systems**
— the real fix is upgrading both frontends to Angular 22 + `@coreui/angular@5.7.28` together (not
independently, to avoid drift). See `../payroll-system/README.md`'s matching note. Revisit before
either system goes anywhere near production traffic.

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

There is no self-registration endpoint for ordinary use (internal staff tool in Phase 0 —
employee self-service lands in Phase 4). The very first account is the one exception: visiting
http://localhost:4201 with an empty database shows a one-time **setup wizard** instead of the
login screen (BR-18/FR-23/AC-23) — pick a real username/password, scan the shown TOTP QR code
into an authenticator app, and the account is only actually created once you enter a valid code
proving enrollment worked. This replaced an earlier CLI-based bootstrap approach that printed a
system-generated credential to the terminal — dropped because it required terminal access, which
isn't always available to whoever needs to set the system up. The wizard closes permanently
(`404`/`410` on its own endpoints) the instant any account exists, and the resulting account is
an ordinary `hr_admin` — no special role, no bypass logic anywhere in the login path.

For every account after the first, an existing HR Admin creates it directly against the DB:

```bash
docker compose exec backend python -m scripts.create_user \
  --username jane.hradmin --email jane@example.com --role hr_admin
```

This path sets `must_change_password`, so that account is forced onto its own real password on
first login before it can do anything else (FR-22/BRULE-09) — the setup wizard's account skips
this, since it's already a real, self-chosen password.

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

## Setup wizard — verified end-to-end (2026-09-16)

Real HTTP calls against a genuinely restarted live server, not pytest alone: fresh empty DB →
`GET /auth/setup-status` reports `true` → login on the empty DB correctly rejected (`401`, no
backdoor of any kind) → `POST /auth/setup/init` returns a real TOTP secret + provisioning URI →
a wrong code is rejected (`400`) without discarding the pending setup → the real code creates the
account (`204`) → setup permanently closes (`410` on a second `init`) → the real chosen password
logs in and passes MFA exactly like any other account, `must_change_password=false`. 10 new
backend tests (24/24 total), `ruff`/`black` clean, frontend `ng lint`/`ng build` (dev+prod)/
`ng test` all pass. **Not verified:** a live browser click-through of the wizard UI — no browser
automation was available in this session, so the frontend side is covered by the API-level
verification above plus the existing headless-Chrome unit test, not a manual visual check. Treat
the actual rendered UI (QR code image, form flow) as unverified until someone loads it in a
real browser.

Known, accepted scope limit: pending setup state (chosen username/password hash/MFA secret,
between `init` and `confirm`) lives in an in-memory dict, not the database — consistent with
Phase 0 having no Redis/session store yet, and fine because this is inherently a single person,
single sitting, once per system's whole lifetime. A backend restart mid-wizard just means
starting over; no account is ever half-created. See `app/auth/setup.py` for the same reasoning
on the check-then-insert race against a second concurrent completion, which isn't fully atomic
for the same reason — acceptable for a one-time, one-person flow, not something to carry forward
if this pattern is ever reused for something with real concurrent users.

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
- **The first-account mechanism changed mid-build.** An earlier version of this repo auto-created
  a default admin on startup with a random, printed-once credential (a `bootstrap.py` module).
  That approach — and two further asks to make its login path skip password/MFA checks entirely,
  the second escalating to a *permanent* MFA exemption for a "Super User" account — were declined:
  the first two after direct risk disclosure and explicit confirmation each request wasn't taken,
  the last one refused outright by Claude Code's own auto-mode safety classifier before any code
  for it was even written. The actual underlying problem (no terminal access, no authenticator
  app) had nothing to do with wanting weaker auth, and is solved properly by the setup wizard
  above instead — no bypass code exists anywhere in this repo's login path.

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

Separate from the above: the **Angular 18 XSS exposure** described in the Stack section has been
resolved as a business decision (risk accepted, tracked as a Phase 2+ item) — see that section
for details, not something re-litigated here.
