# Dashboard Web — Design Spec

> Replaces the Go/Bubble Tea TUI with a FastAPI web dashboard accessible at `localhost:8000`.

**Goal:** Single-page web dashboard to browse, filter, and manage job applications with a split-panel layout and colour-coded statuses.

**Architecture:** FastAPI (Python) + Jinja2 templates + htmx for partial updates + TailwindCSS via CDN. SQLite database already at `dashboard/data/applications.db`.

**Tech Stack:** FastAPI, Jinja2, htmx, TailwindCSS (CDN), sqlite3 (stdlib), uvicorn

---

## 1. Layout

Split-panel (layout C):

- **Left panel** — scrollable offer list with filter bar (status dropdown, grade dropdown, free-text search). Each row shows: coloured status badge + company + role + grade badge.
- **Right panel** — offer detail loaded via htmx on row click. Shows all fields, action buttons, and inline edit form.

No page navigation — everything happens on a single page via htmx partial swaps.

---

## 2. File Structure

The existing `dashboard/` directory is repurposed. Go files are removed.

```
dashboard/
  app.py                       # FastAPI app, all routes
  db.py                        # SQLite access layer (port of db/db.go logic)
  templates/
    base.html                  # Shared layout: Tailwind CDN, htmx CDN, nav bar
    index.html                 # Root page: filter bar + left list + right panel
    partials/
      offer_list.html          # Fragment: list of offer rows (htmx swap target)
      offer_detail.html        # Fragment: right-panel detail view
      offer_form.html          # Fragment: inline edit form
      offer_empty.html         # Fragment: empty right panel (nothing selected)
```

`requirements.txt` gains: `fastapi`, `uvicorn[standard]`.

---

## 3. Routes

| Method | Path | htmx target | Description |
|--------|------|-------------|-------------|
| GET | `/` | — | Renders `index.html` with initial list |
| GET | `/offers` | `#offer-list` | Filtered list fragment (params: `status`, `grade`, `q`) |
| GET | `/offers/{id}` | `#offer-detail` | Detail fragment for one offer |
| GET | `/offers/{id}/edit` | `#offer-detail` | Edit form fragment |
| POST | `/offers/{id}` | `#offer-detail` | Save edit → returns updated detail fragment |
| DELETE | `/offers/{id}` | `#offer-detail` | Delete → returns empty detail fragment; triggers list refresh |
| POST | `/offers/{id}/status` | `#offer-list` + `#offer-detail` | Quick status change → refreshes both panels |

---

## 4. Status Colour Coding

Badges (filled, Tailwind classes):

| Status | Background | Text |
|--------|-----------|------|
| À envoyer | `bg-gray-700` | `text-gray-200` |
| Envoyée | `bg-blue-700` | `text-white` |
| Relance | `bg-amber-600` | `text-white` |
| Entretien RH | `bg-violet-700` | `text-white` |
| Entretien tech | `bg-violet-900` | `text-white` |
| Offre | `bg-emerald-700` | `text-white` |
| Acceptée | `bg-emerald-700` | `text-white` |
| Refusée | `bg-red-700` | `text-white` |
| Abandonnée | `bg-red-900` | `text-white` |

Grade badges (A/B = green, C = yellow, D/F = red).

---

## 5. Offer Detail Panel

Fields displayed:
- Company, Role, Offer URL (clickable link)
- Detection date, Score grade + value, Status
- Send date, Follow-up date
- CV path, Cover letter path
- Notes (multiline)

Action buttons:
- **Changer statut** — dropdown with all valid statuses → POST `/offers/{id}/status`
- **Modifier** — loads edit form inline → GET `/offers/{id}/edit`
- **Supprimer** — DELETE `/offers/{id}` with confirm dialog

---

## 6. Filter Bar

Three controls, all trigger `GET /offers` via htmx on change:
- **Statut** — `<select>` with all valid statuses + "Tous"
- **Grade** — `<select>` with A/B/C/D/F + "Tous"
- **Recherche** — text input, matches company or role (case-insensitive, debounced 300ms via htmx)

---

## 7. db.py

Thin wrapper around `sqlite3`. Functions:

```python
def get_all(filters: dict) -> list[dict]       # filtered list query
def get_by_id(id: int) -> dict | None
def update(id: int, fields: dict) -> dict      # returns updated row
def delete(id: int) -> None
def update_status(id: int, status: str) -> dict
```

No ORM. Rows returned as plain dicts (`sqlite3.Row` with `row_factory`).

---

## 8. Launch

```bash
cd dashboard
uvicorn app:app --reload --port 8000
```

Added to project `Makefile` or documented in README as `make dashboard`.

---

## 9. Go TUI Removal

The Go files (`main.go`, `ui/`, `db/`, `model/`, `go.mod`, `go.sum`, `dashboard` binary) are deleted. The `dashboard/data/` directory and SQLite DB are kept.

---

## 10. Out of Scope

- Authentication (local tool, single user)
- "Score offre" / "Générer CV" button execution — buttons are present but open instructions in a new tab or display a copy-paste command; actual LLM invocation stays in Claude Code CLI
- Pagination (filter + scroll sufficient for ~500 offers)
- Dark/light mode toggle
