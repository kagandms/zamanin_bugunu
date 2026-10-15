from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.dispatch_metadata import (
    format_dispatch, read_dispatch, reject_publication_dispatch, validate_analytics_dispatch,
)
from src.data.models import SlotAttempt
from src.data.publication_slots import SlotStore
from src.publication_run import PublicationRun, execute_publication_run
from test_publication_slots import database, SlotDatabase, MORNING, IDENTITY


def external_environment(moment: datetime = MORNING, kind: str = "publication") -> dict[str, str]:
    """Return a non-secret external occurrence with consistent timestamp/correlation."""
    return {"ZAMANIN_TRIGGER_SOURCE": "cloudflare",
        "ZAMANIN_CORRELATION_ID": f"cf-{kind}-{int(moment.timestamp() * 1000)}",
        "ZAMANIN_INTENDED_AT": moment.isoformat().replace("+00:00", "Z"),
        "ZAMANIN_INTENDED_DAY": moment.astimezone(timezone(timedelta(hours=3))).date().isoformat() if kind == "publication" else "",
        "ZAMANIN_INTENDED_SLOT": ("morning" if moment.hour < 12 else "evening") if kind == "publication" else ""}


def test_legacy_empty_manual_and_native_inputs_keep_real_time_policy() -> None:
    metadata = read_dispatch({})

    assert reject_publication_dispatch(metadata, MORNING) is None
    assert read_dispatch({"ZAMANIN_TRIGGER_SOURCE": "manual"}) == metadata


@pytest.mark.parametrize("key,value", [
    ("ZAMANIN_TRIGGER_SOURCE", "evil"), ("ZAMANIN_CORRELATION_ID", "secret\nurl"),
    ("ZAMANIN_INTENDED_AT", "2026-10-14T06:17:00"), ("ZAMANIN_INTENDED_DAY", "2026-10-15"),
    ("ZAMANIN_INTENDED_SLOT", "arbitrary"), ("ZAMANIN_INTENDED_AT", "2026-99-99T06:17:00Z"),
])
def test_invalid_metadata_is_rejected_without_echoing_raw_values(key: str, value: str) -> None:
    environment = external_environment() | {key: value}

    metadata = read_dispatch(environment)

    assert reject_publication_dispatch(metadata, MORNING) == "skip_invalid_dispatch"
    assert metadata.correlation_id == ""
    assert 'secret' not in format_dispatch(metadata)


@pytest.mark.parametrize("offset,expected", [
    (timedelta(minutes=1), None), (timedelta(hours=11), "skip_slot_mismatch"),
    (timedelta(days=1), "skip_slot_mismatch"), (timedelta(minutes=-1), "skip_stale_dispatch"),
    (timedelta(hours=1, minutes=50), "skip_slot_mismatch"),
])
def test_external_dispatch_never_claims_another_window(offset: timedelta, expected: str | None) -> None:
    metadata = read_dispatch(external_environment())

    assert reject_publication_dispatch(metadata, MORNING + offset) == expected


def test_analytics_rejects_publication_metadata_and_never_selects_slot() -> None:
    metadata = read_dispatch(external_environment(kind="analytics"))

    validate_analytics_dispatch(metadata, MORNING)
    assert metadata.intended_slot == ""
    with pytest.raises(ValueError):
        validate_analytics_dispatch(read_dispatch(external_environment()), MORNING)
    assert reject_publication_dispatch(metadata, MORNING) == "skip_invalid_dispatch"


@pytest.mark.asyncio
async def test_native_external_and_duplicate_correlation_claim_only_one_root(database: SlotDatabase) -> None:
    slots = SlotStore(database.factory)
    external = replace(IDENTITY, event="workflow_dispatch", dispatch=read_dispatch(external_environment()))

    decisions = await asyncio.gather(slots.claim(MORNING, IDENTITY), slots.claim(MORNING, external),
        slots.claim(MORNING, external))

    assert sum(item.status == "claimed" for item in decisions) == 1
    async with database.factory() as session:
        attempts = (await session.scalars(select(SlotAttempt).where(SlotAttempt.correlation_id.is_not(None)))).all()
        assert len(attempts) == 2
        assert all(item.intended_slot == "morning" for item in attempts)


@pytest.mark.asyncio
@pytest.mark.parametrize("observed", [MORNING + timedelta(days=1), MORNING.replace(hour=17)])
async def test_stale_external_run_has_no_preparation_or_social_boundary(database: SlotDatabase, observed: datetime) -> None:
    identity = replace(IDENTITY, event="workflow_dispatch", dispatch=read_dispatch(external_environment()))
    publish = AsyncMock(side_effect=AssertionError("must not prepare/auth/publish"))
    checkpoint = SimpleNamespace(save=AsyncMock(return_value="verified-mock-result"))

    outcome = await execute_publication_run(PublicationRun(SlotStore(database.factory), checkpoint,
        lambda: observed, identity, publish))

    assert outcome == "skip_slot_mismatch"
    publish.assert_not_awaited()
    async with database.factory() as session:
        attempt = await session.scalar(select(SlotAttempt))
        assert attempt.correlation_id == identity.dispatch.correlation_id
        assert attempt.persistence_status == "result_verified"


def test_workflow_inputs_are_env_values_and_keep_common_lock_and_checkout_order() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("schedule.yml", "analytics.yml"):
        workflow = (root / '.github/workflows' / name).read_text()
        assert 'group: zamanin-bugunu-db' in workflow and 'queue: max' in workflow
        assert 'cancel-in-progress: false' in workflow
        assert workflow.index('git switch --detach origin/main') < workflow.index('run: python -m src.')
        assert 'ZAMANIN_CORRELATION_ID: ${{ inputs.correlation_id' in workflow
        assert 'run: ${{' not in workflow
    assert 'TELEGRAM_' not in (root / '.github/workflows/analytics.yml').read_text()


@pytest.mark.asyncio
async def test_readonly_observer_separates_accepted_run_start_and_unknown_publication(tmp_path: Path) -> None:
    import json
    import httpx
    from src.dispatch_observation import ObservationRequest, observe_dispatch
    correlation = external_environment()["ZAMANIN_CORRELATION_ID"]
    receipt = tmp_path / 'receipt.json'
    receipt.write_text(json.dumps({'stage':'dispatch_result', 'correlation_id':correlation,
        'status':'accepted', 'httpStatus':200}))
    requests = []
    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith('/jobs'):
            return httpx.Response(200, json={'jobs':[{'id':8,'started_at':'2026-10-14T06:20:00Z','status':'in_progress'}]})
        return httpx.Response(200, json={'workflow_runs':[{'id':7, 'head_branch':'main',
            'event':'workflow_dispatch', 'display_title':f'Zamanın Bugünü publication slots | {correlation}',
            'head_sha':'source-sha'}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as client:
        result = await observe_dispatch(ObservationRequest(correlation,'schedule.yml',receipt=receipt),client)

    assert all(request.method == 'GET' for request in requests)
    assert result['dispatch_accepted'] == 'observed_in_supplied_receipt'
    assert result['correlated_run_observed'] is True
    assert result['runs'][0]['job_started'] is True
    assert result['db_evidence']['status'] == 'not_supplied'


@pytest.mark.asyncio
async def test_readonly_observer_rejects_arbitrary_target_before_any_request() -> None:
    import httpx
    from src.dispatch_observation import ObservationRequest, observe_dispatch
    def deny(request: httpx.Request) -> httpx.Response:
        raise AssertionError('invalid target must not call API')
    async with httpx.AsyncClient(transport=httpx.MockTransport(deny)) as client:
        with pytest.raises(ValueError):
            await observe_dispatch(ObservationRequest('unsafe','evil.yml'),client)


@pytest.mark.asyncio
async def test_observer_reads_correlation_without_mutating_db(database: SlotDatabase) -> None:
    import hashlib
    from src.dispatch_observation import ObservationRequest, read_database_evidence
    identity = replace(IDENTITY, event='workflow_dispatch',dispatch=read_dispatch(external_environment()))
    await SlotStore(database.factory).claim(MORNING,identity)
    previous = hashlib.sha256(database.path.read_bytes()).hexdigest()

    result = read_database_evidence(ObservationRequest(identity.dispatch.correlation_id,'schedule.yml',database.path))

    assert result['slot_claimed'] is True
    assert result['reservation_checkpoint_verified'] is False
    assert result['main_published'] is False
    assert hashlib.sha256(database.path.read_bytes()).hexdigest() == previous


def test_native_context_is_named_native_and_correlation_must_match_epoch() -> None:
    metadata = read_dispatch({'GITHUB_EVENT_NAME':'schedule'})

    assert metadata.trigger_source == 'native'
    assert reject_publication_dispatch(metadata, MORNING) is None
    corrupted = external_environment() | {'ZAMANIN_CORRELATION_ID':'cf-publication-1791958620001'}
    assert read_dispatch(corrupted).error == 'skip_invalid_dispatch'


@pytest.mark.asyncio
async def test_external_duplicate_replay_publishes_one_root_with_checkpoint_before_effect(database: SlotDatabase) -> None:
    from src.data.models import EventReservation, PublicationPartData, PublicationPart
    from src.data.repository import HistoryRepository
    from src.publication_gate import PublicationGate
    identity = replace(IDENTITY,event='workflow_dispatch',dispatch=read_dispatch(external_environment()))
    sequence: list[str] = []
    async def save(phase: str) -> str:
        sequence.append(phase)
        return 'verified-sha'
    async def publish(gate: PublicationGate) -> None:
        async with database.factory() as session:
            history = HistoryRepository(session)
            event_id = await history.reserve_event(EventReservation('one external event'))
            publication_id = await history.reserve_publication(event_id,'threads')
            assert await gate.authorize(event_id)
            sequence.append('social_auth_publish')
            await history.record_part(PublicationPartData(publication_id,'threads','external-root',0,
                None,'fixture','TEXT',True,MORNING,'fixture'))
            await history.finish_publication(publication_id,'published')
    context = PublicationRun(SlotStore(database.factory),SimpleNamespace(save=save),lambda:MORNING,identity,publish)

    await execute_publication_run(context)
    await execute_publication_run(context)

    assert sequence.count('social_auth_publish') == 1
    assert sequence.index('reservation') < sequence.index('social_auth_publish')
    async with database.factory() as session:
        assert len((await session.scalars(select(PublicationPart))).all()) == 1
