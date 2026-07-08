# Diggo — Auth pages migration to Next.js — Design Spec

Date: 2026-07-08
Status: approved

## Goal

Migrate the four public auth pages — login, signup, email confirmation, password reset — from FastAPI-rendered Jinja2 templates to the new Next.js frontend, reusing the design system established in the "Frontend Foundations" phase (dark-default/teal-accent tokens, Inter, shadcn/ui). This is the first real page migration on top of that foundation: it proves the whole pipeline end-to-end (proxy routing to `web`, the Supabase-JS → cookie-session handshake, build-time public env vars) before the much larger Candidatures page is attempted.

## Context

Today all four pages (`dashboard/templates/auth/{login,signup,confirm,reset-password}.html`) are FastAPI-rendered Jinja2 templates using `@supabase/supabase-js` loaded from a CDN, calling Supabase Auth directly from the browser with `supabase_url`/`supabase_anon_key` injected via Jinja2 template globals. After a successful Supabase sign-in, the page `POST`s the access/refresh tokens to `POST /auth/session`, which validates the token and sets httpOnly cookies (`dashboard/auth.py:set_auth_cookies`); login redirects to `/profile`, signup redirects to `/auth/confirm`, password reset redirects to `/login`. None of this business logic changes — only which service renders the page and where the session-cookie endpoint lives.

## Routing changes (nginx)

`proxy/nginx.conf` gains four new location blocks, each proxying to `web` instead of the current catch-all `api`:
- `/login`
- `/signup`
- `/auth/confirm`
- `/auth/reset-password`

Everything else keeps going to `api` unchanged, including every still-unmigrated protected page (`/candidatures`, `/profile`, `/stats`, `/settings`) and their existing behavior of redirecting an unauthenticated visitor to `/login` — that redirect doesn't care which service ends up serving the page.

`POST`/`DELETE /auth/session` moves to `/api/auth/session`, so it's covered by the existing `/api/` → `api` block with no special-casing needed. Renaming it avoids an unresolvable path collision: nginx cannot route `/auth/confirm` (a page, → `web`) and `/auth/session` (an API call, → `api`) differently under a single `/auth/*` prefix rule.

## Backend changes (FastAPI)

- `dashboard/api.py` gains `POST /api/auth/session` and `DELETE /api/auth/session`, moved verbatim (same body: `validate_access_token`, `set_auth_cookies`/`clear_auth_cookies`) from `dashboard/app.py`.
- The four now-unreachable Jinja2 GET routes (`/login`, `/signup`, `/auth/confirm`, `/auth/reset-password`) are deleted from `dashboard/app.py`, along with their templates (`dashboard/templates/auth/*.html`) — once nginx no longer routes any traffic to them, they're dead code, and this project's convention is deletion over dead-code accumulation.
- `templates.env.globals["supabase_url"]`/`["supabase_anon_key"]` (`dashboard/app.py:139-140`) and the module-level constants that feed them (`_SUPABASE_URL`, `_SUPABASE_PUBLIC_URL`, `_SUPABASE_ANON_KEY`, `dashboard/app.py:36-38`) are used exclusively by the three Jinja2 templates being deleted (`login.html`, `signup.html`, `reset-password.html` — confirmed via grep, no other template references them). They're removed in the same pass rather than left as dead globals.
- Nothing else in `dashboard/app.py` changes. `get_current_user`, `get_current_user_api`, `require_onboarding_complete` are all untouched — they already just set a `location: /login` header or raise 401; they have no opinion on which service renders `/login`.

## Frontend (Next.js)

- `frontend/lib/supabase.ts` — one shared browser Supabase client factory, built from `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`. These are Next.js build-time public env vars, inlined into the client bundle at `npm run build` — not new exposure, since the anon key is already public today (embedded directly in the current Jinja2-rendered HTML).
- Four pages, each a shadcn `Card` containing `Label`/`Input` fields and a `Button`, matching the current pages' fields, copy, validation, and redirect targets exactly:
  - `frontend/app/login/page.tsx` — email/password, "mot de passe oublié" reset trigger, redirects to `/profile` on success.
  - `frontend/app/signup/page.tsx` — email/password/confirm (client-side match + min-length-6 check, same as today), redirects to `/auth/confirm` on success.
  - `frontend/app/auth/confirm/page.tsx` — static "check your email" message, link back to `/login`, Inbucket hint for local dev.
  - `frontend/app/auth/reset-password/page.tsx` — new password/confirm, listens for the Supabase `PASSWORD_RECOVERY` auth event, redirects to `/login` 1.5s after success.
- New shadcn/ui components added: `Input`, `Label`, `Card` (alongside the existing `Button`) — the standard shadcn form primitives, reused by every future page in this redesign that has a form (profile, settings).

## Docker / build changes

`docker-compose.yml`'s `web` service build gets `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` as Docker build args (via `build.args:`), not just `environment:` — Next.js inlines `NEXT_PUBLIC_*` vars into the client bundle at `npm run build` time, inside the `build` stage of `frontend/Dockerfile`, so they must be available then, not only at container-run time.

## Out of scope

- Any change to auth-gating logic for protected pages (`get_current_user`, `require_onboarding_complete`) — those pages aren't migrated yet.
- Any visual/UX change to the auth flow beyond porting it to the new design system — same fields, same copy, same redirect targets, same validation rules as today.
- Server-side session validation in Next.js (e.g. middleware-based route protection) — not needed, since none of these four pages require auth to view.
