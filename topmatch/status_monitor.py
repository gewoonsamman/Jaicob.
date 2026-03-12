"""
Automation 6: Candidate Status Monitor
=======================================
Finds candidates that haven't been updated recently and alerts recruiters
so no one falls through the cracks.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from topmatch.jaicob_client import JaicobClient


def find_stale_candidates(
    stale_days: int = 7,
    jaicob: JaicobClient | None = None,
) -> list[dict]:
    """Find candidates whose records haven't been updated in `stale_days` days."""
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        cutoff = datetime.utcnow() - timedelta(days=stale_days)
        stale: list[dict] = []
        page = 1

        while True:
            resp = jaicob.list_candidates(page=page, take=100)
            for candidate in resp.get("data", []):
                updated = _parse_date(candidate.get("updatedAt"))
                if updated < cutoff:
                    details = candidate.get("applicantDetails", {})
                    stale.append(
                        {
                            "id": candidate.get("id"),
                            "name": f"{details.get('firstName', '')} {details.get('lastName', '')}".strip(),
                            "function": candidate.get("function", ""),
                            "last_updated": candidate.get("updatedAt", ""),
                            "days_stale": (datetime.utcnow() - updated).days,
                            "status": candidate.get("status", ""),
                        }
                    )
            if not resp.get("metadata", {}).get("hasNext", False):
                break
            page += 1

        stale.sort(key=lambda c: c["days_stale"], reverse=True)
        return stale
    finally:
        if own_client and jaicob:
            jaicob.close()


def format_stale_report(stale: list[dict]) -> str:
    """Format stale candidates into a readable alert."""
    if not stale:
        return "Alle kandidaten zijn up-to-date!"

    lines = [
        "⚠️  Top Match — Vergeten Kandidaten Alert",
        "=" * 50,
        "",
    ]
    for c in stale:
        lines.append(
            f"🔴 {c['name']} — {c['function'] or 'geen functie'} "
            f"({c['days_stale']} dagen niet bijgewerkt)"
        )
        lines.append(f"   Status: {c['status'] or 'onbekend'} | ID: {c['id']}")
        lines.append("")

    lines.append(f"Totaal: {len(stale)} kandidaten hebben aandacht nodig.")
    return "\n".join(lines)


def _parse_date(date_str: str | None) -> datetime:
    if not date_str:
        return datetime.min
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    except (ValueError, AttributeError):
        return datetime.min
