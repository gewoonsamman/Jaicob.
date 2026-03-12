"""
CLI entry point for the Top Match automation toolkit.

Usage:
    python -m topmatch <command> [options]

Commands:
    parse-cv <file_or_folder>     Parse CVs and score against vacancies
    match                         Find overlooked candidate-vacancy matches
    create-vacancy <brief>        Create a vacancy from a short brief
    enrich-lead <lead_id>         Enrich a lead and generate outreach
    client-reports                Generate weekly client reports
    stale-candidates [--days N]   Find candidates not updated recently
"""

from __future__ import annotations

import argparse
import json
import sys

from topmatch.jaicob_client import JaicobClient


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="topmatch",
        description="Top Match recruitment automation powered by Jaicob.ai",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # 1. CV parsing
    p_cv = sub.add_parser("parse-cv", help="Parse CVs and match to vacancies")
    p_cv.add_argument("path", help="Path to a CV file or folder of CVs")
    p_cv.add_argument("--min-score", type=float, default=0.6)
    p_cv.add_argument("--auto-create", action="store_true")

    # 2. Matching
    p_match = sub.add_parser("match", help="Find candidate-vacancy matches")
    p_match.add_argument("--min-score", type=float, default=0.6)

    # 3. Vacancy creation
    p_vac = sub.add_parser("create-vacancy", help="Create vacancy from brief")
    p_vac.add_argument("brief", help="Short vacancy description or path to .txt file")
    p_vac.add_argument("--publish", action="store_true", help="Push to Jaicob immediately")

    # 4. Lead enrichment
    p_lead = sub.add_parser("enrich-lead", help="Enrich a lead and generate outreach")
    p_lead.add_argument("lead_id", help="Jaicob lead UUID")

    # 5. Client reports
    sub.add_parser("client-reports", help="Generate weekly client reports")

    # 6. Stale candidates
    p_stale = sub.add_parser("stale-candidates", help="Find forgotten candidates")
    p_stale.add_argument("--days", type=int, default=7)

    args = parser.parse_args()

    with JaicobClient() as jaicob:
        if args.command == "parse-cv":
            _cmd_parse_cv(args, jaicob)
        elif args.command == "match":
            _cmd_match(args, jaicob)
        elif args.command == "create-vacancy":
            _cmd_create_vacancy(args, jaicob)
        elif args.command == "enrich-lead":
            _cmd_enrich_lead(args, jaicob)
        elif args.command == "client-reports":
            _cmd_client_reports(jaicob)
        elif args.command == "stale-candidates":
            _cmd_stale_candidates(args, jaicob)


def _cmd_parse_cv(args: argparse.Namespace, jaicob: JaicobClient) -> None:
    from pathlib import Path
    from topmatch.cv_parser import parse_and_score, watch_folder

    path = Path(args.path)
    if path.is_dir():
        watch_folder(path, jaicob=jaicob, min_score=args.min_score, auto_create=args.auto_create)
    else:
        results = parse_and_score(
            path, jaicob=jaicob, min_score=args.min_score, auto_create=args.auto_create
        )
        print(json.dumps(results, indent=2, ensure_ascii=False))


def _cmd_match(args: argparse.Namespace, jaicob: JaicobClient) -> None:
    from topmatch.matching import find_matches, generate_digest

    matches = find_matches(min_score=args.min_score, jaicob=jaicob)
    print(generate_digest(matches))


def _cmd_create_vacancy(args: argparse.Namespace, jaicob: JaicobClient) -> None:
    from pathlib import Path
    from topmatch.vacancy_creator import create_vacancy_from_brief

    brief = args.brief
    if Path(brief).is_file():
        brief = Path(brief).read_text()

    result = create_vacancy_from_brief(brief, jaicob=jaicob, publish=args.publish)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result.get("id"):
        print(f"\nVacature aangemaakt in Jaicob: {result['id']}")


def _cmd_enrich_lead(args: argparse.Namespace, jaicob: JaicobClient) -> None:
    from topmatch.lead_enrichment import enrich_lead

    result = enrich_lead(args.lead_id, jaicob=jaicob)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _cmd_client_reports(jaicob: JaicobClient) -> None:
    from topmatch.reporting import generate_client_reports, format_reports

    reports = generate_client_reports(jaicob=jaicob)
    print(format_reports(reports))


def _cmd_stale_candidates(args: argparse.Namespace, jaicob: JaicobClient) -> None:
    from topmatch.status_monitor import find_stale_candidates, format_stale_report

    stale = find_stale_candidates(stale_days=args.days, jaicob=jaicob)
    print(format_stale_report(stale))


if __name__ == "__main__":
    main()
