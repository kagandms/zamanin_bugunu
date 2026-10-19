from __future__ import annotations

from datetime import datetime

import pytest
import httpx

from src.services.content_guard import (
    EventRewriteRequest,
    get_source_fact_status,
    resolve_fact_profile,
    validate_event_content,
)
from src.services.threads_service import (
    ContainerReadiness,
    ThreadPublishCallbacks,
    ThreadsService,
    _safe_graph_error_details,
)


KARS_EVENT = "TBMM Hükûmeti, Azerbaycan, Ermenistan ve Gürcistan ile Kars Antlaşması'nı imzaladı."


def test_kars_profile_rejects_moscow_signing_and_national_war_scope() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Kars Antlaşması Moskova'da imzalandı; Türk Kurtuluş Savaşı sona erdi."],
        request,
        profile,
    )

    assert reasons == ("unsupported_signing_location", "unsupported_war_scope")


@pytest.mark.parametrize("sentence", [
    "TBMM Hükûmeti Kars Antlaşması'nı Moskova'da imzaladı.",
    "TBMM Hükûmeti Kars Antlaşması’nı Moskova’da imzaladı.",
    "Kars Antlaşması Moskova'da imzalandı.",
    "Kars Antlaşması Moskova’da imzalandı.",
])
def test_kars_profile_rejects_active_and_passive_moscow_signing(sentence: str) -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content([sentence], request, profile)

    assert "unsupported_signing_location" in reasons


def test_irrelevant_negation_does_not_cancel_moscow_signing_claim() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Kars Antlaşması Moskova’da imzalandı; bunun yanlış bir karar olmadığı söylendi."],
        request,
        profile,
    )

    assert "unsupported_signing_location" in reasons


@pytest.mark.parametrize("sentence", [
    "Kars Antlaşması Moskova'da değil, Kars'ta imzalandı.",
    "Kars Antlaşması Moskova’da değil Kars’ta imzalandı.",
    "Kars Antlaşması Moskova'da imzalanmadı; Kars'ta imzalandı.",
])
def test_local_moscow_denial_and_kars_correction_are_accepted(sentence: str) -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content([sentence], request, profile)

    assert "unsupported_signing_location" not in reasons


def test_kars_profile_rejects_unsupported_georgianized_border_claim() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(["Gürcileşen sınırlar kalemle çizildi."], request, profile)

    assert reasons == ("unsupported_border_claim",)


def test_published_kars_hook_is_rejected_as_a_negative_fixture() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)
    published_hook = (
        "Kurtuluş Savaşı hâlâ devam ediyormuş gibi gösteriliyordu… ama aslında, "
        "Ankara'daki yeni hükümet, Gürcileşen sınırları kalemle çiziyordu!"
    )

    reasons = validate_event_content([published_hook], request, profile)

    assert reasons == ("unsupported_border_claim", "unsupported_war_scope")


def test_kars_profile_accepts_supported_signing_and_front_scope() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Kars Muahedenâmesi 13 Ekim 1921'de Kars'ta imzalandı."],
        request,
        profile,
    )

    assert reasons == ()


def test_source_event_can_scope_war_outcome_to_the_eastern_front() -> None:
    request = EventRewriteRequest(
        "Kars Antlaşması 1921'de imzalandı. Doğu Cephesi’nde Türk Kurtuluş Savaşı sona erdi.",
        "13.10.1921",
        "1921",
    )
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Doğu Cephesi’nde Türk Kurtuluş Savaşı sona erdi."], request, profile
    )

    assert reasons == ()


def test_unrelated_negation_does_not_cancel_national_war_claim() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Türk Kurtuluş Savaşı sona erdi; bunun yanlış bir karar olmadığı söylendi."],
        request,
        profile,
    )

    assert reasons == ("unsupported_war_scope",)


def test_supported_1922_front_context_is_accepted_but_unrelated_year_is_rejected() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    supported = validate_event_content(
        ["Batı Cephesi’ndeki mücadele Eylül 1922’ye kadar sürdü."], request, profile
    )
    unsupported = validate_event_content(
        ["Bu karar 1922 yılında yeni bir dönemi başlattı."], request, profile
    )

    assert supported == ()
    assert unsupported == ("unsupported_year",)


def test_unprofiled_event_source_facts_are_explicitly_not_checked() -> None:
    request = EventRewriteRequest("Moskova Antlaşması imzalandı.", "16.03.1921", "1921")
    profile = resolve_fact_profile(request)

    assert profile is None
    assert get_source_fact_status(profile) == "not_checked"


def test_moscow_is_not_a_global_banned_word() -> None:
    request = EventRewriteRequest("Moskova Antlaşması imzalandı.", "16.03.1921", "1921")
    profile = resolve_fact_profile(request)

    assert profile is None
    assert validate_event_content(["Moskova Antlaşması imzalandı."], request, profile) == ()


@pytest.mark.asyncio
async def test_invalid_kars_generation_uses_curated_source_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    from src.services.ai_service import AIService

    monkeypatch.setattr("src.services.ai_service.settings", Settings(
        OPENROUTER_API_KEY="mock-key", MAX_THREAD_LENGTH=500,
    ))
    service = AIService()
    service.rewrite_event = _invalid_kars_generation
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921", "TBMM", "https://example.test/tbmm")

    parts, _, _ = await service.rewrite_event_safe(request)

    combined_text = "\n".join(parts)
    assert "Moskova'da imzalandı" not in combined_text
    assert "Türk Kurtuluş Savaşı sona erdi" not in combined_text
    assert "Kars'ta imzalandı" in combined_text
    assert "Batı Cephesi" in combined_text
    assert service.prompt_version == "event-rewrite-v4+fact-guard-v4"
    assert service.last_generation_type == "source_fallback:unsupported_signing_location,unsupported_war_scope"
    assert service.last_source_id == "ttk-library-541556+ttk-istiklal-harbi"
    assert "kutuphane.ttk.gov.tr" in service.last_source_url
    assert validate_event_content(parts, request, resolve_fact_profile(request)) == ()
    assert service.last_source_fact_status == "checked_scoped"
    assert service.last_language_format_status == "fallback_template"


async def _invalid_kars_generation(request: EventRewriteRequest) -> tuple[list[str], list[str], None]:
    return ["Kars Antlaşması Moskova'da imzalandı; Türk Kurtuluş Savaşı sona erdi."], [], None


@pytest.mark.asyncio
async def test_model_guard_tries_two_candidates_then_uses_source_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    from src.services.ai_service import AIService

    settings = Settings(
        OPENROUTER_API_KEY="mock-key", AI_MODEL="first-model", BACKUP_MODEL="second-model",
        TERTIARY_MODEL="third-model", QUATERNARY_MODEL="fourth-model", LAST_RESORT_MODEL="fifth-model",
    )
    monkeypatch.setattr("src.services.ai_service.settings", settings)
    requests: list[dict[str, object]] = []

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "model": "mock-model",
                "choices": [{"message": {"content": (
                    "🕊️ Tarihte Bugün (13.10.1921)\nKars Antlaşması Moskova'da imzalandı.\n"
                    "#tarih #tarihteneoldu\n---\nTürk Kurtuluş Savaşı sona erdi."
                )}}],
            }

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            requests.append(kwargs["json"])
            return Response()

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921", "TBMM", "https://example.test/tbmm")

    parts, _, _ = await AIService().rewrite_event_safe(request)

    assert len(requests) == 2
    assert "Kurtuluş Savaşı sona erdi" not in "\n".join(parts)
    assert "Doğu Cephesi'ndeki sonuç" not in requests[0]["messages"][0]["content"]
    assert "Batı Cephesi'ndeki mücadelenin Eylül 1922'ye kadar sürdüğünü" in requests[0]["messages"][0]["content"]


@pytest.mark.asyncio
async def test_unprofiled_ai_metadata_does_not_claim_source_facts_were_checked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings
    from src.services.ai_service import AIService

    monkeypatch.setattr("src.services.ai_service.settings", Settings(
        OPENROUTER_API_KEY="mock-key", AI_MODEL="mock-model", BACKUP_MODEL="backup-model",
        LAST_RESORT_MODEL="last-model",
    ))

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "model": "mock-model",
                "choices": [{"message": {"content": (
                    "🕊️ Tarihte Bugün (16.03.1921)\nBugün önemli bir olay yaşandı.\n"
                    "---\nBu olay Türkiye ve dünya tarihinde iz bıraktı."
                )}}],
            }

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    service = AIService()

    await service.rewrite_event(EventRewriteRequest("Moskova Antlaşması imzalandı.", "16.03.1921", "1921"))

    assert service.last_generation_type == "ai_language_format_only"
    assert service.last_language_format_status == "passed"
    assert service.last_source_fact_status == "not_checked"


def test_kars_profile_allows_moscow_as_a_distinct_treaty_reference() -> None:
    request = EventRewriteRequest(KARS_EVENT, "13.10.1921", "1921")
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Kars Antlaşması Kars'ta imzalandı; Moskova Antlaşması daha önceki bir düzenlemeydi."],
        request,
        profile,
    )

    assert reasons == ()


def test_safe_graph_error_details_keep_diagnostic_fields_and_remove_secrets() -> None:
    class Response:
        status_code = 400
        headers = {"x-fb-trace-id": "trace-123"}

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "error": {
                    "type": "OAuthException",
                    "code": 100,
                    "error_subcode": 33,
                    "message": "Invalid token access_token=secret-token https://example.test/path?access_token=secret",
                }
            }

    details = _safe_graph_error_details(Response())

    assert "OAuthException" in details
    assert "100" in details and "33" in details and "trace-123" in details
    assert "secret-token" not in details and "example.test" not in details


@pytest.mark.asyncio
async def test_container_readiness_polls_processing_until_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    states = iter(["IN_PROGRESS", "FINISHED"])
    sleeps: list[float] = []

    class Response:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"status": next(states)}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> Response:
            return Response()

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("src.services.threads_service.asyncio.sleep", sleep)

    readiness = await ThreadsService()._wait_for_container_status("container", max_timeout=6, poll_interval=3)

    assert readiness == ContainerReadiness("ready")
    assert sleeps == [3]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("container_status", "expected"),
    [
        ("ERROR", ContainerReadiness("error", "container_error:invalid_media")),
        ("EXPIRED", ContainerReadiness("expired", "container_expired")),
        ("PUBLISHED", ContainerReadiness("published", "container_already_published_unknown_id")),
    ],
)
async def test_container_terminal_states_are_returned_without_extra_polls(
    monkeypatch: pytest.MonkeyPatch,
    container_status: str,
    expected: ContainerReadiness,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    calls = 0

    class Response:
        status_code = 200

        def json(self) -> dict[str, str]:
            return {"status": container_status, "error_message": "invalid_media"}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> Response:
            nonlocal calls
            calls += 1
            return Response()

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    readiness = await ThreadsService()._wait_for_container_status("container")

    assert readiness == expected
    assert calls == 1


@pytest.mark.asyncio
async def test_image_rejection_text_fallback_waits_until_ready_before_publish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    state_by_container = {
        "image-container": iter(["FINISHED"]),
        "text-container": iter(["IN_PROGRESS", "FINISHED"]),
    }
    events: list[str] = []

    class Response:
        status_code = 200

        def __init__(self, status: str) -> None:
            self.status = status

        def json(self) -> dict[str, str]:
            return {"status": self.status}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: object) -> Response:
            container_id = url.split("/")[-1].split("?")[0]
            status = next(state_by_container[container_id])
            events.append(f"ready:{container_id}:{status}")
            return Response(status)

    async def create_container(payload: dict[str, str]) -> tuple[str, None]:
        container_id = "image-container" if payload["media_type"] == "IMAGE" else "text-container"
        events.append(f"create:{container_id}")
        return container_id, None

    publish_responses = iter([(None, False, "publish_rejected:http_400"), ("text-post", False, None)])

    async def publish(container_id: str) -> tuple[str | None, bool, str | None]:
        events.append(f"publish:{container_id}")
        return next(publish_responses)

    async def sleep(_: float) -> None:
        return None

    async def published_time(post_id: str, confirmed_at: datetime) -> tuple[datetime, str]:
        return confirmed_at, "client_observed"

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("src.services.threads_service.asyncio.sleep", sleep)
    service = ThreadsService()
    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_publish_container", publish)
    monkeypatch.setattr(service, "_get_published_at", published_time)

    result = await service.post_thread(["main"], "https://image.test/main.jpg")

    assert result.status == "published"
    assert result.main_post_id == "text-post"
    assert events == [
        "create:image-container", "ready:image-container:FINISHED", "publish:image-container",
        "create:text-container", "ready:text-container:IN_PROGRESS",
        "ready:text-container:FINISHED", "publish:text-container",
    ]


@pytest.mark.asyncio
async def test_image_rejection_text_fallback_terminal_error_never_publishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    service = ThreadsService()
    created: list[str] = []
    published: list[str] = []
    readiness_results = iter([
        ContainerReadiness("ready"),
        ContainerReadiness("error", "container_error: media_processing_failed"),
    ])

    async def create_container(payload: dict[str, str]) -> tuple[str, None]:
        container_id = "image-container" if payload["media_type"] == "IMAGE" else "text-container"
        created.append(container_id)
        return container_id, None

    async def wait_for_readiness(container_id: str) -> ContainerReadiness:
        return next(readiness_results)

    async def publish(container_id: str) -> tuple[str | None, bool, str | None]:
        published.append(container_id)
        return None, False, "publish_rejected:http_400"

    records = []

    async def persist(part: object) -> None:
        records.append(part)

    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_wait_for_container_status", wait_for_readiness)
    monkeypatch.setattr(service, "_publish_container", publish)

    result = await service.post_thread(
        ["main"], "https://image.test/main.jpg", ThreadPublishCallbacks(on_part_published=persist)
    )

    assert result.status == "failed"
    assert created == ["image-container", "text-container"]
    assert published == ["image-container"]
    assert records[0].status == "failed"


@pytest.mark.asyncio
async def test_uncertain_image_publish_does_not_create_text_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    service = ThreadsService()
    created: list[str] = []
    published: list[str] = []

    async def create_container(payload: dict[str, str]) -> tuple[str, None]:
        created.append(payload["media_type"])
        return "image-container", None

    async def wait_for_readiness(container_id: str) -> ContainerReadiness:
        return ContainerReadiness("ready")

    async def publish(container_id: str) -> tuple[str | None, bool, str | None]:
        published.append(container_id)
        return None, True, "publish_timeout_unknown"

    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_wait_for_container_status", wait_for_readiness)
    monkeypatch.setattr(service, "_publish_container", publish)

    result = await service.post_thread(["main"], "https://image.test/main.jpg")

    assert result.status == "unknown"
    assert created == ["IMAGE"]
    assert published == ["image-container"]


@pytest.mark.asyncio
async def test_container_polling_deadline_bounds_requests_and_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    current_time = [100.0]
    observed_timeouts: list[float] = []
    request_durations = iter([12.0, 9.0])

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"status": "IN_PROGRESS"}

    class Client:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout
            observed_timeouts.append(timeout)

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, *args: object, **kwargs: object) -> Response:
            duration = next(request_durations)
            current_time[0] += min(duration, self.timeout)
            if duration > self.timeout:
                raise httpx.ReadTimeout("simulated request deadline")
            return Response()

    async def sleep(duration: float) -> None:
        current_time[0] += duration

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)
    monkeypatch.setattr("src.services.threads_service.asyncio.sleep", sleep)
    service = ThreadsService()

    readiness = await service._wait_for_container_status(
        "container", max_timeout=20, poll_interval=3, monotonic=lambda: current_time[0]
    )

    assert readiness == ContainerReadiness("timeout", "container_status_timeout")
    assert observed_timeouts == [15.0, 5.0]
    assert current_time[0] - 100.0 <= 20.0


@pytest.mark.asyncio
async def test_publish_400_is_a_diagnostic_rejection_and_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    calls = 0

    class Response:
        status_code = 400
        headers = {"x-fb-trace-id": "trace-400"}

        @staticmethod
        def json() -> dict[str, object]:
            return {"error": {"type": "OAuthException", "code": 100, "message": "Invalid request"}}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> Response:
            nonlocal calls
            calls += 1
            return Response()

    monkeypatch.setattr("src.services.threads_service.httpx.AsyncClient", Client)

    post_id, is_uncertain, detail = await ThreadsService()._publish_container("container-id")

    assert post_id is None and not is_uncertain
    assert calls == 1
    assert '"code": 100' in detail
    assert "trace-400" in detail


@pytest.mark.asyncio
async def test_every_reply_container_is_ready_before_single_publish_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    service = ThreadsService()
    readiness_ids: list[str] = []
    publish_ids: list[str] = []
    operations: list[str] = []
    payloads: list[dict[str, str]] = []
    recorded = []

    async def create_container(payload: dict[str, str]) -> tuple[str, None]:
        container_id = f"container-{len(readiness_ids)}"
        payloads.append(payload)
        operations.append(f"create:{container_id}")
        return container_id, None

    async def wait_for_ready(container_id: str) -> ContainerReadiness:
        readiness_ids.append(container_id)
        operations.append(f"ready:{container_id}")
        return ContainerReadiness("ready")

    async def publish(container_id: str) -> tuple[str | None, bool, str | None]:
        publish_ids.append(container_id)
        operations.append(f"publish:{container_id}")
        if len(publish_ids) == 1:
            return "root-id", False, None
        return None, False, "publish_http_400"

    async def published_time(post_id: str, confirmed_at: datetime) -> tuple[datetime, str]:
        return confirmed_at, "client_observed"

    async def persist(part: object) -> None:
        recorded.append(part)

    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_wait_for_container_status", wait_for_ready)
    monkeypatch.setattr(service, "_publish_container", publish)
    monkeypatch.setattr(service, "_get_published_at", published_time)

    result = await service.post_thread(
        ["main", "reply"], "https://image.test/root.jpg", ThreadPublishCallbacks(on_part_published=persist)
    )

    assert result.status == "partial"
    assert readiness_ids == ["container-0", "container-1"]
    assert publish_ids == ["container-0", "container-1"]
    assert payloads[0]["media_type"] == "IMAGE"
    assert payloads[1]["media_type"] == "TEXT"
    assert payloads[1]["reply_to_id"] == "root-id"
    assert operations == [
        "create:container-0", "ready:container-0", "publish:container-0",
        "create:container-1", "ready:container-1", "publish:container-1",
    ]
    assert len([part for part in recorded if part.status == "published"]) == 1
    assert recorded[-1].status == "failed"


@pytest.mark.asyncio
async def test_terminal_container_error_does_not_publish_or_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings

    monkeypatch.setattr("src.services.threads_service.settings", Settings(
        THREADS_ACCESS_TOKEN="mock-token", THREADS_USER_ID="123", DRY_RUN=False,
    ))
    service = ThreadsService()
    publish_calls = 0
    records = []

    async def create_container(payload: dict[str, str]) -> tuple[str, None]:
        return "container", None

    async def readiness(container_id: str) -> ContainerReadiness:
        return ContainerReadiness("error", "container_error: media_processing_failed")

    async def publish(container_id: str) -> tuple[str | None, bool, str | None]:
        nonlocal publish_calls
        publish_calls += 1
        return "unexpected", False, None

    async def persist(part: object) -> None:
        records.append(part)

    monkeypatch.setattr(service, "_create_container", create_container)
    monkeypatch.setattr(service, "_wait_for_container_status", readiness)
    monkeypatch.setattr(service, "_publish_container", publish)

    result = await service.post_thread(["main"], callbacks=ThreadPublishCallbacks(on_part_published=persist))

    assert result.status == "failed"
    assert publish_calls == 0
    assert records[0].status == "failed"
    assert "media_processing_failed" in result.error_detail
