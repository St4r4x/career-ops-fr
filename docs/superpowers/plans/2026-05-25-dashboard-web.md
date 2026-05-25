# Dashboard Web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Go/Bubble Tea TUI with a FastAPI + htmx + Tailwind web dashboard at `localhost:8000`.

**Architecture:** FastAPI serves the app. Jinja2 templates render HTML. htmx handles partial swaps (list filtering, detail panel, status updates) without writing JavaScript. SQLite DB at `dashboard/data/applications.db` accessed via a thin Python `db.py` layer.

**Tech Stack:** FastAPI, uvicorn, Jinja2, htmx (CDN), TailwindCSS (CDN), sqlite3 (stdlib), pytest

---

## File Structure

```
dashboard/
  app.py                          # FastAPI app + all routes (CREATE)
  db.py                           # SQLite access layer (CREATE)
  templates/
    base.html                     # Shared layout: Tailwind + htmx CDN (CREATE)
    index.html                    # Root page: filter bar + panels (CREATE)
    partials/
      offer_list.html             # Fragment: list of offer rows (CREATE)
      offer_detail.html           # Fragment: right-panel detail (CREATE)
      offer_form.html             # Fragment: edit form (CREATE)
      offer_empty.html            # Fragment: empty right panel (CREATE)
  data/
    applications.db               # Existing — keep untouched

tests/
  test_dashboard_db.py            # Tests for db.py (CREATE)
  test_dashboard_app.py           # Tests for FastAPI routes (CREATE)

requirements.txt                  # Add: fastapi, uvicorn[standard] (MODIFY)

# Go files to DELETE:
# dashboard/main.go
# dashboard/go.mod
# dashboard/go.sum
# dashboard/db/        (directory)
# dashboard/model/     (directory)
# dashboard/ui/        (directory)
# dashboard/dashboard  (compiled binary)
```

---

## Constants (used throughout)

```python
VALID_STATUSES = [
    "À envoyer", "Envoyée", "Relance",
    "Entretien RH", "Entretien tech",
    "Offre", "Acceptée", "Refusée", "Abandonnée",
]

STATUS_COLORS = {
    "À envoyer":     "bg-gray-700 text-gray-200",
    "Envoyée":       "bg-blue-700 text-white",
    "Relance":       "bg-amber-600 text-white",
    "Entretien RH":  "bg-violet-700 text-white",
    "Entretien tech":"bg-violet-900 text-white",
    "Offre":         "bg-emerald-700 text-white",
    "Acceptée":      "bg-emerald-700 text-white",
    "Refusée":       "bg-red-700 text-white",
    "Abandonnée":    "bg-red-900 text-white",
}

GRADE_COLORS = {
    "A": "bg-green-600 text-white",
    "B": "bg-green-700 text-white",
    "C": "bg-yellow-600 text-white",
    "D": "bg-orange-600 text-white",
    "F": "bg-red-700 text-white",
}

FOLLOW_UP_DAYS = 7
DB_PATH = Path(__file__).parent / "data" / "applications.db"
```

---

## Task 1: db.py — SQLite access layer

**Files:**
- Create: `dashboard/db.py`
- Create: `tests/test_dashboard_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dashboard_db.py
import sqlite3
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
from db import DB, VALID_STATUSES

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL, role TEXT NOT NULL,
    offer_url TEXT NOT NULL DEFAULT '',
    detection_date TEXT NOT NULL,
    score_grade TEXT NOT NULL DEFAULT '',
    score_value REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'À envoyer',
    send_date TEXT, contacts TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '', cv_path TEXT NOT NULL DEFAULT '',
    cover_letter_path TEXT NOT NULL DEFAULT '', follow_up_date TEXT
)"""

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_SQL)
    conn.commit()
    return DB(conn)

def _insert(db, company="Acme", role="AI Engineer", status="À envoyer",
            score_grade="B", score_value=4.0, offer_url="https://x.com/1",
            detection_date="2026-05-25", send_date=None):
    db.conn.execute(
        "INSERT INTO applications (company, role, offer_url, detection_date, "
        "score_grade, score_value, status, send_date) VALUES (?,?,?,?,?,?,?,?)",
        (company, role, offer_url, detection_date, score_grade, score_value, status, send_date)
    )
    db.conn.commit()
    return db.conn.execute("SELECT last_insert_rowid()").fetchone()[0]


class TestGetAll:
    def test_returns_empty_list_when_no_rows(self, db):
        assert db.get_all({}) == []

    def test_returns_all_rows(self, db):
        _insert(db, company="Acme")
        _insert(db, company="Beta")
        rows = db.get_all({})
        assert len(rows) == 2

    def test_filters_by_status(self, db):
        _insert(db, company="Acme", status="À envoyer")
        _insert(db, company="Beta", status="Envoyée")
        rows = db.get_all({"status": "Envoyée"})
        assert len(rows) == 1
        assert rows[0]["company"] == "Beta"

    def test_filters_by_grade(self, db):
        _insert(db, company="Acme", score_grade="A")
        _insert(db, company="Beta", score_grade="F")
        rows = db.get_all({"grade": "A"})
        assert len(rows) == 1
        assert rows[0]["company"] == "Acme"

    def test_filters_by_search_company(self, db):
        _insert(db, company="Mistral AI")
        _insert(db, company="Doctrine")
        rows = db.get_all({"q": "mistral"})
        assert len(rows) == 1
        assert rows[0]["company"] == "Mistral AI"

    def test_filters_by_search_role(self, db):
        _insert(db, company="Acme", role="ML Engineer")
        _insert(db, company="Beta", role="Data Scientist")
        rows = db.get_all({"q": "data"})
        assert len(rows) == 1
        assert rows[0]["role"] == "Data Scientist"

    def test_ordered_by_detection_date_desc(self, db):
        _insert(db, company="Old", detection_date="2026-05-01")
        _insert(db, company="New", detection_date="2026-05-25")
        rows = db.get_all({})
        assert rows[0]["company"] == "New"


class TestGetById:
    def test_returns_row(self, db):
        rid = _insert(db, company="Acme")
        row = db.get_by_id(rid)
        assert row is not None
        assert row["company"] == "Acme"

    def test_returns_none_for_missing_id(self, db):
        assert db.get_by_id(999) is None


class TestUpdate:
    def test_updates_fields(self, db):
        rid = _insert(db, company="Acme", role="AI Engineer")
        db.update(rid, {"notes": "Great company", "status": "Envoyée"})
        row = db.get_by_id(rid)
        assert row["notes"] == "Great company"
        assert row["status"] == "Envoyée"

    def test_returns_updated_row(self, db):
        rid = _insert(db, company="Acme")
        result = db.update(rid, {"notes": "Updated"})
        assert result["notes"] == "Updated"


class TestDelete:
    def test_removes_row(self, db):
        rid = _insert(db)
        db.delete(rid)
        assert db.get_by_id(rid) is None

    def test_no_error_on_missing_id(self, db):
        db.delete(999)  # should not raise


class TestUpdateStatus:
    def test_sets_status(self, db):
        rid = _insert(db, status="À envoyer")
        result = db.update_status(rid, "Envoyée")
        assert result["status"] == "Envoyée"


class TestGetStats:
    def test_total_count(self, db):
        _insert(db)
        _insert(db)
        stats = db.get_stats()
        assert stats["total"] == 2

    def test_stale_count(self, db):
        from datetime import date, timedelta
        old_date = (date.today() - timedelta(days=8)).isoformat()
        _insert(db, status="Envoyée", send_date=old_date)
        _insert(db, status="Envoyée", send_date=date.today().isoformat())
        stats = db.get_stats()
        assert stats["stale_count"] == 1

    def test_by_status_counts(self, db):
        _insert(db, status="À envoyer")
        _insert(db, status="Envoyée")
        stats = db.get_stats()
        assert stats["by_status"]["À envoyer"] == 1
        assert stats["by_status"]["Envoyée"] == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_db.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Install FastAPI and uvicorn**

```bash
.venv/bin/pip install fastapi "uvicorn[standard]"
```

Then add to `requirements.txt`:
```
fastapi==0.115.12
uvicorn[standard]==0.34.2
```

- [ ] **Step 4: Create `dashboard/db.py`**

```python
# dashboard/db.py
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

VALID_STATUSES = [
    "À envoyer", "Envoyée", "Relance",
    "Entretien RH", "Entretien tech",
    "Offre", "Acceptée", "Refusée", "Abandonnée",
]

_RESPONSE_STATUSES = {"Entretien RH", "Entretien tech", "Offre", "Acceptée", "Refusée"}
_INTERVIEW_STATUSES = {"Entretien RH", "Entretien tech", "Offre", "Acceptée"}
_FOLLOW_UP_DAYS = 7

_SELECT = """
SELECT id, company, role, offer_url, detection_date, score_grade, score_value,
       status, send_date, contacts, notes, cv_path, cover_letter_path, follow_up_date
FROM applications
"""


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


class DB:
    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        self.conn = conn

    def get_all(self, filters: dict) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if status := filters.get("status"):
            clauses.append("status = ?")
            params.append(status)
        if grade := filters.get("grade"):
            clauses.append("score_grade = ?")
            params.append(grade)
        if q := filters.get("q"):
            clauses.append("(LOWER(company) LIKE ? OR LOWER(role) LIKE ?)")
            like = f"%{q.lower()}%"
            params.extend([like, like])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"{_SELECT} {where} ORDER BY detection_date DESC"
        rows = self.conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_id(self, id: int) -> dict | None:
        row = self.conn.execute(_SELECT + "WHERE id = ?", (id,)).fetchone()
        return _row_to_dict(row) if row else None

    def update(self, id: int, fields: dict) -> dict:
        allowed = {
            "company", "role", "offer_url", "detection_date", "score_grade",
            "score_value", "status", "send_date", "contacts", "notes",
            "cv_path", "cover_letter_path", "follow_up_date",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_by_id(id)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        self.conn.execute(
            f"UPDATE applications SET {set_clause} WHERE id = ?",
            [*updates.values(), id],
        )
        self.conn.commit()
        return self.get_by_id(id)

    def delete(self, id: int) -> None:
        self.conn.execute("DELETE FROM applications WHERE id = ?", (id,))
        self.conn.commit()

    def update_status(self, id: int, status: str) -> dict:
        return self.update(id, {"status": status})

    def get_stats(self) -> dict:
        rows = self.get_all({})
        by_status = {s: 0 for s in VALID_STATUSES}
        sent = response = interviews = stale = 0
        today = date.today()
        for r in rows:
            s = r["status"]
            by_status[s] = by_status.get(s, 0) + 1
            if s != "À envoyer":
                sent += 1
            if s in _RESPONSE_STATUSES:
                response += 1
            if s in _INTERVIEW_STATUSES:
                interviews += 1
            if s == "Envoyée" and r.get("send_date"):
                try:
                    send_dt = date.fromisoformat(r["send_date"])
                    if (today - send_dt).days > _FOLLOW_UP_DAYS:
                        stale += 1
                except ValueError:
                    pass
        response_rate = (response / sent * 100) if sent else 0.0
        return {
            "total": len(rows),
            "response_rate": round(response_rate, 1),
            "interview_count": interviews,
            "stale_count": stale,
            "by_status": by_status,
        }


def open_db(path: Path) -> DB:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return DB(conn)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_db.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/db.py tests/test_dashboard_db.py requirements.txt
git commit -m "feat: add dashboard db.py SQLite access layer with tests"
```

---

## Task 2: FastAPI app skeleton + base template

**Files:**
- Create: `dashboard/app.py`
- Create: `dashboard/templates/base.html`
- Create: `dashboard/templates/index.html`
- Create: `dashboard/templates/partials/offer_empty.html`
- Create: `tests/test_dashboard_app.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_dashboard_app.py
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL, role TEXT NOT NULL,
    offer_url TEXT NOT NULL DEFAULT '',
    detection_date TEXT NOT NULL,
    score_grade TEXT NOT NULL DEFAULT '',
    score_value REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'À envoyer',
    send_date TEXT, contacts TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '', cv_path TEXT NOT NULL DEFAULT '',
    cover_letter_path TEXT NOT NULL DEFAULT '', follow_up_date TEXT
)"""

@pytest.fixture
def client():
    from db import DB
    import app as dashboard_app
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_SQL)
    conn.commit()
    test_db = DB(conn)
    dashboard_app.app.state.db = test_db
    return TestClient(dashboard_app.app)

@pytest.fixture
def client_with_data(client):
    from db import DB
    import app as dashboard_app
    db = dashboard_app.app.state.db
    db.conn.execute(
        "INSERT INTO applications (company, role, offer_url, detection_date, "
        "score_grade, score_value, status) VALUES (?,?,?,?,?,?,?)",
        ("Mistral AI", "ML Engineer", "https://jobs.lever.co/mistral/1",
         "2026-05-25", "B", 4.0, "À envoyer")
    )
    db.conn.execute(
        "INSERT INTO applications (company, role, offer_url, detection_date, "
        "score_grade, score_value, status) VALUES (?,?,?,?,?,?,?)",
        ("Doctrine", "ML Engineer", "https://jobs.lever.co/doctrine/1",
         "2026-05-24", "A", 4.5, "Envoyée")
    )
    db.conn.commit()
    return client


class TestRoot:
    def test_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_contains_app_title(self, client):
        r = client.get("/")
        assert "career-ops-fr" in r.text.lower()


class TestOfferList:
    def test_returns_200(self, client_with_data):
        r = client_with_data.get("/offers")
        assert r.status_code == 200

    def test_shows_company_names(self, client_with_data):
        r = client_with_data.get("/offers")
        assert "Mistral AI" in r.text
        assert "Doctrine" in r.text

    def test_filters_by_status(self, client_with_data):
        r = client_with_data.get("/offers?status=Envoyée")
        assert "Doctrine" in r.text
        assert "Mistral AI" not in r.text

    def test_filters_by_grade(self, client_with_data):
        r = client_with_data.get("/offers?grade=A")
        assert "Doctrine" in r.text
        assert "Mistral AI" not in r.text

    def test_filters_by_search(self, client_with_data):
        r = client_with_data.get("/offers?q=mistral")
        assert "Mistral AI" in r.text
        assert "Doctrine" not in r.text
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Create `dashboard/templates/base.html`**

```html
<!-- dashboard/templates/base.html -->
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>career-ops-fr</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <style>
    body { background: #0f172a; color: #e2e8f0; }
    .scrollable { overflow-y: auto; }
  </style>
</head>
<body class="h-screen flex flex-col">
  <nav class="bg-slate-800 px-4 py-3 flex items-center gap-6 border-b border-slate-700 shrink-0">
    <span class="font-bold text-violet-400 text-lg">career-ops-fr</span>
    <a href="/" class="text-slate-300 hover:text-white text-sm">Pipeline</a>
    <a href="/stats" class="text-slate-300 hover:text-white text-sm">Stats</a>
  </nav>
  <main class="flex-1 overflow-hidden">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

- [ ] **Step 4: Create `dashboard/templates/partials/offer_empty.html`**

```html
<!-- dashboard/templates/partials/offer_empty.html -->
<div class="flex items-center justify-center h-full text-slate-500 text-sm">
  Sélectionne une offre pour voir le détail
</div>
```

- [ ] **Step 5: Create `dashboard/templates/index.html`**

```html
<!-- dashboard/templates/index.html -->
{% extends "base.html" %}
{% block content %}
<div class="flex h-full gap-0">

  <!-- Left panel: filters + list -->
  <div class="w-96 shrink-0 flex flex-col border-r border-slate-700 bg-slate-900">
    <!-- Filter bar -->
    <div class="p-3 border-b border-slate-700 flex flex-col gap-2">
      <input
        class="w-full bg-slate-800 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-violet-500"
        type="text" name="q" placeholder="Rechercher entreprise ou rôle..."
        hx-get="/offers" hx-trigger="keyup changed delay:300ms"
        hx-target="#offer-list" hx-include="[name='status'],[name='grade']"
        id="search-input">
      <div class="flex gap-2">
        <select name="status" id="status-filter"
          class="flex-1 bg-slate-800 text-slate-200 text-sm rounded px-2 py-2 border border-slate-600 focus:outline-none focus:border-violet-500"
          hx-get="/offers" hx-trigger="change"
          hx-target="#offer-list" hx-include="[name='q'],[name='grade']">
          <option value="">Tous statuts</option>
          {% for s in statuses %}
          <option value="{{ s }}">{{ s }}</option>
          {% endfor %}
        </select>
        <select name="grade" id="grade-filter"
          class="flex-1 bg-slate-800 text-slate-200 text-sm rounded px-2 py-2 border border-slate-600 focus:outline-none focus:border-violet-500"
          hx-get="/offers" hx-trigger="change"
          hx-target="#offer-list" hx-include="[name='q'],[name='status']">
          <option value="">Tous grades</option>
          {% for g in ["A","B","C","D","F"] %}
          <option value="{{ g }}">{{ g }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
    <!-- Offer list -->
    <div id="offer-list" class="flex-1 scrollable">
      {% include "partials/offer_list.html" %}
    </div>
  </div>

  <!-- Right panel: detail -->
  <div id="offer-detail" class="flex-1 scrollable p-6">
    {% include "partials/offer_empty.html" %}
  </div>

</div>
{% endblock %}
```

- [ ] **Step 6: Create `dashboard/app.py` (skeleton — routes GET / and GET /offers only)**

```python
# dashboard/app.py
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db import DB, VALID_STATUSES, open_db

DB_PATH = Path(__file__).parent / "data" / "applications.db"
TEMPLATES_DIR = Path(__file__).parent / "templates"

app = FastAPI()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STATUS_COLORS: dict[str, str] = {
    "À envoyer":     "bg-gray-700 text-gray-200",
    "Envoyée":       "bg-blue-700 text-white",
    "Relance":       "bg-amber-600 text-white",
    "Entretien RH":  "bg-violet-700 text-white",
    "Entretien tech":"bg-violet-900 text-white",
    "Offre":         "bg-emerald-700 text-white",
    "Acceptée":      "bg-emerald-700 text-white",
    "Refusée":       "bg-red-700 text-white",
    "Abandonnée":    "bg-red-900 text-white",
}

GRADE_COLORS: dict[str, str] = {
    "A": "bg-green-600 text-white",
    "B": "bg-green-700 text-white",
    "C": "bg-yellow-600 text-white",
    "D": "bg-orange-600 text-white",
    "F": "bg-red-700 text-white",
}


def _get_db(request: Request) -> DB:
    db = getattr(request.app.state, "db", None)
    if db is None:
        request.app.state.db = open_db(DB_PATH)
        db = request.app.state.db
    return db


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    db = _get_db(request)
    offers = db.get_all({})
    return templates.TemplateResponse("index.html", {
        "request": request,
        "offers": offers,
        "statuses": VALID_STATUSES,
        "status_colors": STATUS_COLORS,
        "grade_colors": GRADE_COLORS,
    })


@app.get("/offers", response_class=HTMLResponse)
async def offer_list(
    request: Request,
    status: str = Query(""),
    grade: str = Query(""),
    q: str = Query(""),
):
    db = _get_db(request)
    filters = {k: v for k, v in {"status": status, "grade": grade, "q": q}.items() if v}
    offers = db.get_all(filters)
    return templates.TemplateResponse("partials/offer_list.html", {
        "request": request,
        "offers": offers,
        "status_colors": STATUS_COLORS,
        "grade_colors": GRADE_COLORS,
    })
```

- [ ] **Step 7: Create `dashboard/templates/partials/offer_list.html`** (minimal — just show rows)

```html
<!-- dashboard/templates/partials/offer_list.html -->
{% if not offers %}
<div class="p-4 text-slate-500 text-sm">Aucune offre trouvée.</div>
{% endif %}
{% for offer in offers %}
<div
  class="px-3 py-2 border-b border-slate-800 cursor-pointer hover:bg-slate-800 flex items-center gap-2"
  hx-get="/offers/{{ offer.id }}"
  hx-target="#offer-detail"
  hx-swap="innerHTML">
  <span class="text-xs px-2 py-0.5 rounded font-medium shrink-0
    {{ status_colors.get(offer.status, 'bg-gray-700 text-gray-200') }}">
    {{ offer.status }}
  </span>
  <span class="text-xs px-1.5 py-0.5 rounded font-bold shrink-0
    {{ grade_colors.get(offer.score_grade, 'bg-gray-700 text-gray-200') }}">
    {{ offer.score_grade }}
  </span>
  <div class="min-w-0">
    <div class="text-sm text-slate-200 truncate">{{ offer.company }}</div>
    <div class="text-xs text-slate-400 truncate">{{ offer.role }}</div>
  </div>
</div>
{% endfor %}
```

- [ ] **Step 8: Run tests to confirm they pass**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py -v
```

Expected: all tests pass.

- [ ] **Step 9: Smoke test in browser**

```bash
cd dashboard && PYTHONPATH=. ../.venv/bin/uvicorn app:app --reload --port 8000
```

Open `http://localhost:8000` — should show the filter bar on the left and offer rows with coloured badges.

- [ ] **Step 10: Commit**

```bash
git add dashboard/app.py dashboard/templates/ tests/test_dashboard_app.py
git commit -m "feat: add FastAPI dashboard skeleton with filter list"
```

---

## Task 3: Offer detail panel

**Files:**
- Create: `dashboard/templates/partials/offer_detail.html`
- Modify: `dashboard/app.py` — add `GET /offers/{id}`
- Modify: `tests/test_dashboard_app.py` — add `TestOfferDetail`

- [ ] **Step 1: Add failing tests**

Add to `tests/test_dashboard_app.py`:

```python
class TestOfferDetail:
    def test_returns_200_for_existing(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.get(f"/offers/{row['id']}")
        assert r.status_code == 200

    def test_shows_company_and_role(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.get(f"/offers/{row['id']}")
        assert row["company"] in r.text
        assert row["role"] in r.text

    def test_returns_404_for_missing(self, client):
        r = client.get("/offers/999")
        assert r.status_code == 404

    def test_shows_offer_url_as_link(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.get(f"/offers/{row['id']}")
        assert row["offer_url"] in r.text
```

- [ ] **Step 2: Run to confirm they fail**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py::TestOfferDetail -v 2>&1 | head -10
```

Expected: FAIL (route not found)

- [ ] **Step 3: Add route to `dashboard/app.py`**

Add after the existing routes:

```python
from fastapi import HTTPException

@app.get("/offers/{offer_id}", response_class=HTMLResponse)
async def offer_detail(request: Request, offer_id: int):
    db = _get_db(request)
    offer = db.get_by_id(offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return templates.TemplateResponse("partials/offer_detail.html", {
        "request": request,
        "offer": offer,
        "statuses": VALID_STATUSES,
        "status_colors": STATUS_COLORS,
        "grade_colors": GRADE_COLORS,
    })
```

- [ ] **Step 4: Create `dashboard/templates/partials/offer_detail.html`**

```html
<!-- dashboard/templates/partials/offer_detail.html -->
<div class="max-w-2xl">
  <!-- Header -->
  <div class="flex items-start justify-between mb-4">
    <div>
      <h2 class="text-xl font-bold text-white">{{ offer.company }}</h2>
      <p class="text-slate-400">{{ offer.role }}</p>
    </div>
    <div class="flex gap-2 items-center">
      <span class="text-sm px-3 py-1 rounded font-bold
        {{ grade_colors.get(offer.score_grade, 'bg-gray-700 text-gray-200') }}">
        {{ offer.score_grade }} {{ "%.1f"|format(offer.score_value) }}
      </span>
      <span class="text-sm px-3 py-1 rounded font-medium
        {{ status_colors.get(offer.status, 'bg-gray-700 text-gray-200') }}">
        {{ offer.status }}
      </span>
    </div>
  </div>

  <!-- Fields -->
  <dl class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm mb-6">
    <dt class="text-slate-400">Détecté le</dt>
    <dd class="text-slate-200">{{ offer.detection_date }}</dd>
    {% if offer.send_date %}
    <dt class="text-slate-400">Envoyé le</dt>
    <dd class="text-slate-200">{{ offer.send_date }}</dd>
    {% endif %}
    {% if offer.follow_up_date %}
    <dt class="text-slate-400">Relance</dt>
    <dd class="text-slate-200">{{ offer.follow_up_date }}</dd>
    {% endif %}
    {% if offer.offer_url %}
    <dt class="text-slate-400">URL</dt>
    <dd><a href="{{ offer.offer_url }}" target="_blank"
          class="text-violet-400 hover:text-violet-300 underline break-all text-xs">
      {{ offer.offer_url }}</a></dd>
    {% endif %}
    {% if offer.cv_path %}
    <dt class="text-slate-400">CV</dt>
    <dd class="text-slate-200 text-xs break-all">{{ offer.cv_path }}</dd>
    {% endif %}
    {% if offer.cover_letter_path %}
    <dt class="text-slate-400">LM</dt>
    <dd class="text-slate-200 text-xs break-all">{{ offer.cover_letter_path }}</dd>
    {% endif %}
    {% if offer.contacts %}
    <dt class="text-slate-400">Contacts</dt>
    <dd class="text-slate-200">{{ offer.contacts }}</dd>
    {% endif %}
  </dl>

  {% if offer.notes %}
  <div class="mb-6">
    <p class="text-slate-400 text-sm mb-1">Notes</p>
    <p class="text-slate-200 text-sm whitespace-pre-wrap bg-slate-800 rounded p-3">{{ offer.notes }}</p>
  </div>
  {% endif %}

  <!-- Status quick-change -->
  <div class="mb-4">
    <p class="text-slate-400 text-sm mb-2">Changer le statut</p>
    <div class="flex flex-wrap gap-2">
      {% for s in statuses %}
      <button
        class="text-xs px-2 py-1 rounded font-medium border
          {% if s == offer.status %}border-violet-500 {{ status_colors.get(s, '') }}{% else %}border-slate-600 text-slate-400 hover:border-slate-400{% endif %}"
        hx-post="/offers/{{ offer.id }}/status"
        hx-vals='{"status": "{{ s }}"}'
        hx-target="#offer-detail"
        hx-swap="innerHTML"
        hx-include="[name='q'],[name='status'],[name='grade']">
        {{ s }}
      </button>
      {% endfor %}
    </div>
  </div>

  <!-- Action buttons -->
  <div class="flex gap-3">
    <button
      class="text-sm px-4 py-2 rounded bg-slate-700 hover:bg-slate-600 text-white"
      hx-get="/offers/{{ offer.id }}/edit"
      hx-target="#offer-detail"
      hx-swap="innerHTML">
      ✏️ Modifier
    </button>
    <button
      class="text-sm px-4 py-2 rounded bg-red-800 hover:bg-red-700 text-white"
      hx-delete="/offers/{{ offer.id }}"
      hx-target="#offer-detail"
      hx-swap="innerHTML"
      hx-confirm="Supprimer cette candidature ?">
      🗑 Supprimer
    </button>
  </div>
</div>
```

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py dashboard/templates/partials/offer_detail.html tests/test_dashboard_app.py
git commit -m "feat: add offer detail panel with status quick-change"
```

---

## Task 4: Edit form + save + delete routes

**Files:**
- Create: `dashboard/templates/partials/offer_form.html`
- Modify: `dashboard/app.py` — add `GET /offers/{id}/edit`, `POST /offers/{id}`, `DELETE /offers/{id}`, `POST /offers/{id}/status`
- Modify: `tests/test_dashboard_app.py` — add `TestOfferEdit`, `TestOfferDelete`, `TestOfferStatus`

- [ ] **Step 1: Add failing tests**

Add to `tests/test_dashboard_app.py`:

```python
class TestOfferEdit:
    def test_edit_returns_form(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.get(f"/offers/{row['id']}/edit")
        assert r.status_code == 200
        assert "form" in r.text.lower() or "input" in r.text.lower()

    def test_save_updates_notes(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.post(f"/offers/{row['id']}", data={
            "company": row["company"], "role": row["role"],
            "detection_date": row["detection_date"], "score_grade": row["score_grade"],
            "score_value": str(row["score_value"]), "status": row["status"],
            "notes": "Test note", "offer_url": row["offer_url"] or "",
            "send_date": "", "follow_up_date": "", "contacts": "",
            "cv_path": "", "cover_letter_path": "",
        })
        assert r.status_code == 200
        updated = db.get_by_id(row["id"])
        assert updated["notes"] == "Test note"


class TestOfferDelete:
    def test_delete_removes_row(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        rid = row["id"]
        r = client_with_data.delete(f"/offers/{rid}")
        assert r.status_code == 200
        assert db.get_by_id(rid) is None


class TestOfferStatus:
    def test_status_change_returns_updated_detail(self, client_with_data):
        import app as dashboard_app
        db = dashboard_app.app.state.db
        row = db.get_all({})[0]
        r = client_with_data.post(f"/offers/{row['id']}/status", data={"status": "Envoyée"})
        assert r.status_code == 200
        updated = db.get_by_id(row["id"])
        assert updated["status"] == "Envoyée"
```

- [ ] **Step 2: Run to confirm they fail**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py::TestOfferEdit tests/test_dashboard_app.py::TestOfferDelete tests/test_dashboard_app.py::TestOfferStatus -v 2>&1 | head -15
```

Expected: FAIL (routes not found)

- [ ] **Step 3: Create `dashboard/templates/partials/offer_form.html`**

```html
<!-- dashboard/templates/partials/offer_form.html -->
<form hx-post="/offers/{{ offer.id }}"
      hx-target="#offer-detail"
      hx-swap="innerHTML"
      class="max-w-2xl flex flex-col gap-3">

  <h2 class="text-lg font-bold text-white mb-2">Modifier — {{ offer.company }}</h2>

  {% set fields = [
    ("company", "Entreprise", offer.company, "text"),
    ("role", "Rôle", offer.role, "text"),
    ("offer_url", "URL offre", offer.offer_url, "text"),
    ("detection_date", "Date détection (YYYY-MM-DD)", offer.detection_date, "text"),
    ("score_grade", "Grade (A/B/C/D/F)", offer.score_grade, "text"),
    ("score_value", "Score (0.0–5.0)", offer.score_value, "text"),
    ("send_date", "Date envoi (YYYY-MM-DD)", offer.send_date or "", "text"),
    ("follow_up_date", "Date relance (YYYY-MM-DD)", offer.follow_up_date or "", "text"),
    ("contacts", "Contacts", offer.contacts, "text"),
    ("cv_path", "Chemin CV", offer.cv_path, "text"),
    ("cover_letter_path", "Chemin LM", offer.cover_letter_path, "text"),
  ] %}

  {% for name, label, value, type in fields %}
  <div>
    <label class="text-slate-400 text-xs block mb-1">{{ label }}</label>
    <input type="{{ type }}" name="{{ name }}" value="{{ value }}"
      class="w-full bg-slate-800 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-violet-500">
  </div>
  {% endfor %}

  <div>
    <label class="text-slate-400 text-xs block mb-1">Statut</label>
    <select name="status"
      class="w-full bg-slate-800 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-violet-500">
      {% for s in statuses %}
      <option value="{{ s }}" {% if s == offer.status %}selected{% endif %}>{{ s }}</option>
      {% endfor %}
    </select>
  </div>

  <div>
    <label class="text-slate-400 text-xs block mb-1">Notes</label>
    <textarea name="notes" rows="4"
      class="w-full bg-slate-800 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-violet-500">{{ offer.notes }}</textarea>
  </div>

  <div class="flex gap-3 mt-2">
    <button type="submit"
      class="text-sm px-4 py-2 rounded bg-violet-700 hover:bg-violet-600 text-white font-medium">
      Sauvegarder
    </button>
    <button type="button"
      class="text-sm px-4 py-2 rounded bg-slate-700 hover:bg-slate-600 text-white"
      hx-get="/offers/{{ offer.id }}"
      hx-target="#offer-detail"
      hx-swap="innerHTML">
      Annuler
    </button>
  </div>
</form>
```

- [ ] **Step 4: Add routes to `dashboard/app.py`**

Add after existing routes:

```python
from fastapi import Form
from typing import Optional

@app.get("/offers/{offer_id}/edit", response_class=HTMLResponse)
async def offer_edit_form(request: Request, offer_id: int):
    db = _get_db(request)
    offer = db.get_by_id(offer_id)
    if offer is None:
        raise HTTPException(status_code=404, detail="Offer not found")
    return templates.TemplateResponse("partials/offer_form.html", {
        "request": request,
        "offer": offer,
        "statuses": VALID_STATUSES,
    })


@app.post("/offers/{offer_id}", response_class=HTMLResponse)
async def offer_save(
    request: Request, offer_id: int,
    company: str = Form(""), role: str = Form(""),
    offer_url: str = Form(""), detection_date: str = Form(""),
    score_grade: str = Form(""), score_value: str = Form("0"),
    status: str = Form("À envoyer"), send_date: str = Form(""),
    follow_up_date: str = Form(""), contacts: str = Form(""),
    notes: str = Form(""), cv_path: str = Form(""),
    cover_letter_path: str = Form(""),
):
    db = _get_db(request)
    fields = {
        "company": company, "role": role, "offer_url": offer_url,
        "detection_date": detection_date, "score_grade": score_grade,
        "score_value": float(score_value) if score_value else 0.0,
        "status": status,
        "send_date": send_date or None,
        "follow_up_date": follow_up_date or None,
        "contacts": contacts, "notes": notes,
        "cv_path": cv_path, "cover_letter_path": cover_letter_path,
    }
    offer = db.update(offer_id, fields)
    return templates.TemplateResponse("partials/offer_detail.html", {
        "request": request,
        "offer": offer,
        "statuses": VALID_STATUSES,
        "status_colors": STATUS_COLORS,
        "grade_colors": GRADE_COLORS,
    })


@app.delete("/offers/{offer_id}", response_class=HTMLResponse)
async def offer_delete(request: Request, offer_id: int):
    db = _get_db(request)
    db.delete(offer_id)
    return templates.TemplateResponse("partials/offer_empty.html", {
        "request": request,
    })


@app.post("/offers/{offer_id}/status", response_class=HTMLResponse)
async def offer_status(request: Request, offer_id: int, status: str = Form(...)):
    db = _get_db(request)
    offer = db.update_status(offer_id, status)
    return templates.TemplateResponse("partials/offer_detail.html", {
        "request": request,
        "offer": offer,
        "statuses": VALID_STATUSES,
        "status_colors": STATUS_COLORS,
        "grade_colors": GRADE_COLORS,
    })
```

- [ ] **Step 5: Run all tests**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py tests/test_dashboard_db.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py dashboard/templates/partials/offer_form.html tests/test_dashboard_app.py
git commit -m "feat: add edit form, save, delete, status-change routes"
```

---

## Task 5: Stats page

**Files:**
- Create: `dashboard/templates/stats.html`
- Modify: `dashboard/app.py` — add `GET /stats`
- Modify: `tests/test_dashboard_app.py` — add `TestStats`

- [ ] **Step 1: Add failing tests**

Add to `tests/test_dashboard_app.py`:

```python
class TestStats:
    def test_stats_returns_200(self, client_with_data):
        r = client_with_data.get("/stats")
        assert r.status_code == 200

    def test_stats_shows_total(self, client_with_data):
        r = client_with_data.get("/stats")
        assert "2" in r.text  # 2 offers inserted in fixture
```

- [ ] **Step 2: Run to confirm they fail**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py::TestStats -v 2>&1 | head -10
```

Expected: FAIL

- [ ] **Step 3: Create `dashboard/templates/stats.html`**

```html
<!-- dashboard/templates/stats.html -->
{% extends "base.html" %}
{% block content %}
<div class="p-8 max-w-2xl mx-auto">
  <h1 class="text-2xl font-bold text-white mb-8">Statistiques</h1>

  <div class="grid grid-cols-2 gap-4 mb-8">
    <div class="bg-slate-800 rounded-lg p-4">
      <p class="text-slate-400 text-sm">Total candidatures</p>
      <p class="text-3xl font-bold text-white">{{ stats.total }}</p>
    </div>
    <div class="bg-slate-800 rounded-lg p-4">
      <p class="text-slate-400 text-sm">Taux de réponse</p>
      <p class="text-3xl font-bold text-white">{{ stats.response_rate }}%</p>
    </div>
    <div class="bg-slate-800 rounded-lg p-4">
      <p class="text-slate-400 text-sm">Entretiens obtenus</p>
      <p class="text-3xl font-bold text-white">{{ stats.interview_count }}</p>
    </div>
    <div class="bg-slate-800 rounded-lg p-4 {% if stats.stale_count > 0 %}border border-amber-500{% endif %}">
      <p class="text-slate-400 text-sm">Relances en retard (+7j)</p>
      <p class="text-3xl font-bold {% if stats.stale_count > 0 %}text-amber-400{% else %}text-white{% endif %}">
        {{ stats.stale_count }}
      </p>
    </div>
  </div>

  <h2 class="text-lg font-semibold text-white mb-4">Par statut</h2>
  <div class="flex flex-col gap-2">
    {% for s in statuses %}
    {% set count = stats.by_status.get(s, 0) %}
    <div class="flex items-center gap-3">
      <span class="w-36 text-xs px-2 py-1 rounded font-medium text-center
        {{ status_colors.get(s, 'bg-gray-700 text-gray-200') }}">{{ s }}</span>
      <div class="flex-1 bg-slate-800 rounded-full h-2">
        {% if stats.total > 0 %}
        <div class="bg-violet-500 h-2 rounded-full"
          style="width: {{ [count / stats.total * 100, 100]|min|int }}%"></div>
        {% endif %}
      </div>
      <span class="text-slate-300 text-sm w-6 text-right">{{ count }}</span>
    </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Add route to `dashboard/app.py`**

```python
@app.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    db = _get_db(request)
    stats = db.get_stats()
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "stats": stats,
        "statuses": VALID_STATUSES,
        "status_colors": STATUS_COLORS,
    })
```

- [ ] **Step 5: Run all tests**

```bash
PYTHONPATH=dashboard .venv/bin/pytest tests/test_dashboard_app.py tests/test_dashboard_db.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py dashboard/templates/stats.html tests/test_dashboard_app.py
git commit -m "feat: add stats page with response rate and by-status breakdown"
```

---

## Task 6: Remove Go TUI + update gitignore + README

**Files:**
- Delete: `dashboard/main.go`, `dashboard/go.mod`, `dashboard/go.sum`
- Delete: `dashboard/db/` (directory with `db.go`, `db_test.go`)
- Delete: `dashboard/model/` (directory with `application.go`, `application_test.go`)
- Delete: `dashboard/ui/` (directory with all `.go` files)
- Delete: `dashboard/dashboard` (compiled binary — already in `.gitignore`)
- Modify: `.gitignore` — add `.superpowers/`
- Modify: `README.md` — update launch instructions

- [ ] **Step 1: Remove Go files**

```bash
gio trash /home/missia03/Projects/career-ops-fr/dashboard/main.go
gio trash /home/missia03/Projects/career-ops-fr/dashboard/go.mod
gio trash /home/missia03/Projects/career-ops-fr/dashboard/go.sum
gio trash /home/missia03/Projects/career-ops-fr/dashboard/db
gio trash /home/missia03/Projects/career-ops-fr/dashboard/model
gio trash /home/missia03/Projects/career-ops-fr/dashboard/ui
gio trash /home/missia03/Projects/career-ops-fr/dashboard/dashboard
```

- [ ] **Step 2: Update `.gitignore`**

Add `.superpowers/` to `.gitignore`:

```
.superpowers/
```

- [ ] **Step 3: Update `README.md` launch section**

Find the dashboard launch instructions in `README.md` and replace with:

```markdown
### Dashboard

```bash
cd dashboard
PYTHONPATH=. uvicorn app:app --reload --port 8000
```

Open http://localhost:8000
```

- [ ] **Step 4: Run full test suite to confirm nothing broken**

```bash
PYTHONPATH=. .venv/bin/pytest tests/ -v --ignore=tests/test_generate_pdf.py --ignore=tests/test_generate_cover_letter.py
```

Expected: all tests pass (PDF tests require WeasyPrint rendering, skip if slow).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove Go TUI, add web dashboard launch instructions"
```

---

## Self-Review

**Spec coverage:**
- ✅ Layout C (split panel) — Tasks 2, 3
- ✅ FastAPI + Jinja2 + htmx + Tailwind — Tasks 2–5
- ✅ Filter bar (status, grade, search) — Task 2
- ✅ Status colour badges — Tasks 2, 3
- ✅ Grade colour badges — Tasks 2, 3
- ✅ All 7 routes — Tasks 2, 3, 4, 5
- ✅ db.py with all 5 functions — Task 1
- ✅ Stats page — Task 5
- ✅ Go TUI removal — Task 6
- ✅ `fastapi`, `uvicorn` added to requirements — Task 1

**Type consistency:** `db.get_all()`, `db.get_by_id()`, `db.update()`, `db.delete()`, `db.update_status()`, `db.get_stats()` used consistently across all tasks.

**No placeholders found.**
