from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.data.models import MetricAttempt, MetricSnapshot, PlatformPublication, PostHistory, PublicationPart

from src.analytics_collection import (
    AnalyticsSummary, Clock, CollectionContext, InsightsClient, WINDOWS,
    collect_due_snapshots,
)


@dataclass(frozen=True)
class WindowSample:
    part_id: int
    snapshot: Optional[MetricSnapshot]
    age_seconds: Optional[int]
    target_seconds: int
    report_time: datetime
    status: str


@dataclass(frozen=True)
class AnalyticsOptions:
    """Session, client, migration and deterministic clock overrides for one sync."""
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    threads_service: Optional[InsightsClient] = None
    now: Optional[datetime] = None
    clock: Optional[Clock] = None
    initialize: bool = True


@dataclass(frozen=True)
class AnalyticsResult:
    """Canonical report and separate operational result for a completed sync."""
    report: str
    summary: AnalyticsSummary


async def sync_analytics(options: Optional[AnalyticsOptions] = None) -> AnalyticsResult:
    """Synchronize measurements and return durable outcomes plus workflow status.

    Args: options: session/client/clock overrides. Returns: report and structured counts.
    Raises: initialization/report/database errors; API failures remain counted outcomes.
    """
    from src.data.database import AsyncSessionLocal, init_db

    selected = options or AnalyticsOptions()
    if selected.initialize:
        await init_db()
    clock = selected.clock or (lambda: selected.now or datetime.now(timezone.utc))
    factory = selected.session_factory or AsyncSessionLocal
    context = CollectionContext(_as_utc(clock()), clock, selected.threads_service)
    async with factory() as session:
        summary = await collect_due_snapshots(session, context)
        report = await _build_report(session, _as_utc(clock()))
    return AnalyticsResult(report + "\nSync summary: " + json.dumps(asdict(summary), sort_keys=True), summary)


async def run_analytics(
    session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
    threads_service: Optional[InsightsClient] = None,
    now: Optional[datetime] = None,
    initialize: bool = True,
) -> str:
    """Compatibility report API; CLI uses sync_analytics.summary for failure status.

    Args: session_factory, threads_service, now, initialize: existing caller overrides.
    Returns: printed report. Raises: database/init/report errors.
    """
    result = await sync_analytics(AnalyticsOptions(session_factory, threads_service, now, initialize=initialize))
    print(result.report)
    return result.report


async def _save_snapshot(session: AsyncSession, snapshot: MetricSnapshot) -> None:
    from src.data.snapshot_store import save_canonical_snapshot

    await save_canonical_snapshot(session, snapshot)


async def _build_report(session: AsyncSession, observed_at: datetime) -> str:
    publication_rows = await session.execute(
        select(PlatformPublication.platform, PlatformPublication.status)
    )
    statuses: dict[str, dict[str, int]] = {}
    for platform, status in publication_rows.all():
        bucket = statuses.setdefault(platform, {})
        bucket[status] = bucket.get(status, 0) + 1
    published_events_result = await session.execute(
        select(func.count(distinct(PlatformPublication.event_id)))
        .join(PublicationPart, PublicationPart.publication_id == PlatformPublication.id)
        .where(PublicationPart.is_main.is_(True), PublicationPart.status == "published")
    )
    event_status_rows = await session.execute(
        select(PostHistory.publication_status, func.count(PostHistory.id))
        .group_by(PostHistory.publication_status)
    )
    event_status_summary = ", ".join(
        f"{status}={count}" for status, count in event_status_rows.all()
    ) or "henüz yok"

    snapshot_rows = await session.execute(
        select(MetricSnapshot, PublicationPart, PostHistory)
        .join(PublicationPart, MetricSnapshot.part_id == PublicationPart.id)
        .join(PlatformPublication, PublicationPart.publication_id == PlatformPublication.id)
        .join(PostHistory, PlatformPublication.event_id == PostHistory.id)
    )
    rows = list(snapshot_rows.all())
    lines = ["ZAMANIN BUGÜNÜ — THREADS ANALİTİK RAPORU", ""]
    for platform in ("threads", "telegram"):
        bucket = statuses.get(platform, {})
        lines.append(f"{platform}: " + ", ".join(f"{key}={value}" for key, value in sorted(bucket.items())))
    lines.append(f"Başarılı ana olay sayısı: {int(published_events_result.scalar_one() or 0)}")
    lines.append(f"Olay durumları: {event_status_summary}")
    attempt_rows = await session.execute(select(MetricAttempt.status, func.count(MetricAttempt.id))
                                         .group_by(MetricAttempt.status))
    lines.append("Insights denemeleri (kanonik örneklem dışında): " + (", ".join(
        f"{status}={count}" for status, count in attempt_rows.all()) or "henüz yok"))
    lines.append("Başarılı ana olay: platformlarda en az bir doğrulanmış ana parça yayımlanan tekil olay sayısı.")
    for window in WINDOWS:
        exact_rows = [snapshot for snapshot, part, _ in rows
                      if part.is_main and snapshot.window == window and snapshot.status == "success"]
        lines.extend(await _window_schedule_report(session, window, observed_at))
        views = [snapshot.views for snapshot in exact_rows if snapshot.views is not None]
        lines.append(f"{window} ana gönderi medyan görüntülenme: {statistics.median(views) if views else 'yok'} (n={len(views)})")
        lines.append(f"{window} gözlem durumu: " + _status_counts(rows, window))
        lines.extend(_engagement_ratios(exact_rows, window))
    lines.extend(_reply_summary(rows))
    categories: dict[str, list[int]] = {}
    for snapshot, part, event in rows:
        if part.is_main and snapshot.window == "24h" and snapshot.status == "success" and snapshot.views is not None:
            categories.setdefault(event.topic_category or "GENEL", []).append(snapshot.views)
    lines.append("Kategori 24h görüntülenmesi:")
    for category, category_views in sorted(categories.items()):
        sample_note = "az örnek (n<5)" if len(category_views) < 5 else f"n={len(category_views)}"
        lines.append(f"  {category}: medyan={statistics.median(category_views)}; {sample_note}")
    lines.append("Dry-run, rezervasyon, başarısız yayın, başarısız ölçüm ve eksik metrikler sıfır başarı olarak sayılmaz.")
    return "\n".join(lines)


async def _window_schedule_report(
    session: AsyncSession, window: str, observed_at: datetime
) -> list[str]:
    target_seconds = WINDOWS[window]
    result = await _load_window_schedule_rows(session, window)
    examples: dict[str, str] = {}
    counts: dict[str, int] = {}
    for part, snapshot in result:
        age = None if part.published_at is None else max(
            0, int((_as_utc(observed_at) - _as_utc(part.published_at)).total_seconds())
        )
        status = "unknown_time" if age is None else "upcoming" if age < target_seconds else (
            snapshot.status if snapshot is not None else "pending"
        )
        counts[status] = counts.get(status, 0) + 1
        if status not in examples:
            sample_age = snapshot.actual_age_seconds if snapshot is not None else age
            sample = WindowSample(part.id, snapshot, sample_age, target_seconds, observed_at, status)
            examples[status] = _format_window_example(sample)
    summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items())) or "henüz yok"
    lines = [f"{window} pencere zamanlaması: {summary}"]
    lines.extend(examples[status] for status in sorted(examples))
    return lines


async def _load_window_schedule_rows(
    session: AsyncSession, window: str
) -> list[tuple[PublicationPart, Optional[MetricSnapshot]]]:
    result = await session.execute(
        select(PublicationPart, MetricSnapshot)
        .join(PlatformPublication, PublicationPart.publication_id == PlatformPublication.id)
        .outerjoin(
            MetricSnapshot,
            (MetricSnapshot.part_id == PublicationPart.id) & (MetricSnapshot.window == window),
        )
        .where(
            PlatformPublication.platform == "threads",
            PublicationPart.is_main.is_(True),
        )
    )
    return list(result.all())


def _format_window_example(sample: WindowSample) -> str:
    observed = _as_utc(sample.snapshot.observed_at).isoformat() if sample.snapshot else "yok"
    age = str(sample.age_seconds) if sample.age_seconds is not None else "unknown"
    deviation = (str(sample.age_seconds - sample.target_seconds)
                 if sample.age_seconds is not None else "unknown")
    report_timestamp = _as_utc(sample.report_time).isoformat()
    reply_time = (sample.snapshot.reply_observed_at if sample.snapshot is not None else None)
    reply_timestamp = _as_utc(reply_time).isoformat() if reply_time else "yok"
    return (f"  örnek part={sample.part_id}: gözlem={observed}; kontrol={report_timestamp}; "
            f"yaş={age} sn; hedef={sample.target_seconds} sn; "
            f"sapma={deviation} sn; durum={sample.status}; reply_gözlem={reply_timestamp}")


def _status_counts(rows: list[tuple], window: str) -> str:
    counts: dict[str, int] = {}
    for snapshot, _, _ in rows:
        if snapshot.window == window:
            counts[snapshot.status] = counts.get(snapshot.status, 0) + 1
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items())) or "henüz yok"


def _engagement_ratios(snapshots: list[MetricSnapshot], window: str) -> list[str]:
    ratios: list[str] = []
    for metric in ("likes", "reposts", "quotes"):
        values = [getattr(snapshot, metric) * 1000 / snapshot.views
                  for snapshot in snapshots
                  if snapshot.views is not None and snapshot.views > 0 and getattr(snapshot, metric) is not None]
        ratios.append(f"{window} 1.000 görüntülenme başına {metric}: " +
                      (f"medyan={statistics.median(values):.2f} (n={len(values)})" if values else "hesaplanamaz (eksik/sıfır payda)"))
    return ratios


def _reply_summary(rows: list[tuple]) -> list[str]:
    main_snapshots = [snapshot for snapshot, part, _ in rows
                      if part.is_main and snapshot.window == "24h"]
    measured_snapshots = [snapshot for snapshot in main_snapshots
                          if snapshot.status in ("success", "late")]
    raw_replies = [snapshot.replies for snapshot in measured_snapshots if snapshot.replies is not None]
    external_replies = [snapshot.verified_external_replies for snapshot in main_snapshots
                        if snapshot.organic_reply_status == "success"
                        and snapshot.verified_external_replies is not None]
    own_replies = [snapshot.own_reply_count for snapshot in main_snapshots
                   if snapshot.organic_reply_status == "success" and snapshot.own_reply_count is not None]
    reply_status_counts: dict[str, int] = {}
    for snapshot in main_snapshots:
        reply_status_counts[snapshot.organic_reply_status] = reply_status_counts.get(snapshot.organic_reply_status, 0) + 1
    return [
        "24h raw replies: " + (f"medyan={statistics.median(raw_replies)} (n={len(raw_replies)})" if raw_replies else "unknown"),
        "24h verified direct external replies: " + (f"medyan={statistics.median(external_replies)} (n={len(external_replies)})" if external_replies else "unknown"),
        "24h verified own direct replies: " + (f"medyan={statistics.median(own_replies)} (n={len(own_replies)})" if own_replies else "unknown"),
        "24h reply attribution status: " + (", ".join(f"{status}={count}" for status, count in sorted(reply_status_counts.items())) or "unknown"),
        "External reply zero, missing reply metrics, and lookup permission/network errors are kept distinct.",
    ]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def _execute_cli(is_report_only: bool) -> int:
    if is_report_only:
        from src.data.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            report = await _build_report(session, datetime.now(timezone.utc))
        print(report)
        return 0
    result = await sync_analytics()
    print(result.report)
    return result.summary.exit_code


def run_cli() -> int:
    """Parse sync/report-only mode; return 0/2/3 for core result, 1 for fatal failures.

    Returns: process exit code. API records commit before reporting operational failure.
    """
    parser = argparse.ArgumentParser(description="Threads analytics synchronization/report")
    parser.add_argument("--report-only", action="store_true", help="Read the migrated DB without sync or migration")
    arguments = parser.parse_args()
    try:
        return asyncio.run(_execute_cli(arguments.report_only))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        from src.core.logger import logger
        logger.error("Analytics fatal failure (%s)", type(error).__name__)
        return 1


if __name__ == "__main__":
    os.environ["ZAMANIN_ANALYTICS_CLI"] = "1"
    sys.exit(run_cli())
