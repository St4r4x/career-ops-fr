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
    - Phone: +33 6 00 00 00 00
    - Location: Paris
    - LinkedIn:
    - GitHub: github.com/testuser

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
