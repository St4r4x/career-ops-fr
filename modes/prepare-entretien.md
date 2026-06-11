# prepare-entretien

Generate the interview prep sheet PDF for a specific offer. Called after the CV has been selected.

## Input

Called with:
```bash
claude --system-prompt "$(cat modes/prepare-entretien.md)" "Prépare l'entretien pour l'offre ID <id>"
```

Extract the offer ID from the user message. Look for a number after "ID", "id", "offer-id", or "offre".

If no ID is found in the message, ask: "Quel est l'ID de l'offre ?"

## Instructions

### Phase 1 — Load context

1. Read `config/profile.md`
2. Query the DB:
   ```bash
   sqlite3 dashboard/data/applications.db \
     "SELECT id, company, role, offer_url, description FROM applications WHERE id = <offer_id>;"
   ```
3. Derive slug: `company.lower().replace(' ', '-')`
4. If `description` is empty or less than 500 characters, fetch the full job description:
   ```bash
   python -c "import httpx; r = httpx.get('<offer_url>', follow_redirects=True, timeout=15); print(r.text[:12000])"
   ```
   Extract the meaningful text mentally (strip HTML tags, navigation, footers).

### Phase 2 — Analyse the offer

From the description, extract:
- `top_skills`: 5–7 required skills mentioned explicitly (exact terms from the posting)
- `company_context`: mission, product, estimated size, tech stack mentioned

### Phase 3 — Generate prep sheet

1. Build `/tmp/prep-context-<slug>.json`:
   ```json
   {
     "company": "<company>",
     "role": "<role>",
     "date_str": "<YYYY-MM-DD>",
     "company_summary": "<2-3 sentences: mission, product, size, why interesting>",
     "tech_stack": ["<tech1>", "<tech2>"],
     "questions": [
       {"theme": "Technique ML", "question": "<question>"},
       {"theme": "MLOps", "question": "<question>"},
       {"theme": "Comportemental", "question": "<question>"}
     ]
   }
   ```
   Aim for 8–12 questions covering: technical depth (linked to top_skills), MLOps/deployment,
   behavioural (STAR format expected), and "why us / why this role".
2. Run:
   ```bash
   python scripts/generate_prep_sheet.py \
     --offer "<slug>" \
     --date "<YYYY-MM-DD>" \
     --context-file /tmp/prep-context-<slug>.json
   ```
   Note the output path printed.

### Phase 4 — Summarise

Print:
```
✅ Fiche entretien prête — <company> / <role>

Fiche révision: output/<slug>-<date>/prep-sheet-<slug>-<date>.pdf

Ouvre le PDF et révise avant l'entretien.
```

## Constraints

- Do NOT generate a CV or cover letter — this mode is for interview prep only.
- Do NOT update cv_path or cover_letter_path in the DB.
- Prep sheet: 8–12 questions minimum.
