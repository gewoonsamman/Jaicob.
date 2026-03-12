"""Jaicob ATS API client wrapper."""

from __future__ import annotations

import httpx
from pathlib import Path
from typing import Any

from topmatch.config import JAICOB_API_KEY, JAICOB_BASE_URL, DEFAULT_LANGUAGE


class JaicobClient:
    """Thin wrapper around the Jaicob REST API."""

    def __init__(
        self,
        api_key: str = JAICOB_API_KEY,
        base_url: str = JAICOB_BASE_URL,
        language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "x-api-key": api_key,
            "x-language": language,
            "Content-Type": "application/json",
        }
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> JaicobClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ── Candidates ──────────────────────────────────────────────

    def list_candidates(
        self, page: int = 1, take: int = 50, **filters: Any
    ) -> dict:
        params: dict[str, Any] = {"page": page, "take": take, **filters}
        r = self._client.get("/candidates/public", params=params)
        r.raise_for_status()
        return r.json()

    def get_candidate(self, candidate_id: str) -> dict:
        r = self._client.get(f"/candidates/public/{candidate_id}")
        r.raise_for_status()
        return r.json()

    def create_candidate(self, data: dict) -> dict:
        r = self._client.post("/candidates", json=data)
        r.raise_for_status()
        return r.json()

    def update_candidate(self, candidate_id: str, data: dict) -> dict:
        r = self._client.put(f"/candidates/{candidate_id}", json=data)
        r.raise_for_status()
        return r.json()

    # ── Vacancies ───────────────────────────────────────────────

    def list_vacancies(
        self, page: int = 1, take: int = 50, **filters: Any
    ) -> dict:
        params: dict[str, Any] = {"page": page, "take": take, **filters}
        r = self._client.get("/vacancies/public", params=params)
        r.raise_for_status()
        return r.json()

    def get_vacancy(self, vacancy_id: str) -> dict:
        r = self._client.get(f"/vacancies/public/{vacancy_id}")
        r.raise_for_status()
        return r.json()

    def create_vacancy(self, data: dict) -> dict:
        r = self._client.post("/vacancies", json=data)
        r.raise_for_status()
        return r.json()

    def update_vacancy(self, vacancy_id: str, data: dict) -> dict:
        r = self._client.put(f"/vacancies/{vacancy_id}", json=data)
        r.raise_for_status()
        return r.json()

    # ── Applications ────────────────────────────────────────────

    def list_applications(
        self, page: int = 1, take: int = 50, **filters: Any
    ) -> dict:
        params: dict[str, Any] = {"page": page, "take": take, **filters}
        r = self._client.get("/applications/public", params=params)
        r.raise_for_status()
        return r.json()

    def create_application(self, vacancy_id: str, data: dict) -> dict:
        r = self._client.post(f"/applications/{vacancy_id}", json=data)
        r.raise_for_status()
        return r.json()

    # ── Resume parsing ──────────────────────────────────────────

    def parse_resume(self, file_path: str | Path) -> dict:
        """Upload a CV/resume file and get back structured candidate data."""
        path = Path(file_path)
        # Resume endpoint uses multipart/form-data, so drop JSON content-type
        headers = {k: v for k, v in self._headers.items() if k != "Content-Type"}
        with open(path, "rb") as f:
            r = self._client.post(
                "/file/resume",
                files={"resume": (path.name, f)},
                headers=headers,
            )
        r.raise_for_status()
        return r.json()

    # ── Clients ─────────────────────────────────────────────────

    def list_clients(
        self, page: int = 1, take: int = 50, query: str | None = None
    ) -> dict:
        params: dict[str, Any] = {"page": page, "take": take}
        if query:
            params["query"] = query
        r = self._client.get("/clients/public", params=params)
        r.raise_for_status()
        return r.json()

    def get_client(self, client_id: str) -> dict:
        r = self._client.get(f"/clients/public/{client_id}")
        r.raise_for_status()
        return r.json()

    def create_client(self, data: dict) -> dict:
        r = self._client.post("/clients", json=data)
        r.raise_for_status()
        return r.json()

    # ── Leads ───────────────────────────────────────────────────

    def get_lead(self, lead_id: str) -> dict:
        r = self._client.get(f"/leads/public/{lead_id}")
        r.raise_for_status()
        return r.json()

    def create_lead(self, data: dict) -> dict:
        r = self._client.post("/leads", json=data)
        r.raise_for_status()
        return r.json()

    # ── Taxonomies (for vacancy creation) ───────────────────────

    def list_industries(self) -> list[dict]:
        r = self._client.get("/industries")
        r.raise_for_status()
        return r.json()

    def list_education_levels(self) -> list[dict]:
        r = self._client.get("/educations")
        r.raise_for_status()
        return r.json()

    def list_job_categories(self) -> list[dict]:
        r = self._client.get("/job-categories")
        r.raise_for_status()
        return r.json()

    def list_seniorities(self) -> list[dict]:
        r = self._client.get("/seniorities")
        r.raise_for_status()
        return r.json()

    # ── Locations ───────────────────────────────────────────────

    def list_locations(self, page: int = 1, take: int = 50) -> dict:
        r = self._client.get(
            "/locations/public", params={"page": page, "take": take}
        )
        r.raise_for_status()
        return r.json()
