# Top Match — Jaicob.ai Recruitment Automation

Automatiseringstoolkit voor Top Match, gebouwd op de [Jaicob.ai ATS API](https://developers.jaicob.ai/docs/getting-started) en Claude AI.

## Wat zit erin?

| # | Commando | Wat het doet |
|---|----------|-------------|
| 1 | `parse-cv` | CV uploaden, parsen via Jaicob, scoren tegen alle vacatures met AI |
| 2 | `match` | Semantische matching tussen alle kandidaten en vacatures |
| 3 | `create-vacancy` | Van een kort briefje naar een volledige vacaturetekst |
| 4 | `enrich-lead` | Lead verrijken + gepersonaliseerd outreach-bericht genereren |
| 5 | `client-reports` | Wekelijks overzicht per klant met pipeline-status |
| 6 | `stale-candidates` | Kandidaten vinden die te lang geen aandacht hebben gehad |

## Installatie

```bash
# Clone en installeer
git clone <repo-url>
cd Jaicob.
pip install -e .

# Configureer je API keys
cp .env.example .env
# Vul JAICOB_API_KEY en ANTHROPIC_API_KEY in
```

## Gebruik

```bash
# 1. CV parsen en matchen
topmatch parse-cv /pad/naar/cv.pdf
topmatch parse-cv /pad/naar/cv-map/ --auto-create --min-score 0.7

# 2. Alle kandidaten matchen tegen vacatures
topmatch match --min-score 0.6

# 3. Vacature aanmaken vanuit een briefje
topmatch create-vacancy "Sales manager B2B, 3+ jaar ervaring, regio Utrecht, fulltime, 4000-5500 bruto"
topmatch create-vacancy briefje.txt --publish

# 4. Lead verrijken
topmatch enrich-lead "uuid-van-de-lead"

# 5. Klantrapportages
topmatch client-reports

# 6. Vergeten kandidaten
topmatch stale-candidates --days 14
```

## Als Python library

```python
from topmatch.jaicob_client import JaicobClient
from topmatch.cv_parser import parse_and_score
from topmatch.matching import find_matches

with JaicobClient() as jaicob:
    # CV parsen en scoren
    results = parse_and_score("cv.pdf", jaicob=jaicob)

    # Matching draaien
    matches = find_matches(jaicob=jaicob)
```

## n8n Workflows

Alle 6 automations zijn ook beschikbaar als kant-en-klare n8n workflows die je direct kunt importeren.

### Overzicht

| # | Workflow | Trigger | Slack kanaal |
|---|----------|---------|-------------|
| 1 | **CV Parsing Pipeline** | Webhook (`POST /topmatch-cv-upload`) | `#recruitment` |
| 2 | **Nightly Matching** | Schedule (ma-vr 06:00) | `#recruitment` |
| 3 | **Vacancy from Brief** | Webhook (`POST /topmatch-vacancy-brief`) | `#recruitment` |
| 4 | **Lead Enrichment** | Webhook (`POST /topmatch-enrich-lead`) | `#recruitment` |
| 5 | **Weekly Client Reports** | Schedule (ma 08:00) | `#management` |
| 6 | **Stale Candidates Monitor** | Schedule (ma-vr 09:00) | `#recruitment` |

### n8n Installatie

1. **Importeer workflows** — Ga naar n8n > Workflows > Import from File, selecteer de JSON uit `n8n-workflows/`
2. **Environment variables** — Stel in n8n in:
   - `JAICOB_API_KEY` — Je Jaicob API key
   - `ANTHROPIC_API_KEY` — Je Anthropic API key
3. **Slack credentials** — Koppel je Slack workspace in n8n
4. **Activeer** — Zet de workflows op actief

### Webhook endpoints gebruiken

```bash
# 1. CV uploaden en matchen
curl -X POST https://jouw-n8n.com/webhook/topmatch-cv-upload \
  -F "resume=@cv.pdf"

# 3. Vacature aanmaken vanuit een briefje
curl -X POST https://jouw-n8n.com/webhook/topmatch-vacancy-brief \
  -H "Content-Type: application/json" \
  -d '{"brief": "Sales manager B2B, 3+ jaar ervaring, regio Utrecht, fulltime"}'

# 4. Lead verrijken
curl -X POST https://jouw-n8n.com/webhook/topmatch-enrich-lead \
  -H "Content-Type: application/json" \
  -d '{"lead_id": "uuid-van-de-lead"}'
```

### Workflow architectuur

Elke workflow volgt hetzelfde patroon:

```
Trigger → Jaicob API (data ophalen) → Code (prompt bouwen) → Claude AI → Code (response parsen) → Actie (Slack/Jaicob)
```

- **Webhook workflows** (1, 3, 4): Worden getriggerd door een HTTP POST en geven een JSON response terug
- **Schedule workflows** (2, 5, 6): Draaien automatisch op vaste tijden en sturen Slack-notificaties

## Architectuur

```
topmatch/
├── config.py            # .env configuratie
├── jaicob_client.py     # Jaicob ATS API wrapper
├── cv_parser.py         # CV parsing + vacancy scoring
├── matching.py          # Kandidaat-vacature matching
├── vacancy_creator.py   # Vacature generatie vanuit brief
├── lead_enrichment.py   # Lead verrijking + outreach
├── reporting.py         # Klantrapportages
├── status_monitor.py    # Vergeten kandidaten alert
└── cli.py               # CLI entry point

n8n-workflows/
├── 1-cv-parsing-pipeline.json
├── 2-nightly-matching.json
├── 3-vacancy-from-brief.json
├── 4-lead-enrichment.json
├── 5-weekly-client-reports.json
└── 6-stale-candidates-monitor.json
```

## API Keys

- **Jaicob API key**: Maak aan via [app.jaicob.ai/settings/integration/api-keys](https://app.jaicob.ai/settings/integration/api-keys)
- **Anthropic API key**: Maak aan via [console.anthropic.com](https://console.anthropic.com)
