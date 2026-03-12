"""
Automation 1: CV Parsing Pipeline
=================================
Watches a folder (or accepts a file path) for new CVs, parses them via Jaicob,
scores the candidate against open vacancies using Claude, and creates the
candidate record in the ATS when the match score is high enough.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

from topmatch.config import ANTHROPIC_API_KEY
from topmatch.jaicob_client import JaicobClient

SCORE_PROMPT = """\
Je bent een senior recruiter bij Top Match, een recruitmentbureau in Nederland.

Hieronder staat het geparseerde CV van een kandidaat en de beschrijving van een vacature.

**Kandidaat (JSON):**
{candidate_json}

**Vacature:**
Titel: {vacancy_title}
Beschrijving: {vacancy_description}

Geef een JSON-antwoord met exact deze velden:
- "score": een getal van 0.0 tot 1.0 dat aangeeft hoe goed de kandidaat past
- "reasoning": een korte uitleg in het Nederlands (max 3 zinnen)
- "missing": een lijst van vaardigheden/eisen die de kandidaat mist

Antwoord ALLEEN met geldige JSON, geen tekst eromheen.
"""


def parse_and_score(
    cv_path: str | Path,
    jaicob: JaicobClient | None = None,
    min_score: float = 0.6,
    auto_create: bool = False,
    top_n: int = 5,
) -> list[dict]:
    """Parse a CV and score it against all active vacancies.

    Returns a list of dicts with vacancy info and match scores, sorted best-first.
    """
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        # 1. Parse the resume via Jaicob
        parsed = jaicob.parse_resume(cv_path)

        # 2. Fetch active vacancies
        vacancies = _fetch_all_vacancies(jaicob)

        # 3. Score against each vacancy using Claude
        claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        results: list[dict] = []
        for vacancy in vacancies:
            score_data = _score_candidate(claude, parsed, vacancy)
            score_data["vacancy_id"] = vacancy.get("id")
            score_data["vacancy_title"] = vacancy.get("title", "")
            results.append(score_data)

        results.sort(key=lambda r: r.get("score", 0), reverse=True)
        results = results[:top_n]

        # 4. Optionally create the candidate in Jaicob
        if auto_create and results and results[0].get("score", 0) >= min_score:
            candidate = jaicob.create_candidate(parsed)
            for r in results:
                r["candidate_id"] = candidate.get("id")

        return results
    finally:
        if own_client and jaicob:
            jaicob.close()


def _fetch_all_vacancies(jaicob: JaicobClient) -> list[dict]:
    """Paginate through all vacancies."""
    all_vacancies: list[dict] = []
    page = 1
    while True:
        resp = jaicob.list_vacancies(page=page, take=100)
        data = resp.get("data", [])
        all_vacancies.extend(data)
        meta = resp.get("metadata", {})
        if not meta.get("hasNext", False):
            break
        page += 1
    return all_vacancies


def _score_candidate(
    claude: anthropic.Anthropic, candidate: dict, vacancy: dict
) -> dict:
    """Ask Claude to score a candidate against a vacancy."""
    prompt = SCORE_PROMPT.format(
        candidate_json=json.dumps(candidate, ensure_ascii=False, indent=2),
        vacancy_title=vacancy.get("title", ""),
        vacancy_description=vacancy.get("description", ""),
    )
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"score": 0.0, "reasoning": text, "missing": []}


def watch_folder(
    folder: str | Path,
    jaicob: JaicobClient | None = None,
    min_score: float = 0.6,
    auto_create: bool = True,
) -> None:
    """Process all CV files in a folder (one-shot scan)."""
    folder = Path(folder)
    extensions = {".pdf", ".docx", ".doc", ".rtf"}
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in extensions:
            print(f"\n📄 Verwerken: {path.name}")
            results = parse_and_score(
                path, jaicob=jaicob, min_score=min_score, auto_create=auto_create
            )
            for r in results:
                score = r.get("score", 0)
                title = r.get("vacancy_title", "?")
                print(f"  {'✅' if score >= min_score else '⬜'} {score:.0%} — {title}")
                if r.get("reasoning"):
                    print(f"     {r['reasoning']}")
