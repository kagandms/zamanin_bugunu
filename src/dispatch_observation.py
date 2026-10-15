from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

GITHUB_ACTIONS_URL = "https://api.github.com/repos/kagandms/zamanin_bugunu/actions"


@dataclass(frozen=True)
class ObservationRequest:
    """Read-only inputs; database must be a provenance-verified temporary copy."""
    correlation_id: str
    workflow: str
    database: Path | None = None
    receipt: Path | None = None


def validate_request(request: ObservationRequest) -> None:
    """Validate allowlisted target and safe correlation. Raises ValueError on invalid inputs."""
    if request.workflow not in ("schedule.yml", "analytics.yml"):
        raise ValueError("Unrecognized workflow")
    expected = "publication" if request.workflow == "schedule.yml" else "analytics"
    if not re.fullmatch(rf"cf-{expected}-\d{{13}}", request.correlation_id):
        raise ValueError("Invalid correlation ID")


async def observe_dispatch(request: ObservationRequest, client: httpx.AsyncClient) -> dict[str, object]:
    """GET bounded run/job pages and read an optional DB copy; never dispatch, sync, or migrate.

    Args: request: fixed-target correlation and evidence paths; client: read-only HTTP edge.
    Returns: separate acceptance, observed run/start and DB stages. Raises: HTTP/IO/validation errors.
    """
    validate_request(request)
    response = await client.get(f"{GITHUB_ACTIONS_URL}/workflows/{request.workflow}/runs",
        params={"event": "workflow_dispatch", "branch": "main", "per_page": 100})
    response.raise_for_status()
    runs = [run for run in response.json().get("workflow_runs", [])
        if run.get("display_title") == f"{_workflow_name(request.workflow)} | {request.correlation_id}"
        and run.get("event") == "workflow_dispatch" and run.get("head_branch") == "main"]
    observed = await asyncio.gather(*(_observe_run(client, run) for run in runs))
    return {"correlation_id": request.correlation_id,
        "dispatch_accepted": _accepted_receipt(request), "correlated_run_observed": bool(runs),
        "runs": observed, "db_evidence": read_database_evidence(request),
        "coverage": "latest 100 workflow_dispatch runs only; absent evidence remains unknown",
        "provenance": "caller must verify DB checkpoint commit and subsequent natural checkout separately"}


def _workflow_name(workflow: str) -> str:
    return "Zamanın Bugünü publication slots" if workflow == "schedule.yml" else "Zamanın Bugünü analytics only"


async def _observe_run(client: httpx.AsyncClient, run: dict[str, object]) -> dict[str, object]:
    run_id = run.get("id")
    if not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("Invalid GitHub run ID")
    response = await client.get(f"{GITHUB_ACTIONS_URL}/runs/{run_id}/jobs", params={"per_page": 100})
    response.raise_for_status()
    jobs = [{key: job.get(key) for key in ("id", "started_at", "completed_at", "status", "conclusion")}
        for job in response.json().get("jobs", [])]
    return {"run_id": run_id, "workflow_source_sha": run.get("head_sha"),
        "created_at": run.get("created_at"), "run_started_at": run.get("run_started_at"),
        "job_started": any(job.get("started_at") for job in jobs), "jobs": jobs,
        "checkout_sha": "unknown_until_sanitized_job_log_checked"}


def _accepted_receipt(request: ObservationRequest) -> str:
    if request.receipt is None:
        return "unknown"
    receipt = json.loads(request.receipt.read_text())
    matches = (receipt.get("correlation_id") == request.correlation_id
        and receipt.get("stage") == "dispatch_result" and receipt.get("status") == "accepted"
        and receipt.get("httpStatus") in (200, 204))
    return "observed_in_supplied_receipt" if matches else "unknown"


def read_database_evidence(request: ObservationRequest) -> dict[str, object]:
    """Read only the supplied immutable DB copy, keeping unobserved publication stages unknown."""
    if request.database is None:
        return {"status": "not_supplied"}
    with sqlite3.connect(request.database.resolve().as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        attempts = [dict(row) for row in connection.execute(
            "SELECT * FROM slot_attempts WHERE correlation_id = ?", (request.correlation_id,))]
        slots = [dict(row) for row in connection.execute(
            "SELECT DISTINCT s.* FROM publication_slots s JOIN slot_attempts a ON a.slot_id=s.id "
            "WHERE a.correlation_id=?", (request.correlation_id,))]
        parts = [dict(row) for row in connection.execute(
            "SELECT pp.* FROM publication_parts pp JOIN platform_publications p ON p.id=pp.publication_id "
            "WHERE p.event_id IN (SELECT s.event_id FROM publication_slots s JOIN slot_attempts a "
            "ON a.slot_id=s.id WHERE a.correlation_id=?)", (request.correlation_id,))]
    has_claim = any(attempt["decision"] in ("claimed", "published", "partial", "failed", "reconciliation_required")
        for attempt in attempts)
    return {"slot_claimed": has_claim if attempts else "unknown",
        "reservation_checkpoint_verified": has_claim and any(slot["reservation_commit_sha"] for slot in slots) if attempts else "unknown",
        "main_published": has_claim and any(part["is_main"] and part["status"] == "published" for part in parts) if attempts else "unknown",
        "result_persisted_receipt": any(attempt["persistence_status"] == "result_verified" for attempt in attempts) if attempts else "unknown",
        "attempts": attempts, "slots": slots, "parts": parts}


async def _run_observer(request: ObservationRequest) -> dict[str, object]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
    token = os.getenv("GITHUB_OBSERVER_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(headers=headers, timeout=10, follow_redirects=False) as client:
        return await observe_dispatch(request, client)


def run_cli() -> int:
    """Run the bounded GET-only observer; stdout JSON, sanitized failure type on stderr."""
    parser = argparse.ArgumentParser(description="GET-only external dispatch evidence observer")
    parser.add_argument("--correlation", required=True)
    parser.add_argument("--workflow", choices=("schedule.yml", "analytics.yml"), required=True)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    request = ObservationRequest(args.correlation, args.workflow, args.db, args.receipt)
    try:
        sys.stdout.write(json.dumps(asyncio.run(_run_observer(request)), ensure_ascii=False, indent=2) + "\n")
        return 0
    except (ValueError, OSError, sqlite3.Error, httpx.HTTPError) as error:
        logging.error("Read-only observation failed (%s)", type(error).__name__)
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(run_cli())
