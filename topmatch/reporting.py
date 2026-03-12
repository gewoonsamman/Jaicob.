"""
Automation 5: Client Reporting Dashboard
=========================================
Generates weekly reports per client: pipeline counts, new applications,
and a Claude-written summary for account managers.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import anthropic

from topmatch.config import ANTHROPIC_API_KEY
from topmatch.jaicob_client import JaicobClient

SUMMARY_PROMPT = """\
Je bent de account manager bij Top Match. Schrijf een kort weekrapport
(3-5 zinnen, professioneel Nederlands) voor de klant op basis van deze data.

**Klant:** {client_name}
**Kandidaten in pipeline:** {pipeline_count}
**Nieuwe sollicitaties deze week:** {new_applications}
**Actieve vacatures:** {active_vacancies}
**Vacature-titels:** {vacancy_titles}

Maak het persoonlijk en informatief. Als er weinig activiteit is, stel dan
proactief een actie voor (bijv. vacaturetekst aanpassen, salary range herzien).

Antwoord als JSON:
{{
  "summary": "het rapport in platte tekst",
  "status": "on_track|needs_attention|urgent",
  "suggested_actions": ["actie 1", "actie 2"]
}}
"""


def generate_client_reports(
    jaicob: JaicobClient | None = None,
) -> list[dict]:
    """Generate a weekly report for every client."""
    own_client = jaicob is None
    if own_client:
        jaicob = JaicobClient()

    try:
        clients_resp = jaicob.list_clients(take=100)
        clients = clients_resp.get("data", [])

        vacancies_resp = jaicob.list_vacancies(take=200)
        all_vacancies = vacancies_resp.get("data", [])

        applications_resp = jaicob.list_applications(take=200)
        all_applications = applications_resp.get("data", [])

        candidates_resp = jaicob.list_candidates(take=200)
        all_candidates = candidates_resp.get("data", [])

        claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        week_ago = datetime.utcnow() - timedelta(days=7)

        reports: list[dict] = []
        for client in clients:
            client_id = client.get("id")
            client_name = client.get("companyName", "Onbekend")

            # Filter vacancies for this client
            client_vacancies = [
                v for v in all_vacancies if v.get("clientId") == client_id
            ]
            vacancy_titles = [v.get("title", "") for v in client_vacancies]

            # Count candidates linked to this client
            client_candidates = [
                c for c in all_candidates if c.get("clientId") == client_id
            ]

            # Count recent applications
            new_apps = [
                a
                for a in all_applications
                if a.get("clientId") == client_id
                and _parse_date(a.get("createdAt")) >= week_ago
            ]

            report = _generate_summary(
                claude,
                client_name=client_name,
                pipeline_count=len(client_candidates),
                new_applications=len(new_apps),
                active_vacancies=len(client_vacancies),
                vacancy_titles=vacancy_titles,
            )
            report["client_id"] = client_id
            report["client_name"] = client_name
            reports.append(report)

        return reports
    finally:
        if own_client and jaicob:
            jaicob.close()


def format_reports(reports: list[dict]) -> str:
    """Format reports into a readable digest."""
    lines = [
        "📊 Top Match — Wekelijks Klantenoverzicht",
        f"   {datetime.utcnow().strftime('%d-%m-%Y')}",
        "=" * 50,
        "",
    ]
    for r in reports:
        status_icon = {"on_track": "🟢", "needs_attention": "🟡", "urgent": "🔴"}.get(
            r.get("status", ""), "⚪"
        )
        lines.append(f"{status_icon} {r['client_name']}")
        lines.append(f"   {r.get('summary', '')}")
        actions = r.get("suggested_actions", [])
        if actions:
            lines.append("   Acties:")
            for a in actions:
                lines.append(f"   • {a}")
        lines.append("")
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


def _generate_summary(
    claude: anthropic.Anthropic,
    client_name: str,
    pipeline_count: int,
    new_applications: int,
    active_vacancies: int,
    vacancy_titles: list[str],
) -> dict:
    prompt = SUMMARY_PROMPT.format(
        client_name=client_name,
        pipeline_count=pipeline_count,
        new_applications=new_applications,
        active_vacancies=active_vacancies,
        vacancy_titles=", ".join(vacancy_titles[:10]) or "geen",
    )
    message = claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(message.content[0].text)
    except json.JSONDecodeError:
        return {
            "summary": message.content[0].text,
            "status": "on_track",
            "suggested_actions": [],
        }
