"""
Automation 2: Candidate-Vacancy Matching
=========================================
Pulls all candidates and vacancies from Jaicob, uses Claude for semantic
matching, and produces a digest of overlooked matches.
"""

from __future__ import annotations

import json

import anthropic

from topmatch.config import ANTHROPIC_API_KEY
from topmatch.jaicob_client import JaicobClient

MATCHING_PROMPT = """\
Je bent een senior recruiter bij Top Match. Analyseer de onderstaande kandidaat
en vacature en beoordeel of er een goede match is.

Let op semantische overeenkomsten — bijvoorbeeld:
- "Medewerker binnendienst" en "Inside Sales" zijn gelijk
- "Projectleider" en "Project Manager" zijn gelijk
- Vergelijkbare vaardigheden met andere namen

**Kandidaat:**
Naam: {name}
Functie: {function}
Vaardigheden: {skills}
Ervaring: {experience}

**Vacature:**
Titel: {title}
Beschrijving: {description}

Antwoord als JSON:
- "match_score": 0.0 tot 1.0
- "explanation": korte uitleg in het Nederlands (max 2 zinnen)
- "key_overlaps": lijst van overlappende vaardigheden/ervaringen
"""


def find_matches(
    min_score: float = 0.6,
    jaicob: JaicobClient | None = None,
) -> list[dict]:
    """Find overlooked candidate-vacancy matches across the entire database."""
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        candidates = _fetch_all(jaicob, "candidates")
        vacancies = _fetch_all(jaicob, "vacancies")
        claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        matches: list[dict] = []
        for candidate in candidates:
            for vacancy in vacancies:
                result = _match(claude, candidate, vacancy)
                score = result.get("match_score", 0)
                if score >= min_score:
                    matches.append(
                        {
                            "candidate_id": candidate.get("id"),
                            "candidate_name": _candidate_name(candidate),
                            "vacancy_id": vacancy.get("id"),
                            "vacancy_title": vacancy.get("title", ""),
                            **result,
                        }
                    )

        matches.sort(key=lambda m: m.get("match_score", 0), reverse=True)
        return matches
    finally:
        if own_client and jaicob:
            jaicob.close()


def generate_digest(matches: list[dict]) -> str:
    """Format matches into a human-readable Dutch digest."""
    if not matches:
        return "Geen nieuwe matches gevonden vandaag."

    lines = ["🔍 Top Match — Dagelijks Matching Overzicht", "=" * 50, ""]
    for m in matches:
        lines.append(
            f"✅ {m['candidate_name']} → {m['vacancy_title']} "
            f"({m['match_score']:.0%})"
        )
        lines.append(f"   {m.get('explanation', '')}")
        overlaps = m.get("key_overlaps", [])
        if overlaps:
            lines.append(f"   Overlap: {', '.join(overlaps)}")
        lines.append("")
    return "\n".join(lines)


# ── helpers ─────────────────────────────────────────────────────

def _fetch_all(jaicob: JaicobClient, resource: str) -> list[dict]:
    fetcher = getattr(jaicob, f"list_{resource}")
    items: list[dict] = []
    page = 1
    while True:
        resp = fetcher(page=page, take=100)
        items.extend(resp.get("data", []))
        if not resp.get("metadata", {}).get("hasNext", False):
            break
        page += 1
    return items


def _candidate_name(c: dict) -> str:
    details = c.get("applicantDetails", {})
    first = details.get("firstName", "")
    last = details.get("lastName", "")
    return f"{first} {last}".strip() or "Onbekend"


def _match(claude: anthropic.Anthropic, candidate: dict, vacancy: dict) -> dict:
    details = candidate.get("applicantDetails", {})
    skills = [s.get("name", "") for s in candidate.get("skills", [])]
    experience_items = candidate.get("workExperiences", [])
    experience_summary = "; ".join(
        f"{e.get('position', '')} bij {e.get('company', '')}"
        for e in experience_items[:5]
    )

    prompt = MATCHING_PROMPT.format(
        name=_candidate_name(candidate),
        function=candidate.get("function", ""),
        skills=", ".join(skills) or "niet opgegeven",
        experience=experience_summary or "niet opgegeven",
        title=vacancy.get("title", ""),
        description=vacancy.get("description", ""),
    )

    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(message.content[0].text)
    except json.JSONDecodeError:
        return {"match_score": 0.0, "explanation": message.content[0].text}
