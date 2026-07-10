# Diggo — Settings page migration — Design Spec

Date: 2026-07-10
Status: approved

## Goal

Migrate `/settings` from FastAPI/Jinja2 to Next.js — the last remaining rendered page in the dashboard. Single sub-phase (unlike Candidatures' four and Profile's two): the page is small (3 sections, 164 lines of templates total, 6 routes including the read route), has no nested CRUD and no async state machine, so it fits Stats' economical single-phase model rather than Profile's split model — but unlike Stats, this page has real mutations, not just reads.

## Context

Today `GET /settings` (`dashboard/app.py`) renders `dashboard/templates/settings.html`: three sections — search preferences (keywords/portal queries/location/contract/experience-max-years/salary range/target companies/follow-up days, one flat form), ATS targets (a simple name+URL list with add/delete, no edit), and a Hugging Face API token (masked input, save/delete, with a numbered how-to-get-a-token guide). Backed by `user_data.get_settings()`/`save_settings()`, `get_ats_targets()`/`add_ats_target()`/`delete_ats_target()`, `get_hf_token()`/`save_hf_token()`/`delete_hf_token()` — all already DB-backed, no new backend logic needed beyond the JSON-speaking layer.

`POST /settings/hf-token` (`dashboard/app.py:144-175`) calls `llm.validate_hf_token()` before saving, which makes a live network round-trip to Hugging Face's inference API (`OpenAI(...).chat.completions.create(...)`, a blocking synchronous call) directly inside the `async def` route handler, with no `asyncio.to_thread` wrapping — this blocks the whole FastAPI event loop for the duration of that HTTP call, the same class of bug `dashboard/prepare_state.py` fixed for the LLM/PDF pipeline during Candidatures sub-phase D. This migration fixes it the same way for the new route, since it's directly in scope (the route being migrated) — not a speculative unrelated refactor.

`dashboard/templates/settings.html` has two anchor IDs (`id="search"`, `id="hf-token"`) that `frontend/components/onboarding-banner.tsx` (built during Profile sub-phase A, already shipped) links to (`/settings#search`, `/settings#hf-token`) when those onboarding steps are incomplete. The new page must keep both IDs on the corresponding sections so those already-live links keep working.

## Backend

Six routes in `dashboard/api.py`, all gated by `get_current_user_api` only — **no** onboarding-completion gate. This mirrors Profile's exact rationale: `user_data.get_onboarding_state()` computes `search_complete` from `settings["keywords"]` and `hf_token_complete` from `get_hf_token()` — both are themselves Settings data, so Settings cannot require onboarding to already be complete without becoming impossible to complete.

- `GET /api/settings` → `{"settings": {...9 fields...}, "ats_targets": [{id, name, careers_url}, ...], "hf_token_set": bool, "onboarding": {...}}` — same 4-way payload shape as the current Jinja2 route's template context, aggregated from `get_settings()`/`get_ats_targets()`/`get_hf_token() is not None`/`get_onboarding_state()`.
- `PUT /api/settings/search` (body: the 9 settings fields as a JSON object — `keywords`/`portal_queries`/`target_companies` as string arrays already split, not newline-joined text, since the frontend uses `<textarea>` + manual `.split("\n")` the same way the old form's raw multiline text did, but the wire format is a proper array) → `user_data.save_settings()`, returns `{"ok": true}`.
- `POST /api/settings/ats` (body: `{name, careers_url}`) → `user_data.add_ats_target()`, returns `{"ats_targets": [...]}` (the refreshed full list, matching the old Jinja2 partial's re-render-the-list behavior — simpler for the frontend than a bespoke single-row response plus a manual list-merge).
- `DELETE /api/settings/ats/{target_id}` → `user_data.delete_ats_target()`, returns `{"ats_targets": [...]}` (same refreshed-list shape). No 404 check beyond what `delete_ats_target()` already does (`DELETE ... WHERE id = %s AND user_id = %s`, silent no-op on a missing/foreign id — same behavior as today's Jinja2 route).
- `POST /api/settings/hf-token` (body: `{"hf_token": str}`) → if the trimmed token is empty, calls `delete_hf_token()` and returns `{"hf_token_set": false}` (matching the old route's "empty submission clears the token" behavior); otherwise calls `llm.validate_hf_token()` **wrapped in `asyncio.to_thread(...)`** (the bug fix described above) — on `LLMError`, returns 422 with `{"detail": {"error": "invalid_hf_token", "message": str(exc)}}` (the exact French message `validate_hf_token` already raises, one of three specific messages depending on failure mode); on success, calls `save_hf_token()` and returns `{"hf_token_set": true}`.
- `DELETE /api/settings/hf-token` → `user_data.delete_hf_token()`, returns `{"hf_token_set": false}`.

## Frontend

- **`frontend/app/settings/page.tsx`**: async Server Component, same SSR auth-check pattern as every other protected page (`getSessionUser()` from the existing shared `frontend/lib/session.ts`). Renders `DashboardNav` (`activePath="/settings"`) + `SettingsClient`.
- **`frontend/components/settings/settings-client.tsx`**: client component, `useQuery(['settings'], ...)` fetching `/api/settings`, renders `OnboardingBanner` (existing, unmodified, imported from `frontend/components/onboarding-banner.tsx`) at the top, then the three sections. The page's search section wrapper carries `id="search"` and the HF-token section wrapper carries `id="hf-token"`, preserving the anchors `OnboardingBanner`'s links already target.
- **`frontend/components/settings/search-settings-section.tsx`**: self-contained (own `isEditing` + `useMutation`, matching the established `ScanButton`/`PreparePanel`/Profile-section pattern), a single form with all 9 fields, submitting the whole object to `PUT /api/settings/search` and invalidating `["settings"]` on success.
- **`frontend/components/settings/ats-targets-section.tsx`**: self-contained, a table of existing targets each with a delete button (native `window.confirm`, matching the old `hx-confirm` behavior — no dialog library needed for a single yes/no) firing `DELETE /api/settings/ats/{id}`, plus an always-visible add form (name + URL, both required) firing `POST /api/settings/ats` — no separate edit/read toggle needed here since the old UI never had one either (add-only, delete-only, no in-place edit).
- **`frontend/components/settings/hf-token-section.tsx`**: self-contained, shows "Configuré ✓" or the not-configured message plus the same numbered how-to-get-a-token guide (static copy, ported verbatim), a masked `<input type="password">` + save button firing `POST /api/settings/hf-token` (displaying the 422 error message inline on failure, matching the old `hf_token_error` flash), and a delete button (confirm dialog) shown only when a token is currently set, firing `DELETE /api/settings/hf-token`.

No new npm dependencies.

**Bundled minor fix**: the `POST /api/settings/hf-token` backend route wraps `llm.validate_hf_token()` in `asyncio.to_thread(...)` — see Context section for the bug this closes.

## Out of scope

- No new dependency management UI beyond what exists (no bulk-import, no ATS target editing — matches current Jinja2 behavior exactly, add/delete only).
- Any reconciliation of `dashboard/user_data.py`'s Settings functions with unrelated modules — none needed here, unlike Profile's `profile_parser`/`user_data` duplication.
