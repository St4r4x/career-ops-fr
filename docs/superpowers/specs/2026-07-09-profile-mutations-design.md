# Diggo — Profile: mutations (edit contact/résumé/CV) + cutover — Design Spec

Date: 2026-07-09
Status: approved

## Goal

Migrate the write path of the Profile page — editing contact info, the free-text résumé, and the FR/EN CV (summary, experience, skills, certifications, education) — from FastAPI/Jinja2 to Next.js. This is sub-phase B of two (A: read-only — done, B: mutations + cutover — this spec), extending the page that went live at the end of sub-phase A, then flipping nginx and deleting the Jinja2 side. Unlike Candidatures (four sub-phases, because scan/prepare needed their own async-state-machine work), Profile needed only two: every mutation here is synchronous CRUD against Postgres.

## Context

Today, 8 separate Jinja2/HTMX routes in `dashboard/app.py` handle Profile writes: `POST /profile/contact`, `POST /profile/text`, `POST /profile/cv/meta`, `POST /profile/cv/experience`, `DELETE /profile/cv/experience/{exp_id}`, `POST /profile/cv/skills`, `POST /profile/cv/certifications`, `POST /profile/cv/education`. Each renders back the corresponding Jinja2 partial (`profile_contact.html`, `profile_text.html`, `profile_cv_meta.html`, `profile_cv_experience.html`, `profile_cv_skills.html`, `profile_cv_certifications.html`, `profile_cv_education.html`) — all still live today since `/profile` still routes to `api`; sub-phase A only added a parallel, currently-unrouted `/api/profile` read endpoint and Next.js page.

Every backend save function in `dashboard/user_data.py` (`save_experience`, `save_skills`, `save_certifications`, `save_education`) follows the same shape: **delete-then-reinsert the whole list** for a given `user_id`/`lang` (not per-item upsert) — confirmed by reading each function body. `save_cv_meta` is a single-row upsert (`ON CONFLICT ... DO UPDATE`). `delete_experience` is the one genuinely single-item operation (deletes one row + its bullets by id). `profile_parser.save_profile(conn, user_id, data)` takes the **whole** profile dict (`{contact, profile_md}`) and overwrites both fields — the existing Jinja2 contact/text routes both `load_profile()` first, mutate only the field they own, then `save_profile()` the merged whole, to avoid clobbering the field they don't touch. The new JSON routes replicate this same load→mutate→save pattern for contact/text, and the same whole-list-replace semantics for the CV list sections — no rewriting of `user_data.py`/`profile_parser.py`, this migration only adds a JSON-speaking layer in front of functions that already do the right thing.

## Backend

Eight new routes in `dashboard/api.py`, mirroring the 8 Jinja2 routes 1:1 (not consolidated into one flexible endpoint like Candidatures-B's `PATCH /api/offers/{id}` — that consolidation worked because every field lived on one `applications` row; here the backend functions have genuinely different signatures — nested bullets, category+skill pairs, no-`lang` certifications — so mirroring that structure is more honest than a generic string-keyed dispatcher):

- `PATCH /api/profile/contact` — body: contact dict (`name`/`title`/`email`/`phone`/`location`/`linkedin`/`github`). Loads the current profile via `profile_parser.load_profile()`, overwrites `contact`, saves via `profile_parser.save_profile()` — same pattern as today's `profile_save_contact`.
- `PATCH /api/profile/text` — body: `{"profile_md": str}`. Same load→mutate→save pattern for the résumé field.
- `PUT /api/profile/cv/meta?lang=fr` — body: `{"summary": str}` → `user_data.save_cv_meta(conn, user_id, lang, summary)`.
- `PUT /api/profile/cv/experience?lang=fr` — body: list of `{title, company, type, period, sort_order, bullets: [str, ...]}` → `user_data.save_experience()` (full delete-then-reinsert, including nested bullets).
- `DELETE /api/profile/cv/experience/{exp_id}` → `user_data.delete_experience(conn, user_id, exp_id)`. No 404 check needed beyond what the function already does (it deletes by `id AND user_id`, so a foreign/missing id is a silent no-op — same behavior as today's Jinja2 route, not a regression to fix here).
- `PUT /api/profile/cv/skills?lang=fr` — body: list of `{category, skill, sort_order}` → `user_data.save_skills()`.
- `PUT /api/profile/cv/certifications` — body: list of `{name, issuer, year}`, **no** `lang` query param (certifications aren't language-split in the schema) → `user_data.save_certifications()`.
- `PUT /api/profile/cv/education?lang=fr` — body: list of `{degree, school, year}` → `user_data.save_education()`.

All eight gated by `get_current_user_api` only (same as sub-phase A's read route — no onboarding gate; a user actively editing their profile is, by definition, not yet fully onboarded). `lang` query params default to `"fr"` and reject anything outside `("fr", "en")` by falling back to `"fr"`, matching the existing Jinja2 routes' exact validation (`if lang not in ("fr", "en"): lang = "fr"`).

Every route returns `{"ok": true}` — no route hand-rolls a partial response shape. The frontend invalidates the single `["profile"]` TanStack Query key after any successful mutation and refetches via the already-existing `GET /api/profile`, which is simpler than 8 different response contracts and matches sub-phase A's single-query architecture (the whole page already re-renders from one query).

**Deleted this sub-phase** (once nginx stops routing `/profile` to `api`): `dashboard/app.py`'s `profile_page()` and all 8 mutation routes; `dashboard/templates/profile.html` and its live partials (`profile_contact.html`, `profile_text.html`, `profile_cv_meta.html`, `profile_cv_experience.html`, `profile_cv_skills.html`, `profile_cv_certifications.html`, `profile_cv_education.html`); the 4 already-confirmed-orphaned partials from sub-phase A's spec (`profile_education.html`, `profile_experience.html`, `profile_projects.html`, `profile_skills.html`).

Test file `tests/test_profile_routes.py`: the entire file is deleted at cutover — `TestProfilePage`, `TestSaveContact`, `TestSaveText`, `TestCvRoutes` all test Jinja2 routes this sub-phase deletes. New tests for the 8 JSON routes go in `tests/test_api_routes.py`, reusing the `client_with_profile`-style fixture pattern sub-phase A already established there (monkeypatched `profile_parser`/`user_data` functions + `MagicMock` DB connection, not a real Postgres CV-table fixture).

## Frontend

All extending `frontend/components/profile/profile-client.tsx` (sub-phase A) — no new page, no nginx change until cutover. Each save fires its own `useMutation` (matching each backend route), all invalidating the same `["profile"]` query key on success. A brief "✓ Sauvegardé" indicator renders from the mutation's own `isSuccess` flag (matching the old Jinja2 partials' flash message) — no new toast/notification library.

- **Contact card**: becomes an editable form (7 inputs) toggled via a "Modifier"/"Annuler" pair, matching the read/edit toggle pattern `offer-edit-form.tsx` established in Candidatures-B. Submitting fires `PATCH /api/profile/contact`.
- **Résumé card**: a `<textarea>` bound to `profile_md`, with a "Sauvegarder" button (not autosave-on-blur — this field can be long free text, an explicit save avoids surprising partial saves mid-edit) firing `PATCH /api/profile/text`.
- **CV card, per FR/EN tab**: summary becomes a `<textarea>` + save button (`PUT /api/profile/cv/meta`). Experience/skills/certifications/education each get an editable-list UI: existing rows render as inputs (experience additionally gets a per-bullet text-list with add/remove-bullet buttons), a "+ Ajouter" row appends a blank entry to local state, a "🗑" per row removes it locally, and one "Sauvegarder" button per section submits the *entire current local list* to that section's `PUT` route — matching the backend's whole-list-replace semantics (no per-row optimistic save, since the backend doesn't support per-row upsert). Experience additionally gets a lighter-weight "🗑" that calls `DELETE /api/profile/cv/experience/{id}` directly for already-saved rows (matching today's Jinja2 behavior, where delete is instant/no-confirm — small, low-consequence action on your own data, no `window.confirm` needed, same triviality bar as Candidatures' notes-field edits).
- Certifications' editable list has **no** FR/EN toggle — its save button always calls the language-less `PUT /api/profile/cv/certifications` regardless of which CV tab is currently selected, matching the backend's schema (certifications aren't `lang`-scoped).

**Bundled from sub-phase A's deferred Minor findings** (its final review explicitly recommended folding these in here rather than churning the read-only diff): add `aria-pressed={lang === "fr"}` / `aria-pressed={lang === "en"}` to the FR/EN toggle buttons; render `contact.linkedin`/`contact.github` as real `<a href>` anchors instead of bare text with a literal `"in "` prefix.

## Out of scope (this sub-phase)

- `/settings` — a separate future phase entirely, unrelated to Profile (though it will reuse `onboarding-banner.tsx`, built in sub-phase A).
- Any reconciliation between `profile_parser.load_profile()`/`save_profile()` and `user_data.py`'s separately-existing, unrelated `get_profile()`/`save_profile()` (same `user_profiles` table, two different call paths) — pre-existing duplication, not something this migration created or is in scope to fix.
- Per-item upsert for CV list sections (experience/skills/certifications/education) — the backend only supports whole-list replace; changing that would mean rewriting `user_data.py`'s save functions, out of scope for a frontend migration.
