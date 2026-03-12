"""
Automation 3: Automated Vacancy Creation from Brief
====================================================
Takes a short recruiter brief (or pasted client email) and uses Claude to
expand it into a full Jaicob vacancy with all required fields.
"""

from __future__ import annotations

import json

import anthropic

from topmatch.config import ANTHROPIC_API_KEY
from topmatch.jaicob_client import JaicobClient

EXPAND_PROMPT = """\
Je bent een recruitment-specialist bij Top Match. Maak van het onderstaande
korte vacature-briefje een volledige vacaturetekst.

**Briefje van recruiter:**
{brief}

**Beschikbare taxonomie-opties (kies het best passende ID):**
Industrieën: {industries}
Opleidingsniveaus: {education_levels}
Functiecategorieën: {job_categories}
Senioriteitsniveaus: {seniorities}

Geef je antwoord als JSON met exact deze velden:
{{
  "title": "functietitel",
  "description": "volledige vacaturetekst in HTML-formaat",
  "employmentType": "permanent|temporary|fixed_term|fixed_term_with_option_for_permanent|freelance|traineeship|internship",
  "yearsOfExperience": <getal>,
  "workingHours": {{"from": <uren>, "to": <uren>}},
  "salary": {{"period": "monthly", "from": <bedrag>, "to": <bedrag>, "currency": "EUR"}},
  "location": {{"city": "stad", "country": "NL", "allowsRemoteWork": true/false}},
  "tags": ["tag1", "tag2"],
  "industryId": "gekozen-id",
  "educationLevelId": "gekozen-id",
  "jobCategoryId": "gekozen-id",
  "seniorityId": "gekozen-id"
}}

Schrijf de beschrijving in professioneel Nederlands met HTML-opmaak (<h3>, <ul>, <li>, <p>).
Antwoord ALLEEN met geldige JSON.
"""


def create_vacancy_from_brief(
    brief: str,
    jaicob: JaicobClient | None = None,
    publish: bool = False,
) -> dict:
    """Expand a short brief into a full vacancy and optionally push it to Jaicob.

    Returns the vacancy data dict (with 'id' if published).
    """
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        # 1. Load taxonomy options so Claude can pick the right IDs
        taxonomies = _load_taxonomies(jaicob)

        # 2. Ask Claude to expand the brief
        claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        vacancy_data = _expand_brief(claude, brief, taxonomies)

        # 3. Optionally publish to Jaicob
        if publish:
            result = jaicob.create_vacancy(vacancy_data)
            vacancy_data["id"] = result.get("id")

        return vacancy_data
    finally:
        if own_client and jaicob:
            jaicob.close()


def _load_taxonomies(jaicob: JaicobClient) -> dict[str, str]:
    """Fetch taxonomy lookup lists and format them for the prompt."""
    def fmt(items: list[dict]) -> str:
        return ", ".join(f"{i.get('id')}: {i.get('name', '')}" for i in items[:30])

    return {
        "industries": fmt(jaicob.list_industries()),
        "education_levels": fmt(jaicob.list_education_levels()),
        "job_categories": fmt(jaicob.list_job_categories()),
        "seniorities": fmt(jaicob.list_seniorities()),
    }


def _expand_brief(
    claude: anthropic.Anthropic, brief: str, taxonomies: dict[str, str]
) -> dict:
    prompt = EXPAND_PROMPT.format(brief=brief, **taxonomies)
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code block
        if "```" in text:
            json_str = text.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
            return json.loads(json_str.strip())
        raise ValueError(f"Claude gaf geen geldig JSON terug:\n{text}")
