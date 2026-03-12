"""
Automation 4: Lead Enrichment & Follow-up
==========================================
When a new lead arrives, pull their profile, use Claude to generate a
personalized outreach message, and identify matching clients.
"""

from __future__ import annotations

import json

import anthropic

from topmatch.config import ANTHROPIC_API_KEY
from topmatch.jaicob_client import JaicobClient

OUTREACH_PROMPT = """\
Je bent een recruiter bij Top Match, een persoonlijk en professioneel
recruitmentbureau in Nederland.

Schrijf een kort, persoonlijk berichtje (3-5 zinnen) in het Nederlands om
contact op te nemen met deze lead. Het doel is om hun interesse te wekken
zonder te pushy te zijn.

**Lead profiel:**
Naam: {name}
Huidige functie: {function}
Vaardigheden: {skills}
Werkervaring: {experience}
Opleiding: {education}

**Onze klanten die mogelijk passen:**
{matching_clients}

Het bericht moet:
- Persoonlijk en warm zijn (gebruik voornaam)
- Verwijzen naar hun specifieke ervaring/vaardigheden
- Aangeven dat je mogelijk iets interessants hebt
- Eindigen met een zachte call-to-action

Geef je antwoord als JSON:
{{
  "subject": "onderwerp voor email",
  "message": "het bericht",
  "matching_client_ids": ["id1", "id2"],
  "follow_up_days": <aantal dagen tot follow-up>
}}
"""


def enrich_lead(
    lead_id: str,
    jaicob: JaicobClient | None = None,
) -> dict:
    """Pull lead data, generate outreach, and find matching clients."""
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        # 1. Get lead profile
        lead = jaicob.get_lead(lead_id)

        # 2. Get all clients for matching
        clients_resp = jaicob.list_clients(take=100)
        clients = clients_resp.get("data", [])

        # 3. Generate outreach with Claude
        claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        result = _generate_outreach(claude, lead, clients)
        result["lead_id"] = lead_id
        result["lead_name"] = _lead_name(lead)
        return result
    finally:
        if own_client and jaicob:
            jaicob.close()


def _lead_name(lead: dict) -> str:
    details = lead.get("applicantDetails", {})
    return f"{details.get('firstName', '')} {details.get('lastName', '')}".strip()


def _generate_outreach(
    claude: anthropic.Anthropic, lead: dict, clients: list[dict]
) -> dict:
    details = lead.get("applicantDetails", {})
    skills = [s.get("name", "") for s in lead.get("skills", [])]
    experiences = lead.get("workExperiences", [])
    exp_summary = "; ".join(
        f"{e.get('position', '')} bij {e.get('company', '')}"
        for e in experiences[:5]
    )
    educations = lead.get("educations", [])
    edu_summary = "; ".join(
        f"{e.get('degree', '')} — {e.get('organization', '')}"
        for e in educations[:3]
    )
    client_lines = "\n".join(
        f"- {c.get('id')}: {c.get('companyName', '')} "
        f"({c.get('details', {}).get('description', '')[:100]})"
        for c in clients[:20]
    )

    prompt = OUTREACH_PROMPT.format(
        name=_lead_name(lead),
        function=lead.get("function", "niet opgegeven"),
        skills=", ".join(skills) or "niet opgegeven",
        experience=exp_summary or "niet opgegeven",
        education=edu_summary or "niet opgegeven",
        matching_clients=client_lines or "Geen klanten beschikbaar",
    )

    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(message.content[0].text)
    except json.JSONDecodeError:
        return {
            "subject": "",
            "message": message.content[0].text,
            "matching_client_ids": [],
            "follow_up_days": 3,
        }
