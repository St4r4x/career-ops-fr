# Dashboard Improvements — Design Spec
**Date:** 2026-07-03

## Overview

Four independent improvements to the dashboard, each self-contained:

1. Follow-up reminders (badge + bandeau)
2. Cover letter viewer (`/cover-letters`)
3. Funnel + conversion rates in `/stats`
4. Daily report widget in `/stats`

---

## Feature 1 — Follow-up reminders

### Context

`db.py` already has `_FOLLOW_UP_DAYS = 7` and a `send_date` column. `follow_up_date` column exists but is unused. Statuses in scope: `"Envoyée"` and `"Entretien RH"`.

### Logic

A follow-up is due when:
- status is `"Envoyée"` and `send_date` < today − 7 days
- status is `"Entretien RH"` and `send_date` < today − 7 days

Use `send_date` for both (already populated when status changes to "Envoyée"). If `send_date` is NULL, skip.

### Implementation

**`db.py`** — add `get_followups() -> list[dict]` method on `DB`:
```python
def get_followups(self) -> list[dict]:
    cutoff = (date.today() - timedelta(days=_FOLLOW_UP_DAYS)).isoformat()
    rows = self._conn.execute(
        _SELECT + " WHERE status IN ('Envoyée','Entretien RH') AND send_date <= ? AND send_date IS NOT NULL",
        (cutoff,)
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
```

**`app.py`** — in the `GET /` route, add `followups = db.get_followups()` to context.

**`dashboard/templates/index.html`** — two changes:
1. Bandeau en haut (masqué si `followups` est vide) :
   ```html
   {% if followups %}
   <div class="followup-banner">
     {{ followups|length }} offre(s) à relancer —
     <a href="/?status=followup">voir</a>
   </div>
   {% endif %}
   ```
2. Pastille rouge sur chaque ligne d'offre dont l'`id` est dans `followup_ids`.

**Filtre "À relancer"** — ajouter `"followup"` comme valeur de filtre status dans `GET /offers`. Côté DB, `get_all(filters)` traduit `status=followup` vers la query `get_followups()`.

### What's not needed
- No new DB column (reuse `send_date`)
- No new settings key (reuse `_FOLLOW_UP_DAYS`)

---

## Feature 2 — Cover letter viewer

### Context

Files: `config/cover-letter-*.json`, not committed (gitignored). No existing route. Structure: JSON with string fields (intro, body, closing_line, etc. — varies per file).

### Implementation

**`app.py`** — new route `GET /cover-letters`:
```python
@app.get("/cover-letters", response_class=HTMLResponse)
def cover_letters(request: Request):
    config_dir = Path("config")
    letters = []
    for p in sorted(config_dir.glob("cover-letter-*.json")):
        company = p.stem.replace("cover-letter-", "")
        data = json.loads(p.read_text(encoding="utf-8"))
        letters.append({"company": company, "data": data, "filename": p.name})
    return templates.TemplateResponse("cover_letters.html", {"request": request, "letters": letters})
```

**`dashboard/templates/cover_letters.html`** — layout `base.html`. Une carte par lettre :
- Titre : nom entreprise (depuis le filename)
- Champs du JSON rendus en paragraphes labelisés
- Bouton "Copier" par champ (JS `navigator.clipboard.writeText`)

**Nav** — ajouter le lien "Lettres" dans `base.html` nav.

### What's not needed
- No DB persistence (read-only from files)
- No edit functionality

---

## Feature 3 — Funnel + conversion rates in `/stats`

### Context

`db.get_stats()` retourne déjà `by_status: dict[str, int]`. À enrichir avec les taux de conversion.

### Funnel order

```
À envoyer → Envoyée → Relance → Entretien RH → Entretien tech → Offre → Acceptée
                                                                              ↓
                                                              Refusée / Abandonnée (sorties)
```

### Implementation

**`db.py`** — `get_stats()` existe déjà et retourne `by_status`. Pas de modification nécessaire — le calcul des taux se fait dans le template ou dans la route.

**`app.py`** — dans `GET /stats`, calculer les taux de conversion :
```python
funnel_steps = ["À envoyer", "Envoyée", "Relance", "Entretien RH", "Entretien tech", "Offre", "Acceptée"]
exits = ["Refusée", "Abandonnée"]
# taux = count[step_n+1] / count[step_n] * 100 si count[step_n] > 0
```
Passer `funnel` (list de dicts `{status, count, rate}`) et `exits` au contexte.

**`dashboard/templates/stats.html`** — nouvelle section "Funnel" :
- Barres horizontales décroissantes (CSS pur, largeur proportionnelle au max)
- Taux de conversion entre étapes adjacentes affiché entre les barres
- Sorties (Refusée, Abandonnée) en bas avec couleur distincte (rouge/gris)

### What's not needed
- No new DB query (reuse `by_status` from `get_stats()`)

---

## Feature 4 — Daily report widget in `/stats`

### Context

`daily_report.py` re-lance le pipeline complet (scan → scrape → score) — trop coûteux pour un widget. Le widget lit plutôt le dernier fichier `reports/daily-*.md` généré sur disque.

### Implementation

**`app.py`** — dans `GET /stats`, ajouter :
```python
reports_dir = Path("reports")
report_files = sorted(reports_dir.glob("daily-*.md"), reverse=True)
latest_report = report_files[0].read_text(encoding="utf-8") if report_files else None
latest_report_date = report_files[0].stem.replace("daily-", "") if report_files else None
```
Passer `latest_report` et `latest_report_date` au contexte.

**`dashboard/templates/stats.html`** — widget "Dernier rapport" :
- Titre : "Rapport du {latest_report_date}" (ou "Aucun rapport disponible")
- Contenu Markdown rendu en HTML via `mistune` (ajouté à `requirements.txt`)
- Placé à côté du funnel

### What's not needed
- No re-run of the pipeline
- No new route
- `mistune==3.0.2` added to `requirements.txt`

---

## Files touched

| File | Changes |
|------|---------|
| `dashboard/db.py` | Add `get_followups()` method |
| `dashboard/app.py` | Feature 1 context, `/cover-letters` route, feature 3/4 context in `/stats` |
| `dashboard/templates/index.html` | Bandeau + pastilles follow-up |
| `dashboard/templates/stats.html` | Funnel section + report widget |
| `dashboard/templates/cover_letters.html` | New template |
| `dashboard/templates/base.html` | Add "Lettres" nav link |

## Tests

- `tests/test_dashboard_app.py` — `GET /cover-letters` retourne 200 ; `GET /stats` retourne 200 avec funnel data
- `tests/test_db.py` (ou `test_dashboard_app.py`) — `get_followups()` retourne les offres dues, pas les autres
