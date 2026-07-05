"""Rescore all existing DB offers using the updated score_offer() function.

Usage:
    python -m scripts.rescore --user-id <UUID> [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

from scripts.import_offers import score_to_grade
from scripts.models import RawOffer
from scripts.pre_filter import load_settings, score_offer

logger = logging.getLogger(__name__)

_DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://career:career@localhost:5432/career"
)


def _infer_portal(url: str) -> str:
    url_lower = url.lower()
    if "lever.co" in url_lower:
        return "lever"
    if "greenhouse.io" in url_lower:
        return "greenhouse"
    if "ashby.com" in url_lower:
        return "ashby"
    return "unknown"


def rescore(
    conn: psycopg2.extensions.connection, user_id: str, dry_run: bool = False
) -> dict:
    settings = load_settings(user_id=user_id)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, company, role, offer_url, score_grade, score_value, description"
            " FROM applications WHERE user_id = %s AND status = 'À envoyer'",
            (user_id,),
        )
        rows = cur.fetchall()

    updates: list[tuple[str, float, int]] = []
    summary: dict[str, int] = {"total": len(rows), "changed": 0}

    for row in rows:
        id_, company, role, offer_url, old_grade, old_score, description = row
        portal = _infer_portal(offer_url or "")
        offer = RawOffer(
            title=role or "",
            company=company or "",
            url=offer_url or "",
            portal=portal,
            location="",
            description=description or "",
        )
        new_score, _ = score_offer(offer, settings)
        new_grade = score_to_grade(new_score)
        if new_grade != old_grade or abs(new_score - (old_score or 0)) > 0.001:
            updates.append((new_grade, new_score, id_))
            summary["changed"] += 1
            logger.info(
                "  id=%-4d  %-40s : %s/%.1f -> %s/%.1f",
                id_,
                f"{company} / {role}"[:40],
                old_grade,
                old_score,
                new_grade,
                new_score,
            )

    if not dry_run and updates:
        with conn.cursor() as cur:
            for new_grade, new_score, id_ in updates:
                cur.execute(
                    "UPDATE applications SET score_grade = %s, score_value = %s"
                    " WHERE id = %s AND user_id = %s",
                    (new_grade, new_score, id_, user_id),
                )
        conn.commit()

    return summary


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="Rescore all DB offers with updated scorer"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print changes without writing"
    )
    parser.add_argument(
        "--user-id",
        required=True,
        metavar="UUID",
        help="Supabase user UUID to scope rescored offers",
    )
    args = parser.parse_args()

    conn = psycopg2.connect(_DATABASE_URL)
    prefix = "[DRY RUN] " if args.dry_run else ""
    logger.info("%sRescoring offers for user %s", prefix, args.user_id)

    try:
        stats = rescore(conn, args.user_id, dry_run=args.dry_run)
    finally:
        conn.close()

    action = "Would update" if args.dry_run else "Updated"
    print(f"\n{prefix}Total: {stats['total']} offers -- {action}: {stats['changed']}")


if __name__ == "__main__":
    main()
