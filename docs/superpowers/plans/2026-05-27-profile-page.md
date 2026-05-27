# Profile Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/profile` page to the dashboard that reads `config/profile.md` + `config/contact.yaml`, displays all sections in collapsible accordions, and lets the user edit + save each section individually via HTMX POST.

**Architecture:** New `dashboard/profile_parser.py` module owns all parsing/serialization. `dashboard/app.py` gets one GET route and six POST routes. Templates follow the exact same Jinja2 + Tailwind + HTMX patterns as the existing dashboard. Complex sections (experience, skills, education, projects) use `hx-vals="js:..."` to serialize card data to JSON before POSTing.

**Tech Stack:** FastAPI, Jinja2, HTMX 1.9.12, Tailwind CDN, PyYAML (already in requirements), pytest + TestClient.

---

## File map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `dashboard/profile_parser.py` | Parse profile.md + contact.yaml → dict; serialize dict → files |
| Modify | `dashboard/app.py` | Add GET `/profile` + 6 POST routes |
| Modify | `dashboard/templates/base.html` | Add "Profil" nav link |
| Create | `dashboard/templates/profile.html` | Full page with accordion skeleton |
| Create | `dashboard/templates/partials/profile_contact.html` | Contact form partial |
| Create | `dashboard/templates/partials/profile_summary.html` | Summary textarea partial |
| Create | `dashboard/templates/partials/profile_experience.html` | Experience cards partial |
| Create | `dashboard/templates/partials/profile_skills.html` | Skills by category partial |
| Create | `dashboard/templates/partials/profile_education.html` | Education + certifications partial |
| Create | `dashboard/templates/partials/profile_projects.html` | Projects cards partial |
| Create | `tests/test_profile_parser.py` | Unit tests for parser/serializer |
| Create | `tests/test_profile_routes.py` | Route integration tests |

---

### Task 1: profile_parser.py — load and save

**Files:**
- Create: `dashboard/profile_parser.py`
- Create: `tests/test_profile_parser.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_profile_parser.py
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))
import profile_parser as parser_mod

SAMPLE_CONTACT_YAML = textwrap.dedent("""\
    name: Test User
    title: AI Engineer
    email: test@example.com
    phone: "+33 6 00 00 00 00"
    location: Paris
    linkedin: ""
    github: github.com/testuser
""")

SAMPLE_PROFILE_MD = textwrap.dedent("""\
    # Profile — Test User

    ## Contact
    - Email: test@example.com
    - Phone: +33 6 00 00 00 00
    - Location: Paris
    - LinkedIn: 
    - GitHub: github.com/testuser

    ## Summary
    An experienced engineer with production ML background.

    ## Experience

    ### ML Engineer — Acme Corp (CDI, January 2024 – Present)
    - Built real-time inference pipeline
    - Deployed model to edge device

    ## Education
    - **Master of Science** — Great School (2022–2024)

    ## Certifications & Training
    - AWS Certified ML Specialty

    ## Skills

    ### Machine Learning
    - PyTorch
    - Scikit-learn

    ### MLOps
    - Docker
    - GitHub Actions

    ## Personal Projects

    - **cool-project**: A very cool project with many features
""")


@pytest.fixture
def tmp_config(tmp_path: Path, monkeypatch):
    contact_file = tmp_path / "contact.yaml"
    profile_file = tmp_path / "profile.md"
    contact_file.write_text(SAMPLE_CONTACT_YAML, encoding="utf-8")
    profile_file.write_text(SAMPLE_PROFILE_MD, encoding="utf-8")
    monkeypatch.setattr(parser_mod, "_CONTACT_YAML", contact_file)
    monkeypatch.setattr(parser_mod, "_PROFILE_MD", profile_file)
    return tmp_path


def test_load_contact_from_yaml(tmp_config):
    data = parser_mod.load_profile()
    assert data["contact"]["name"] == "Test User"
    assert data["contact"]["email"] == "test@example.com"
    assert data["contact"]["github"] == "github.com/testuser"


def test_load_summary(tmp_config):
    data = parser_mod.load_profile()
    assert "experienced engineer" in data["summary"]


def test_load_experience_entries(tmp_config):
    data = parser_mod.load_profile()
    assert len(data["experience"]) == 1
    exp = data["experience"][0]
    assert exp["title"] == "ML Engineer"
    assert exp["company"] == "Acme Corp"
    assert exp["type"] == "CDI"
    assert exp["period"] == "January 2024 – Present"
    assert len(exp["bullets"]) == 2


def test_load_skills_categories(tmp_config):
    data = parser_mod.load_profile()
    assert "Machine Learning" in data["skills"]
    assert "PyTorch" in data["skills"]["Machine Learning"]
    assert "MLOps" in data["skills"]
    assert "Docker" in data["skills"]["MLOps"]


def test_load_education_and_certs(tmp_config):
    data = parser_mod.load_profile()
    assert len(data["education"]) == 1
    assert data["education"][0]["degree"] == "Master of Science"
    assert data["education"][0]["school"] == "Great School"
    assert "AWS Certified ML Specialty" in data["certifications"]


def test_load_projects(tmp_config):
    data = parser_mod.load_profile()
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "cool-project"
    assert "very cool" in data["projects"][0]["description"]


def test_roundtrip(tmp_config):
    original = parser_mod.load_profile()
    parser_mod.save_profile(original)
    reloaded = parser_mod.load_profile()
    assert reloaded["contact"] == original["contact"]
    assert reloaded["summary"] == original["summary"]
    assert len(reloaded["experience"]) == len(original["experience"])
    assert reloaded["skills"] == original["skills"]
    assert reloaded["education"] == original["education"]
    assert reloaded["certifications"] == original["certifications"]
    assert reloaded["projects"] == original["projects"]


def test_missing_files_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(parser_mod, "_CONTACT_YAML", tmp_path / "contact.yaml")
    monkeypatch.setattr(parser_mod, "_PROFILE_MD", tmp_path / "profile.md")
    data = parser_mod.load_profile()
    assert data["contact"]["name"] == ""
    assert data["summary"] == ""
    assert data["experience"] == []
    assert data["skills"] == {}
```

- [ ] **Step 2: Run tests — confirm they all fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_parser.py -v
```
Expected: `ModuleNotFoundError: No module named 'profile_parser'`

- [ ] **Step 3: Create `dashboard/profile_parser.py`**

```python
# dashboard/profile_parser.py
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_PROFILE_MD = Path(__file__).parent.parent / "config" / "profile.md"
_CONTACT_YAML = Path(__file__).parent.parent / "config" / "contact.yaml"


def _parse_contact(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"name": "", "title": "", "email": "", "phone": "",
                "location": "", "linkedin": "", "github": ""}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {k: str(data.get(k, "") or "") for k in
            ("name", "title", "email", "phone", "location", "linkedin", "github")}


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines).strip()
            current = line[3:].strip()
            lines = []
        elif not line.startswith("# "):
            if current is not None:
                lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines).strip()
    return sections


def _parse_experience(text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    heading_re = re.compile(r"^### (.+?) — (.+?) \((.+?), (.+)\)$")
    for line in text.splitlines():
        m = heading_re.match(line)
        if m:
            if current is not None:
                entries.append(current)
            current = {
                "title": m.group(1).strip(),
                "company": m.group(2).strip(),
                "type": m.group(3).strip(),
                "period": m.group(4).strip(),
                "bullets": [],
            }
        elif line.startswith("- ") and current is not None:
            current["bullets"].append(line[2:].strip())
    if current is not None:
        entries.append(current)
    return entries


def _parse_skills(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = line[4:].strip()
            result[current] = []
        elif line.startswith("- ") and current is not None:
            result[current].append(line[2:].strip())
    return result


def _parse_education(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    edu_re = re.compile(r"^- \*\*(.+?)\*\* — (.+?) \((.+?)\)$")
    for line in text.splitlines():
        m = edu_re.match(line)
        if m:
            entries.append({
                "degree": m.group(1).strip(),
                "school": m.group(2).strip(),
                "period": m.group(3).strip(),
            })
    return entries


def _parse_projects(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    proj_re = re.compile(r"^- \*\*(.+?)\*\*: (.+)$")
    for line in text.splitlines():
        m = proj_re.match(line)
        if m:
            entries.append({
                "name": m.group(1).strip(),
                "description": m.group(2).strip(),
            })
    return entries


def _parse_profile_md(path: Path) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "summary": "", "experience": [], "skills": {},
        "education": [], "certifications": [], "projects": [],
    }
    if not path.exists():
        return empty
    with path.open(encoding="utf-8") as f:
        text = f.read()
    sections = _split_sections(text)
    return {
        "summary": sections.get("Summary", "").strip(),
        "experience": _parse_experience(sections.get("Experience", "")),
        "skills": _parse_skills(sections.get("Skills", "")),
        "education": _parse_education(sections.get("Education", "")),
        "certifications": [
            line[2:].strip()
            for line in sections.get("Certifications & Training", "").splitlines()
            if line.startswith("- ")
        ],
        "projects": _parse_projects(sections.get("Personal Projects", "")),
    }


def load_profile() -> dict[str, Any]:
    contact = _parse_contact(_CONTACT_YAML)
    md_data = _parse_profile_md(_PROFILE_MD)
    return {"contact": contact, **md_data}


def _serialize_profile_md(data: dict[str, Any]) -> str:
    c = data.get("contact", {})
    lines: list[str] = [
        f"# Profile — {c.get('name', '')}",
        "",
        "## Contact",
        f"- Email: {c.get('email', '')}",
        f"- Phone: {c.get('phone', '')}",
        f"- Location: {c.get('location', '')}",
        f"- LinkedIn: {c.get('linkedin', '')}",
        f"- GitHub: {c.get('github', '')}",
        "",
        "## Summary",
        data.get("summary", ""),
        "",
        "## Experience",
        "",
    ]
    for exp in data.get("experience", []):
        lines.append(
            f"### {exp['title']} — {exp['company']} ({exp['type']}, {exp['period']})"
        )
        for b in exp.get("bullets", []):
            lines.append(f"- {b}")
        lines.append("")

    lines += ["## Education"]
    for edu in data.get("education", []):
        lines.append(f"- **{edu['degree']}** — {edu['school']} ({edu['period']})")
    lines.append("")

    lines += ["## Certifications & Training"]
    for cert in data.get("certifications", []):
        lines.append(f"- {cert}")
    lines.append("")

    lines += ["## Skills", ""]
    for category, skills in data.get("skills", {}).items():
        lines.append(f"### {category}")
        for skill in skills:
            lines.append(f"- {skill}")
        lines.append("")

    lines += ["## Personal Projects", ""]
    for proj in data.get("projects", []):
        lines.append(f"- **{proj['name']}**: {proj['description']}")
    lines.append("")

    return "\n".join(lines)


def save_profile(data: dict[str, Any]) -> None:
    c = data.get("contact", {})
    contact_data = {k: c.get(k, "") for k in
                    ("name", "title", "email", "phone", "location", "linkedin", "github")}
    _CONTACT_YAML.parent.mkdir(parents=True, exist_ok=True)
    with _CONTACT_YAML.open("w", encoding="utf-8") as f:
        yaml.dump(contact_data, f, allow_unicode=True, default_flow_style=False)
    md_content = _serialize_profile_md(data)
    _PROFILE_MD.parent.mkdir(parents=True, exist_ok=True)
    with _PROFILE_MD.open("w", encoding="utf-8") as f:
        f.write(md_content)
```

- [ ] **Step 4: Run tests — confirm they all pass**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_parser.py -v
```
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add dashboard/profile_parser.py tests/test_profile_parser.py
git commit -m "feat: add profile_parser — load/save profile.md and contact.yaml"
```

---

### Task 2: Nav link + GET /profile + page skeleton

**Files:**
- Modify: `dashboard/templates/base.html`
- Modify: `dashboard/app.py`
- Create: `dashboard/templates/profile.html`

- [ ] **Step 1: Write failing test**

```python
# tests/test_profile_routes.py
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

SAMPLE_CONTACT_YAML = textwrap.dedent("""\
    name: Test User
    title: AI Engineer
    email: test@example.com
    phone: "+33 6 00 00 00 00"
    location: Paris
    linkedin: ""
    github: github.com/testuser
""")

SAMPLE_PROFILE_MD = textwrap.dedent("""\
    # Profile — Test User

    ## Contact
    - Email: test@example.com

    ## Summary
    An experienced engineer.

    ## Experience

    ### ML Engineer — Acme Corp (CDI, January 2024 – Present)
    - Built a pipeline

    ## Education
    - **MSc AI** — Great School (2022–2024)

    ## Certifications & Training
    - AWS ML

    ## Skills

    ### Machine Learning
    - PyTorch

    ## Personal Projects

    - **cool-project**: A cool project
""")


@pytest.fixture
def profile_client(tmp_path, monkeypatch):
    import profile_parser as parser_mod
    import sqlite3
    import app as dashboard_app
    from db import DB

    contact_file = tmp_path / "contact.yaml"
    profile_file = tmp_path / "profile.md"
    contact_file.write_text(SAMPLE_CONTACT_YAML, encoding="utf-8")
    profile_file.write_text(SAMPLE_PROFILE_MD, encoding="utf-8")
    monkeypatch.setattr(parser_mod, "_CONTACT_YAML", contact_file)
    monkeypatch.setattr(parser_mod, "_PROFILE_MD", profile_file)

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL,
        role TEXT NOT NULL, offer_url TEXT NOT NULL DEFAULT '',
        detection_date TEXT NOT NULL, score_grade TEXT NOT NULL DEFAULT '',
        score_value REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'À envoyer',
        send_date TEXT, contacts TEXT NOT NULL DEFAULT '',
        notes TEXT NOT NULL DEFAULT '', cv_path TEXT NOT NULL DEFAULT '',
        cover_letter_path TEXT NOT NULL DEFAULT '', follow_up_date TEXT,
        description TEXT NOT NULL DEFAULT '')""")
    conn.commit()
    dashboard_app.app.state.db = DB(conn)
    return TestClient(dashboard_app.app)


class TestProfilePage:
    def test_profile_page_loads(self, profile_client):
        r = profile_client.get("/profile")
        assert r.status_code == 200

    def test_profile_shows_name(self, profile_client):
        r = profile_client.get("/profile")
        assert "Test User" in r.text

    def test_profile_nav_link_present(self, profile_client):
        r = profile_client.get("/profile")
        assert "/profile" in r.text
        assert "Profil" in r.text
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestProfilePage -v
```
Expected: FAIL — route `/profile` not found (404)

- [ ] **Step 3: Add "Profil" nav link to `dashboard/templates/base.html`**

Replace the existing nav block:
```html
  <nav class="bg-slate-800 px-4 py-3 flex items-center gap-6 border-b border-slate-700 shrink-0">
    <span class="font-bold text-violet-400 text-lg">career-ops-fr</span>
    <a href="/" class="text-slate-300 hover:text-white text-sm">Pipeline</a>
    <a href="/stats" class="text-slate-300 hover:text-white text-sm">Stats</a>
    <a href="/profile" class="text-slate-300 hover:text-white text-sm">Profil</a>
  </nav>
```

- [ ] **Step 4: Add GET `/profile` route to `dashboard/app.py`**

Add after the existing imports at the top:
```python
from pathlib import Path
```
(already present — skip if so)

Add after the `stats_page` route at the bottom of `app.py`:

```python
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    import profile_parser
    profile = profile_parser.load_profile()
    profile_exists = (Path(__file__).parent.parent / "config" / "profile.md").exists()
    return templates.TemplateResponse(
        request,
        "profile.html",
        {"profile": profile, "profile_exists": profile_exists},
    )
```

- [ ] **Step 5: Create `dashboard/templates/profile.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="p-6 max-w-3xl mx-auto overflow-y-auto h-full">

  {% if not profile_exists %}
  <div class="bg-amber-900 border border-amber-500 rounded p-3 mb-4 text-amber-200 text-sm">
    Fichier profile.md introuvable — créez <code>config/profile.md</code> à partir de <code>config/profile.md.example</code>
  </div>
  {% endif %}

  <!-- Header -->
  <div id="profile-header" class="flex justify-between items-start mb-6">
    <div>
      <h1 class="text-2xl font-bold text-white">{{ profile.contact.name or "Votre nom" }}</h1>
      <p class="text-slate-400 text-sm">{{ profile.contact.title }}</p>
    </div>
    <div class="text-right text-xs text-slate-400 space-y-1">
      {% if profile.contact.email %}<div>✉ {{ profile.contact.email }}</div>{% endif %}
      {% if profile.contact.github %}<div>⌥ {{ profile.contact.github }}</div>{% endif %}
    </div>
  </div>

  <div class="flex flex-col gap-1">

    <div>
      <button class="acc-btn" onclick="toggleAcc(this)">
        <span>Coordonnées</span><svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-contact" class="acc-body">
        {% include "partials/profile_contact.html" %}
      </div>
    </div>

    <div>
      <button class="acc-btn acc-open" onclick="toggleAcc(this)">
        <span>Résumé</span><svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-summary" class="acc-body acc-open">
        {% include "partials/profile_summary.html" %}
      </div>
    </div>

    <div>
      <button class="acc-btn" onclick="toggleAcc(this)">
        <span>Expériences <span class="text-slate-500 font-normal text-xs">({{ profile.experience | length }} postes)</span></span>
        <svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-experience" class="acc-body">
        {% include "partials/profile_experience.html" %}
      </div>
    </div>

    <div>
      <button class="acc-btn" onclick="toggleAcc(this)">
        <span>Compétences <span class="text-slate-500 font-normal text-xs">({{ profile.skills | length }} catégories)</span></span>
        <svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-skills" class="acc-body">
        {% include "partials/profile_skills.html" %}
      </div>
    </div>

    <div>
      <button class="acc-btn" onclick="toggleAcc(this)">
        <span>Formation &amp; Certifications <span class="text-slate-500 font-normal text-xs">({{ profile.education | length }} diplômes · {{ profile.certifications | length }} certifs)</span></span>
        <svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-education" class="acc-body">
        {% include "partials/profile_education.html" %}
      </div>
    </div>

    <div>
      <button class="acc-btn" onclick="toggleAcc(this)">
        <span>Projets personnels <span class="text-slate-500 font-normal text-xs">({{ profile.projects | length }} projets)</span></span>
        <svg class="chv w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
      </button>
      <div id="section-projects" class="acc-body">
        {% include "partials/profile_projects.html" %}
      </div>
    </div>

  </div>
</div>

<style>
  .acc-btn {
    width:100%; display:flex; justify-content:space-between; align-items:center;
    padding:0.55rem 1rem; background:#1e293b; border:1px solid #334155;
    border-radius:0.5rem; color:#e2e8f0; font-size:0.875rem; font-weight:600;
    cursor:pointer; text-align:left; margin-top:0.25rem;
  }
  .acc-btn:hover { background:#273548; }
  .acc-btn.acc-open { border-bottom-left-radius:0; border-bottom-right-radius:0;
    border-bottom-color:transparent; color:#a78bfa; }
  .acc-body { display:none; border:1px solid #334155; border-top:none;
    border-bottom-left-radius:0.5rem; border-bottom-right-radius:0.5rem;
    padding:1rem; background:#1e293b; }
  .acc-body.acc-open { display:block; }
  .chv { transition:transform 0.2s; }
  .acc-btn.acc-open .chv { transform:rotate(180deg); }
  .pf-input { width:100%; background:#0f172a; border:1px solid #334155; border-radius:0.375rem;
    color:#e2e8f0; padding:0.35rem 0.6rem; font-size:0.8rem; box-sizing:border-box; }
  .pf-input:focus { outline:none; border-color:#7c3aed; }
  .pf-label { display:block; font-size:0.7rem; color:#94a3b8; margin-bottom:0.2rem; }
  .pf-card { background:#0f172a; border:1px solid #334155; border-radius:0.375rem;
    padding:0.75rem; margin-bottom:0.5rem; }
  .pf-save-btn { background:#7c3aed; color:white; border:none; border-radius:0.375rem;
    padding:0.35rem 0.9rem; font-size:0.8rem; cursor:pointer; }
  .pf-save-btn:hover { background:#6d28d9; }
  .pf-add-btn { background:transparent; border:1px dashed #475569; color:#94a3b8;
    border-radius:0.375rem; padding:0.25rem 0.75rem; font-size:0.75rem; cursor:pointer; }
  .pf-add-btn:hover { border-color:#7c3aed; color:#a78bfa; }
  .pf-del-btn { background:transparent; border:none; color:#f87171;
    font-size:0.75rem; cursor:pointer; padding:0; }
  .pf-flash { color:#34d399; font-size:0.75rem; }
</style>
<script>
function toggleAcc(btn) {
  btn.classList.toggle('acc-open');
  btn.nextElementSibling.classList.toggle('acc-open');
}
</script>
{% endblock %}
```

- [ ] **Step 6: Create the six section partials as empty stubs** (needed so `{% include %}` in profile.html doesn't error)

`dashboard/templates/partials/profile_contact.html`:
```html
<p class="text-slate-500 text-sm">Contact — à implémenter</p>
```

`dashboard/templates/partials/profile_summary.html`:
```html
<p class="text-slate-500 text-sm">Résumé — à implémenter</p>
```

`dashboard/templates/partials/profile_experience.html`:
```html
<p class="text-slate-500 text-sm">Expériences — à implémenter</p>
```

`dashboard/templates/partials/profile_skills.html`:
```html
<p class="text-slate-500 text-sm">Compétences — à implémenter</p>
```

`dashboard/templates/partials/profile_education.html`:
```html
<p class="text-slate-500 text-sm">Formation — à implémenter</p>
```

`dashboard/templates/partials/profile_projects.html`:
```html
<p class="text-slate-500 text-sm">Projets — à implémenter</p>
```

- [ ] **Step 7: Run tests — confirm they pass**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestProfilePage -v
```
Expected: 3 passed

- [ ] **Step 8: Commit**

```bash
git add dashboard/app.py dashboard/templates/base.html dashboard/templates/profile.html \
  dashboard/templates/partials/profile_contact.html \
  dashboard/templates/partials/profile_summary.html \
  dashboard/templates/partials/profile_experience.html \
  dashboard/templates/partials/profile_skills.html \
  dashboard/templates/partials/profile_education.html \
  dashboard/templates/partials/profile_projects.html \
  tests/test_profile_routes.py
git commit -m "feat: add /profile route and page skeleton with accordion layout"
```

---

### Task 3: Contact and Summary sections

**Files:**
- Modify: `dashboard/templates/partials/profile_contact.html`
- Modify: `dashboard/templates/partials/profile_summary.html`
- Modify: `dashboard/app.py`
- Modify: `tests/test_profile_routes.py`

- [ ] **Step 1: Add failing tests to `tests/test_profile_routes.py`**

Append to the file:

```python
class TestSaveContact:
    def test_save_contact_returns_200(self, profile_client):
        r = profile_client.post("/profile/contact", data={
            "name": "New Name", "title": "ML Eng", "email": "new@test.com",
            "phone": "+33 6 11 11 11 11", "location": "Lyon",
            "linkedin": "", "github": "github.com/new",
        })
        assert r.status_code == 200

    def test_save_contact_persists_to_yaml(self, profile_client, tmp_path, monkeypatch):
        import profile_parser as parser_mod
        contact_file = tmp_path / "contact.yaml"
        profile_file = tmp_path / "profile.md"
        contact_file.write_text(SAMPLE_CONTACT_YAML, encoding="utf-8")
        profile_file.write_text(SAMPLE_PROFILE_MD, encoding="utf-8")
        monkeypatch.setattr(parser_mod, "_CONTACT_YAML", contact_file)
        monkeypatch.setattr(parser_mod, "_PROFILE_MD", profile_file)
        profile_client.post("/profile/contact", data={
            "name": "Updated", "title": "Eng", "email": "u@test.com",
            "phone": "", "location": "", "linkedin": "", "github": "",
        })
        import yaml
        saved = yaml.safe_load(contact_file.read_text())
        assert saved["name"] == "Updated"

    def test_save_contact_response_contains_saved_flash(self, profile_client):
        r = profile_client.post("/profile/contact", data={
            "name": "N", "title": "T", "email": "e@e.com",
            "phone": "", "location": "", "linkedin": "", "github": "",
        })
        assert "Sauvegardé" in r.text


class TestSaveSummary:
    def test_save_summary_returns_200(self, profile_client):
        r = profile_client.post("/profile/summary",
                                data={"summary": "New summary text."})
        assert r.status_code == 200

    def test_save_summary_response_contains_flash(self, profile_client):
        r = profile_client.post("/profile/summary",
                                data={"summary": "New summary text."})
        assert "Sauvegardé" in r.text
```

- [ ] **Step 2: Run new tests — confirm they fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestSaveContact tests/test_profile_routes.py::TestSaveSummary -v
```
Expected: FAIL — routes not found (404)

- [ ] **Step 3: Add POST routes to `dashboard/app.py`**

Append after the `profile_page` route:

```python
@app.post("/profile/contact", response_class=HTMLResponse)
async def profile_save_contact(
    request: Request,
    name: str = Form(""),
    title: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    linkedin: str = Form(""),
    github: str = Form(""),
):
    import profile_parser
    data = profile_parser.load_profile()
    data["contact"] = {
        "name": name, "title": title, "email": email,
        "phone": phone, "location": location,
        "linkedin": linkedin, "github": github,
    }
    profile_parser.save_profile(data)
    return templates.TemplateResponse(
        request,
        "partials/profile_contact.html",
        {"profile": data, "saved": True},
    )


@app.post("/profile/summary", response_class=HTMLResponse)
async def profile_save_summary(request: Request, summary: str = Form("")):
    import profile_parser
    data = profile_parser.load_profile()
    data["summary"] = summary
    profile_parser.save_profile(data)
    return templates.TemplateResponse(
        request,
        "partials/profile_summary.html",
        {"profile": data, "saved": True},
    )
```

- [ ] **Step 4: Write `dashboard/templates/partials/profile_contact.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<form hx-post="/profile/contact" hx-target="#section-contact" hx-swap="innerHTML">
  <div class="grid grid-cols-2 gap-2 mb-3">
    {% for field, label in [("name","Nom"),("title","Titre"),("email","Email"),
        ("phone","Téléphone"),("location","Localisation"),("linkedin","LinkedIn"),("github","GitHub")] %}
    <div>
      <label class="pf-label">{{ label }}</label>
      <input class="pf-input" name="{{ field }}" value="{{ profile.contact.get(field, '') }}">
    </div>
    {% endfor %}
  </div>
  <div class="flex justify-end">
    <button type="submit" class="pf-save-btn">Sauvegarder</button>
  </div>
</form>
```

- [ ] **Step 5: Write `dashboard/templates/partials/profile_summary.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<form hx-post="/profile/summary" hx-target="#section-summary" hx-swap="innerHTML">
  <textarea class="pf-input mb-2" name="summary" rows="4"
    style="resize:vertical">{{ profile.summary }}</textarea>
  <div class="flex justify-end">
    <button type="submit" class="pf-save-btn">Sauvegarder</button>
  </div>
</form>
```

- [ ] **Step 6: Run tests — confirm they pass**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py -v
```
Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add dashboard/app.py \
  dashboard/templates/partials/profile_contact.html \
  dashboard/templates/partials/profile_summary.html \
  tests/test_profile_routes.py
git commit -m "feat: add contact and summary profile sections with save"
```

---

### Task 4: Experience section

**Files:**
- Modify: `dashboard/templates/partials/profile_experience.html`
- Modify: `dashboard/app.py`
- Modify: `tests/test_profile_routes.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_profile_routes.py`:

```python
class TestSaveExperience:
    def test_save_experience_returns_200(self, profile_client):
        import json
        payload = json.dumps([{
            "title": "SWE", "company": "Acme", "type": "CDI",
            "period": "2024 – Present", "bullets": ["Built things"]
        }])
        r = profile_client.post("/profile/experience", data={"data": payload})
        assert r.status_code == 200

    def test_save_experience_response_contains_flash(self, profile_client):
        import json
        r = profile_client.post("/profile/experience",
                                data={"data": json.dumps([])})
        assert "Sauvegardé" in r.text
```

- [ ] **Step 2: Run — confirm fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestSaveExperience -v
```
Expected: FAIL — 404

- [ ] **Step 3: Add POST route to `dashboard/app.py`**

```python
@app.post("/profile/experience", response_class=HTMLResponse)
async def profile_save_experience(request: Request, data: str = Form("")):
    import json
    import profile_parser
    profile_data = profile_parser.load_profile()
    try:
        profile_data["experience"] = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        profile_data["experience"] = []
    profile_parser.save_profile(profile_data)
    return templates.TemplateResponse(
        request,
        "partials/profile_experience.html",
        {"profile": profile_data, "saved": True},
    )
```

- [ ] **Step 4: Write `dashboard/templates/partials/profile_experience.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<div id="exp-cards">
  {% for exp in profile.experience %}
  <div class="pf-card exp-card">
    <div class="grid grid-cols-2 gap-2 mb-2">
      <div><label class="pf-label">Titre</label><input class="pf-input" name="title" value="{{ exp.title }}"></div>
      <div><label class="pf-label">Entreprise</label><input class="pf-input" name="company" value="{{ exp.company }}"></div>
      <div><label class="pf-label">Type</label><input class="pf-input" name="type" value="{{ exp.type }}"></div>
      <div><label class="pf-label">Période</label><input class="pf-input" name="period" value="{{ exp.period }}"></div>
    </div>
    <label class="pf-label">Bullets (une par ligne)</label>
    <textarea class="pf-input mb-1" name="bullets" rows="3"
      style="resize:vertical">{{ exp.bullets | join('\n') }}</textarea>
    <button type="button" class="pf-del-btn" onclick="this.closest('.exp-card').remove()">✕ Supprimer</button>
  </div>
  {% endfor %}
</div>
<div class="flex justify-between items-center mt-2">
  <button type="button" class="pf-add-btn" onclick="addExpCard()">+ Ajouter un poste</button>
  <button type="button" class="pf-save-btn"
    hx-post="/profile/experience"
    hx-target="#section-experience"
    hx-swap="innerHTML"
    hx-vals="js:{data: collectExperience()}"
    hx-include="[name='_csrf']">Sauvegarder</button>
</div>
<script>
function collectExperience() {
  const cards = document.querySelectorAll('#exp-cards .exp-card');
  return JSON.stringify(Array.from(cards).map(c => ({
    title: c.querySelector('[name=title]').value.trim(),
    company: c.querySelector('[name=company]').value.trim(),
    type: c.querySelector('[name=type]').value.trim(),
    period: c.querySelector('[name=period]').value.trim(),
    bullets: c.querySelector('[name=bullets]').value
      .split('\n').map(s => s.trim()).filter(Boolean)
  })));
}
function addExpCard() {
  const tpl = `<div class="pf-card exp-card">
    <div class="grid grid-cols-2 gap-2 mb-2">
      <div><label class="pf-label">Titre</label><input class="pf-input" name="title" value=""></div>
      <div><label class="pf-label">Entreprise</label><input class="pf-input" name="company" value=""></div>
      <div><label class="pf-label">Type</label><input class="pf-input" name="type" value=""></div>
      <div><label class="pf-label">Période</label><input class="pf-input" name="period" value=""></div>
    </div>
    <label class="pf-label">Bullets (une par ligne)</label>
    <textarea class="pf-input mb-1" name="bullets" rows="3" style="resize:vertical"></textarea>
    <button type="button" class="pf-del-btn" onclick="this.closest('.exp-card').remove()">✕ Supprimer</button>
  </div>`;
  document.getElementById('exp-cards').insertAdjacentHTML('beforeend', tpl);
}
</script>
```

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py -v
```
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py dashboard/templates/partials/profile_experience.html tests/test_profile_routes.py
git commit -m "feat: add experience section with add/remove cards and save"
```

---

### Task 5: Skills section

**Files:**
- Modify: `dashboard/templates/partials/profile_skills.html`
- Modify: `dashboard/app.py`
- Modify: `tests/test_profile_routes.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_profile_routes.py`:

```python
class TestSaveSkills:
    def test_save_skills_returns_200(self, profile_client):
        import json
        payload = json.dumps({"Machine Learning": ["PyTorch", "Scikit-learn"]})
        r = profile_client.post("/profile/skills", data={"data": payload})
        assert r.status_code == 200

    def test_save_skills_response_contains_flash(self, profile_client):
        import json
        r = profile_client.post("/profile/skills",
                                data={"data": json.dumps({})})
        assert "Sauvegardé" in r.text
```

- [ ] **Step 2: Run — confirm fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestSaveSkills -v
```
Expected: FAIL — 404

- [ ] **Step 3: Add POST route to `dashboard/app.py`**

```python
@app.post("/profile/skills", response_class=HTMLResponse)
async def profile_save_skills(request: Request, data: str = Form("")):
    import json
    import profile_parser
    profile_data = profile_parser.load_profile()
    try:
        profile_data["skills"] = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        profile_data["skills"] = {}
    profile_parser.save_profile(profile_data)
    return templates.TemplateResponse(
        request,
        "partials/profile_skills.html",
        {"profile": profile_data, "saved": True},
    )
```

- [ ] **Step 4: Write `dashboard/templates/partials/profile_skills.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<div id="skills-cats">
  {% for category, items in profile.skills.items() %}
  <div class="pf-card skill-cat mb-2">
    <div class="flex justify-between items-center mb-1">
      <input class="pf-input" style="flex:1; margin-right:0.5rem"
        name="cat_name" value="{{ category }}" placeholder="Nom de la catégorie">
      <button type="button" class="pf-del-btn"
        onclick="this.closest('.skill-cat').remove()">✕</button>
    </div>
    <label class="pf-label">Compétences (une par ligne)</label>
    <textarea class="pf-input" name="cat_items" rows="4"
      style="resize:vertical">{{ items | join('\n') }}</textarea>
  </div>
  {% endfor %}
</div>
<div class="flex justify-between items-center mt-2">
  <button type="button" class="pf-add-btn" onclick="addSkillCat()">+ Ajouter une catégorie</button>
  <button type="button" class="pf-save-btn"
    hx-post="/profile/skills"
    hx-target="#section-skills"
    hx-swap="innerHTML"
    hx-vals="js:{data: collectSkills()}">Sauvegarder</button>
</div>
<script>
function collectSkills() {
  const cats = document.querySelectorAll('#skills-cats .skill-cat');
  const result = {};
  cats.forEach(cat => {
    const name = cat.querySelector('[name=cat_name]').value.trim();
    const items = cat.querySelector('[name=cat_items]').value
      .split('\n').map(s => s.trim()).filter(Boolean);
    if (name) result[name] = items;
  });
  return JSON.stringify(result);
}
function addSkillCat() {
  const tpl = `<div class="pf-card skill-cat mb-2">
    <div class="flex justify-between items-center mb-1">
      <input class="pf-input" style="flex:1; margin-right:0.5rem"
        name="cat_name" value="" placeholder="Nom de la catégorie">
      <button type="button" class="pf-del-btn"
        onclick="this.closest('.skill-cat').remove()">✕</button>
    </div>
    <label class="pf-label">Compétences (une par ligne)</label>
    <textarea class="pf-input" name="cat_items" rows="3" style="resize:vertical"></textarea>
  </div>`;
  document.getElementById('skills-cats').insertAdjacentHTML('beforeend', tpl);
}
</script>
```

- [ ] **Step 5: Run tests**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py -v
```
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py dashboard/templates/partials/profile_skills.html tests/test_profile_routes.py
git commit -m "feat: add skills section with category add/remove and save"
```

---

### Task 6: Education and Projects sections

**Files:**
- Modify: `dashboard/templates/partials/profile_education.html`
- Modify: `dashboard/templates/partials/profile_projects.html`
- Modify: `dashboard/app.py`
- Modify: `tests/test_profile_routes.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_profile_routes.py`:

```python
class TestSaveEducation:
    def test_save_education_returns_200(self, profile_client):
        import json
        payload = json.dumps({
            "education": [{"degree": "MSc", "school": "School", "period": "2022–2024"}],
            "certifications": ["AWS ML"]
        })
        r = profile_client.post("/profile/education", data={"data": payload})
        assert r.status_code == 200

    def test_save_education_response_contains_flash(self, profile_client):
        import json
        r = profile_client.post("/profile/education",
                                data={"data": json.dumps({"education": [], "certifications": []})})
        assert "Sauvegardé" in r.text


class TestSaveProjects:
    def test_save_projects_returns_200(self, profile_client):
        import json
        payload = json.dumps([{"name": "my-proj", "description": "A project"}])
        r = profile_client.post("/profile/projects", data={"data": payload})
        assert r.status_code == 200

    def test_save_projects_response_contains_flash(self, profile_client):
        import json
        r = profile_client.post("/profile/projects", data={"data": json.dumps([])})
        assert "Sauvegardé" in r.text
```

- [ ] **Step 2: Run — confirm fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py::TestSaveEducation tests/test_profile_routes.py::TestSaveProjects -v
```
Expected: FAIL — 404

- [ ] **Step 3: Add POST routes to `dashboard/app.py`**

```python
@app.post("/profile/education", response_class=HTMLResponse)
async def profile_save_education(request: Request, data: str = Form("")):
    import json
    import profile_parser
    profile_data = profile_parser.load_profile()
    try:
        parsed = json.loads(data)
        profile_data["education"] = parsed.get("education", [])
        profile_data["certifications"] = parsed.get("certifications", [])
    except (json.JSONDecodeError, ValueError):
        pass
    profile_parser.save_profile(profile_data)
    return templates.TemplateResponse(
        request,
        "partials/profile_education.html",
        {"profile": profile_data, "saved": True},
    )


@app.post("/profile/projects", response_class=HTMLResponse)
async def profile_save_projects(request: Request, data: str = Form("")):
    import json
    import profile_parser
    profile_data = profile_parser.load_profile()
    try:
        profile_data["projects"] = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        profile_data["projects"] = []
    profile_parser.save_profile(profile_data)
    return templates.TemplateResponse(
        request,
        "partials/profile_projects.html",
        {"profile": profile_data, "saved": True},
    )
```

- [ ] **Step 4: Write `dashboard/templates/partials/profile_education.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<p class="pf-label mb-2" style="font-size:0.8rem; color:#94a3b8;">Diplômes</p>
<div id="edu-cards">
  {% for edu in profile.education %}
  <div class="pf-card edu-card mb-2">
    <div class="grid grid-cols-2 gap-2 mb-1">
      <div style="grid-column:span 2"><label class="pf-label">Diplôme</label>
        <input class="pf-input" name="degree" value="{{ edu.degree }}"></div>
      <div><label class="pf-label">École</label>
        <input class="pf-input" name="school" value="{{ edu.school }}"></div>
      <div><label class="pf-label">Période</label>
        <input class="pf-input" name="period" value="{{ edu.period }}"></div>
    </div>
    <button type="button" class="pf-del-btn"
      onclick="this.closest('.edu-card').remove()">✕ Supprimer</button>
  </div>
  {% endfor %}
</div>
<button type="button" class="pf-add-btn mb-3" onclick="addEduCard()">+ Ajouter un diplôme</button>

<p class="pf-label mb-1" style="font-size:0.8rem; color:#94a3b8;">Certifications (une par ligne)</p>
<textarea id="cert-items" class="pf-input mb-2" rows="5"
  style="resize:vertical">{{ profile.certifications | join('\n') }}</textarea>

<div class="flex justify-end mt-1">
  <button type="button" class="pf-save-btn"
    hx-post="/profile/education"
    hx-target="#section-education"
    hx-swap="innerHTML"
    hx-vals="js:{data: collectEducation()}">Sauvegarder</button>
</div>
<script>
function collectEducation() {
  const cards = document.querySelectorAll('#edu-cards .edu-card');
  const education = Array.from(cards).map(c => ({
    degree: c.querySelector('[name=degree]').value.trim(),
    school: c.querySelector('[name=school]').value.trim(),
    period: c.querySelector('[name=period]').value.trim(),
  }));
  const certifications = document.getElementById('cert-items').value
    .split('\n').map(s => s.trim()).filter(Boolean);
  return JSON.stringify({education, certifications});
}
function addEduCard() {
  const tpl = `<div class="pf-card edu-card mb-2">
    <div class="grid grid-cols-2 gap-2 mb-1">
      <div style="grid-column:span 2"><label class="pf-label">Diplôme</label>
        <input class="pf-input" name="degree" value=""></div>
      <div><label class="pf-label">École</label>
        <input class="pf-input" name="school" value=""></div>
      <div><label class="pf-label">Période</label>
        <input class="pf-input" name="period" value=""></div>
    </div>
    <button type="button" class="pf-del-btn"
      onclick="this.closest('.edu-card').remove()">✕ Supprimer</button>
  </div>`;
  document.getElementById('edu-cards').insertAdjacentHTML('beforeend', tpl);
}
</script>
```

- [ ] **Step 5: Write `dashboard/templates/partials/profile_projects.html`**

```html
{% if saved %}<p class="pf-flash mb-2">✓ Sauvegardé</p>{% endif %}
<div id="proj-cards">
  {% for proj in profile.projects %}
  <div class="pf-card proj-card mb-2">
    <div class="mb-1">
      <label class="pf-label">Nom du projet</label>
      <input class="pf-input mb-1" name="proj_name" value="{{ proj.name }}">
      <label class="pf-label">Description</label>
      <textarea class="pf-input" name="proj_desc" rows="2"
        style="resize:vertical">{{ proj.description }}</textarea>
    </div>
    <button type="button" class="pf-del-btn"
      onclick="this.closest('.proj-card').remove()">✕ Supprimer</button>
  </div>
  {% endfor %}
</div>
<div class="flex justify-between items-center mt-2">
  <button type="button" class="pf-add-btn" onclick="addProjCard()">+ Ajouter un projet</button>
  <button type="button" class="pf-save-btn"
    hx-post="/profile/projects"
    hx-target="#section-projects"
    hx-swap="innerHTML"
    hx-vals="js:{data: collectProjects()}">Sauvegarder</button>
</div>
<script>
function collectProjects() {
  const cards = document.querySelectorAll('#proj-cards .proj-card');
  return JSON.stringify(Array.from(cards).map(c => ({
    name: c.querySelector('[name=proj_name]').value.trim(),
    description: c.querySelector('[name=proj_desc]').value.trim(),
  })));
}
function addProjCard() {
  const tpl = `<div class="pf-card proj-card mb-2">
    <div class="mb-1">
      <label class="pf-label">Nom du projet</label>
      <input class="pf-input mb-1" name="proj_name" value="">
      <label class="pf-label">Description</label>
      <textarea class="pf-input" name="proj_desc" rows="2" style="resize:vertical"></textarea>
    </div>
    <button type="button" class="pf-del-btn"
      onclick="this.closest('.proj-card').remove()">✕ Supprimer</button>
  </div>`;
  document.getElementById('proj-cards').insertAdjacentHTML('beforeend', tpl);
}
</script>
```

- [ ] **Step 6: Run full test suite**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_profile_routes.py tests/test_profile_parser.py -v
```
Expected: all passed

- [ ] **Step 7: Run the full suite to check for regressions**

```bash
PYTHONPATH=. .venv/bin/pytest tests/ -q
```
Expected: all passed

- [ ] **Step 8: Commit**

```bash
git add dashboard/app.py \
  dashboard/templates/partials/profile_education.html \
  dashboard/templates/partials/profile_projects.html \
  tests/test_profile_routes.py
git commit -m "feat: add education, certifications, and projects profile sections"
```
