"""Read-only weekly publication report with D-04 noon-slot experiment check.

Reads SQLite in strict read-only URI mode (`mode=ro`) and prints plain-text
tables (no ANSI colours, no HTML) with Turkish labels.

Output format
-------------
1. Header:
   - Report title, Istanbul date range (`YYYY-MM-DD .. YYYY-MM-DD`), DB path,
     and total published posts in window.
2. Per-post table (`GÖNDERİLER`):
   - Columns: `id`, `tarih_saat` (Istanbul `YYYY-MM-DD HH:MM`), `slot`
     (`morning` / `noon` / `evening`), `yil` (`event_year`), `konu`
     (`topic_category`), `uretim` (`generation_type`), `24h`, `72h`, `7d`
     (views at each window from `metric_snapshots`), `begeni` (`likes`),
     `yanit` (`verified_external_replies`), `repost` (`reposts`).
   - Missing/NULL metrics are rendered as `-` (never `0`).
3. Summaries (`ÖZET İSTATİSTİKLER`):
   - `n` (measured/total), `medyan`, `ortalama`, `p90` of views at `72h`
     (falling back to `7d` when `72h` is missing; the active window note is
     printed).
   - Breakdowns:
     * Tüm gönderiler
     * Konu kategorisi (`topic_category`)
     * Dönem (`event_year`: `1900 öncesi`, `1900-1999`, `2000 ve sonrası`,
       `Bilinmiyor`)
     * Üretim tipi (`generation_type`)
     * Slot (`slot`)
4. D-04 Experiment Check (`D-04 DENEY KONTROLÜ`), printed only when
   `experiment_id = 'D-04'` rows exist:
   - Compares median 24h views of D-04 `noon` posts against `morning`/`evening`
     posts on the same Istanbul calendar days, and compares overall D-04
     `morning`/`evening` 24h median against the pre-experiment period.
   - Verdict: `belirsiz` if fewer than 4 measured `noon` posts (or missing
     baseline), `GEÇTİ` if `noon_median >= 0.80 * same_day_me_median` and
     `d04_me_median >= 0.80 * pre_me_median`, otherwise `KALDI`.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import math
from pathlib import Path
import sqlite3
import statistics
import sys
from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")

EXCLUDED_PUBLICATION_STATUSES = ("reserved", "failed", "cancelled", "skipped", "dry_run")

PERIOD_LABELS = (
    "1900 öncesi",
    "1900-1999",
    "2000 ve sonrası",
    "Bilinmiyor",
)


@dataclass(frozen=True)
class PostRow:
    id: int
    posted_at_istanbul: datetime
    local_day: str
    slot: str
    slot_source: str
    event_year: Optional[str]
    topic_category: Optional[str]
    generation_type: Optional[str]
    experiment_id: Optional[str]
    variant: Optional[str]
    views_24h: Optional[int]
    views_72h: Optional[int]
    views_7d: Optional[int]
    likes: Optional[int]
    verified_external_replies: Optional[int]
    reposts: Optional[int]


@dataclass(frozen=True)
class SummaryStats:
    label: str
    n_total: int
    n_measured: int
    median: Optional[float]
    mean: Optional[float]
    p90: Optional[float]
    used_72h: int
    used_7d: int


def parse_utc_datetime(raw: str) -> datetime:
    """Parse an ISO/SQLite datetime string and normalize to UTC."""
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def derive_slot_from_istanbul_time(local_dt: datetime) -> str:
    """Fallback slot mapping based on src/publication_policy.py and D-04 schedule.

    Policy windows in Istanbul time:
      - morning: target 09:07 (window 09:07-11:07) -> < 11:30
      - noon:    target 12:07 (window 12:07-14:07) -> 11:30 <= t < 16:00
      - evening: target 20:07 (window 20:07-22:07) -> >= 16:00
    """
    t = local_dt.timetz().replace(tzinfo=None)
    if t < time(11, 30):
        return "morning"
    if t < time(16, 0):
        return "noon"
    return "evening"


def classify_period(event_year: Optional[str]) -> str:
    """Classify event_year into period buckets."""
    if not event_year:
        return "Bilinmiyor"
    text = event_year.strip()
    if not text:
        return "Bilinmiyor"
    upper = text.upper()
    if upper.startswith("MÖ") or upper.startswith("MO ") or upper.endswith("BC"):
        return "1900 öncesi"
    try:
        year = int(text)
    except ValueError:
        return "Bilinmiyor"
    if year < 1900:
        return "1900 öncesi"
    if year <= 1999:
        return "1900-1999"
    return "2000 ve sonrası"


def percentile_linear(sorted_values: Sequence[float], q: float) -> float:
    """Compute linear-interpolated percentile q in [0, 1] on a non-empty sorted sequence."""
    n = len(sorted_values)
    if n == 1:
        return float(sorted_values[0])
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    frac = pos - lo
    return float(sorted_values[lo]) + frac * (float(sorted_values[hi]) - float(sorted_values[lo]))


def compute_summary(label: str, posts: Iterable[PostRow]) -> SummaryStats:
    """Compute median, mean, p90 of 72h views (or 7d if 72h missing)."""
    post_list = list(posts)
    values: list[float] = []
    used_72h = 0
    used_7d = 0
    for p in post_list:
        if p.views_72h is not None:
            values.append(float(p.views_72h))
            used_72h += 1
        elif p.views_7d is not None:
            values.append(float(p.views_7d))
            used_7d += 1

    if not values:
        return SummaryStats(
            label=label,
            n_total=len(post_list),
            n_measured=0,
            median=None,
            mean=None,
            p90=None,
            used_72h=0,
            used_7d=0,
        )

    sorted_vals = sorted(values)
    return SummaryStats(
        label=label,
        n_total=len(post_list),
        n_measured=len(sorted_vals),
        median=float(statistics.median(sorted_vals)),
        mean=float(statistics.mean(sorted_vals)),
        p90=percentile_linear(sorted_vals, 0.90),
        used_72h=used_72h,
        used_7d=used_7d,
    )


def open_readonly_connection(db_path: Path) -> sqlite3.Connection:
    """Open SQLite database strictly in read-only URI mode without creating it."""
    if not db_path.exists():
        raise FileNotFoundError(f"Veritabanı bulunamadı: {db_path}")
    if not db_path.is_file():
        raise FileNotFoundError(f"Veritabanı yolu bir dosya değil: {db_path}")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_posts(conn: sqlite3.Connection) -> list[PostRow]:
    """Load all published post_history rows joined with slot and main-part snapshots."""
    placeholders = ",".join("?" for _ in EXCLUDED_PUBLICATION_STATUSES)
    post_rows = conn.execute(
        f"""
        SELECT
            h.id,
            h.posted_at,
            h.topic_category,
            h.event_year,
            h.generation_type,
            h.experiment_id,
            h.variant,
            h.publication_status
        FROM post_history AS h
        WHERE h.publication_status IS NULL
           OR h.publication_status NOT IN ({placeholders})
        ORDER BY h.posted_at ASC, h.id ASC
        """,
        EXCLUDED_PUBLICATION_STATUSES,
    ).fetchall()

    slot_by_event: dict[int, str] = {}
    for row in conn.execute(
        """
        SELECT event_id, slot_key
        FROM publication_slots
        WHERE event_id IS NOT NULL
        ORDER BY id DESC
        """
    ):
        event_id = int(row["event_id"])
        if event_id not in slot_by_event and row["slot_key"]:
            slot_by_event[event_id] = str(row["slot_key"])

    snapshots_by_event: dict[int, dict[str, sqlite3.Row]] = {}
    snap_rows = conn.execute(
        """
        SELECT
            pp_pub.event_id AS event_id,
            ms.window AS window,
            ms.views AS views,
            ms.likes AS likes,
            ms.verified_external_replies AS verified_external_replies,
            ms.reposts AS reposts,
            part.is_main AS is_main,
            part.part_index AS part_index
        FROM metric_snapshots AS ms
        JOIN publication_parts AS part ON part.id = ms.part_id
        JOIN platform_publications AS pp_pub ON pp_pub.id = part.publication_id
        ORDER BY pp_pub.event_id ASC, part.is_main DESC, part.part_index ASC, ms.id DESC
        """
    ).fetchall()

    for row in snap_rows:
        event_id = int(row["event_id"])
        win = str(row["window"])
        event_snaps = snapshots_by_event.setdefault(event_id, {})
        if win not in event_snaps:
            event_snaps[win] = row

    posts: list[PostRow] = []
    for row in post_rows:
        post_id = int(row["id"])
        utc_dt = parse_utc_datetime(str(row["posted_at"]))
        local_dt = utc_dt.astimezone(ISTANBUL)
        local_day = local_dt.date().isoformat()

        if post_id in slot_by_event:
            slot = slot_by_event[post_id]
            slot_source = "publication_slots"
        else:
            slot = derive_slot_from_istanbul_time(local_dt)
            slot_source = "posted_at_istanbul"

        snaps = snapshots_by_event.get(post_id, {})
        s24 = snaps.get("24h")
        s72 = snaps.get("72h")
        s7d = snaps.get("7d")

        def _pick_latest(col: str) -> Optional[int]:
            for s in (s7d, s72, s24):
                if s is not None and s[col] is not None:
                    return int(s[col])
            return None

        posts.append(
            PostRow(
                id=post_id,
                posted_at_istanbul=local_dt,
                local_day=local_day,
                slot=slot,
                slot_source=slot_source,
                event_year=row["event_year"],
                topic_category=row["topic_category"],
                generation_type=row["generation_type"],
                experiment_id=row["experiment_id"],
                variant=row["variant"],
                views_24h=int(s24["views"]) if s24 is not None and s24["views"] is not None else None,
                views_72h=int(s72["views"]) if s72 is not None and s72["views"] is not None else None,
                views_7d=int(s7d["views"]) if s7d is not None and s7d["views"] is not None else None,
                likes=_pick_latest("likes"),
                verified_external_replies=_pick_latest("verified_external_replies"),
                reposts=_pick_latest("reposts"),
            )
        )
    return posts


def _fmt_int(val: Optional[int]) -> str:
    return "-" if val is None else str(val)


def _fmt_num(val: Optional[float]) -> str:
    if val is None:
        return "-"
    if abs(val - round(val)) < 1e-9:
        return str(int(round(val)))
    return f"{val:.1f}"


def _format_table(headers: Sequence[str], rows: Sequence[Sequence[str]], right_align: set[int]) -> list[str]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if len(cell) > widths[i]:
                widths[i] = len(cell)

    def _fmt_row(cells: Sequence[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i in right_align:
                parts.append(cell.rjust(widths[i]))
            else:
                parts.append(cell.ljust(widths[i]))
        return " | ".join(parts)

    sep = "-+-".join("-" * w for w in widths)
    lines = [_fmt_row(headers), sep]
    for row in rows:
        lines.append(_fmt_row(row))
    return lines


def _window_note(stats: SummaryStats) -> str:
    if stats.n_measured == 0:
        return "veri yok"
    if stats.used_72h > 0 and stats.used_7d == 0:
        return "72h"
    if stats.used_7d > 0 and stats.used_72h == 0:
        return "7d (72h eksik)"
    return f"72h ({stats.used_72h}) + 7d ({stats.used_7d})"


def format_summary_section(title: str, stats_list: Sequence[SummaryStats]) -> list[str]:
    lines = [f"\n-- {title} --"]
    headers = ("Grup", "n", "Medyan", "Ortalama", "P90", "Pencere")
    rows = [
        (
            s.label,
            f"{s.n_measured}/{s.n_total}",
            _fmt_num(s.median),
            _fmt_num(s.mean),
            _fmt_num(s.p90),
            _window_note(s),
        )
        for s in stats_list
    ]
    lines.extend(_format_table(headers, rows, right_align={1, 2, 3, 4}))
    return lines


def format_d04_section(all_posts: Sequence[PostRow]) -> Optional[list[str]]:
    """Evaluate D-04 noon slot rule if any experiment_id='D-04' rows exist."""
    d04_posts = [p for p in all_posts if p.experiment_id == "D-04"]
    if not d04_posts:
        return None

    min_d04_dt = min(p.posted_at_istanbul for p in d04_posts)
    max_d04_dt = max(p.posted_at_istanbul for p in d04_posts)

    noon_posts = [p for p in d04_posts if p.slot == "noon"]
    noon_views = [float(p.views_24h) for p in noon_posts if p.views_24h is not None]
    noon_days = {p.local_day for p in noon_posts}

    same_day_me_views = [
        float(p.views_24h)
        for p in all_posts
        if p.local_day in noon_days and p.slot in ("morning", "evening") and p.views_24h is not None
    ]

    d04_me_views = [
        float(p.views_24h)
        for p in all_posts
        if min_d04_dt <= p.posted_at_istanbul <= max_d04_dt
        and p.slot in ("morning", "evening")
        and p.views_24h is not None
    ]

    pre_me_views = [
        float(p.views_24h)
        for p in all_posts
        if p.posted_at_istanbul < min_d04_dt
        and p.experiment_id != "D-04"
        and p.slot in ("morning", "evening")
        and p.views_24h is not None
    ]

    noon_med = float(statistics.median(noon_views)) if noon_views else None
    same_day_me_med = float(statistics.median(same_day_me_views)) if same_day_me_views else None
    d04_me_med = float(statistics.median(d04_me_views)) if d04_me_views else None
    pre_me_med = float(statistics.median(pre_me_views)) if pre_me_views else None

    if len(noon_views) < 4:
        verdict = "belirsiz (yetersiz öğle örneği: < 4)"
    elif same_day_me_med is None or pre_me_med is None or d04_me_med is None:
        verdict = "belirsiz (karşılaştırma verisi eksik)"
    else:
        cond1 = noon_med is not None and noon_med >= 0.80 * same_day_me_med
        cond2 = d04_me_med >= 0.80 * pre_me_med
        if cond1 and cond2:
            verdict = "GEÇTİ (3. slot kalır)"
        else:
            verdict = "KALDI (3. slot kriteri sağlamadı)"

    ratio_str = (
        f"{(noon_med / same_day_me_med) * 100:.1f}%"
        if noon_med is not None and same_day_me_med
        else "-"
    )
    change_str = (
        f"{((d04_me_med - pre_me_med) / pre_me_med) * 100:+.1f}%"
        if d04_me_med is not None and pre_me_med
        else "-"
    )

    lines = [
        "\n=== D-04 DENEY KONTROLÜ (Öğle Slotu - 24h Görüntüleme) ===",
        f"Öğle (noon) gönderi sayısı (24h ölçümlü): {len(noon_views)} / {len(noon_posts)}",
        f"Öğle (noon) 24h medyan                  : {_fmt_num(noon_med)}",
        f"Aynı gün sabah/akşam 24h medyan (n={len(same_day_me_views)}): {_fmt_num(same_day_me_med)} (Öğle/Sabah-Akşam: {ratio_str})",
        f"Deney dönemi sabah/akşam medyan (n={len(d04_me_views)}): {_fmt_num(d04_me_med)}",
        f"Deney öncesi sabah/akşam medyan (n={len(pre_me_views)}): {_fmt_num(pre_me_med)} (Değişim: {change_str})",
        f"Karar                                   : {verdict}",
    ]
    return lines


def build_report(
    all_posts: Sequence[PostRow],
    db_path: Path,
    days: int,
    today: date,
) -> str:
    """Build the full plain-text weekly report."""
    start_day = today - timedelta(days=days - 1)
    start_iso = start_day.isoformat()
    end_iso = today.isoformat()

    window_posts = [p for p in all_posts if start_iso <= p.local_day <= end_iso]

    lines: list[str] = [
        "=== HAFTALIK YAYIN RAPORU ===",
        f"Veritabanı : {db_path}",
        f"Tarih Aralığı (İstanbul): {start_iso} .. {end_iso} ({days} gün)",
        f"Toplam Gönderi: {len(window_posts)}",
        "",
        "=== GÖNDERİLER ===",
    ]

    if not window_posts:
        lines.append("(Bu tarih aralığında gönderi bulunamadı)")
    else:
        headers = (
            "id",
            "tarih_saat",
            "slot",
            "yil",
            "konu",
            "uretim",
            "24h",
            "72h",
            "7d",
            "begeni",
            "yanit",
            "repost",
        )
        table_rows = [
            (
                str(p.id),
                p.posted_at_istanbul.strftime("%Y-%m-%d %H:%M"),
                p.slot,
                p.event_year or "-",
                p.topic_category or "-",
                p.generation_type or "-",
                _fmt_int(p.views_24h),
                _fmt_int(p.views_72h),
                _fmt_int(p.views_7d),
                _fmt_int(p.likes),
                _fmt_int(p.verified_external_replies),
                _fmt_int(p.reposts),
            )
            for p in window_posts
        ]
        lines.extend(_format_table(headers, table_rows, right_align={0, 6, 7, 8, 9, 10, 11}))

    lines.append("")
    lines.append("=== ÖZET İSTATİSTİKLER (72h görüntüleme; 72h eksikse 7d) ===")
    lines.extend(format_summary_section("Genel", [compute_summary("Tüm gönderiler", window_posts)]))

    # By topic_category
    topics = sorted({p.topic_category or "(belirtilmemiş)" for p in window_posts})
    topic_stats = [
        compute_summary(t, [p for p in window_posts if (p.topic_category or "(belirtilmemiş)") == t])
        for t in topics
    ]
    if topic_stats:
        lines.extend(format_summary_section("Konu Kategorisi", topic_stats))

    # By period
    period_stats = []
    for period_label in PERIOD_LABELS:
        group = [p for p in window_posts if classify_period(p.event_year) == period_label]
        if group:
            period_stats.append(compute_summary(period_label, group))
    if period_stats:
        lines.extend(format_summary_section("Dönem", period_stats))

    # By generation_type
    gen_types = sorted({p.generation_type or "(belirtilmemiş)" for p in window_posts})
    gen_stats = [
        compute_summary(g, [p for p in window_posts if (p.generation_type or "(belirtilmemiş)") == g])
        for g in gen_types
    ]
    if gen_stats:
        lines.extend(format_summary_section("Üretim Tipi", gen_stats))

    # By slot
    slots = sorted({p.slot for p in window_posts})
    slot_stats = [
        compute_summary(s, [p for p in window_posts if p.slot == s])
        for s in slots
    ]
    if slot_stats:
        lines.extend(format_summary_section("Slot", slot_stats))

    d04_lines = format_d04_section(all_posts)
    if d04_lines is not None:
        lines.extend(d04_lines)

    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only weekly publication report.")
    parser.add_argument("--db", default="bot_data.db", help="Path to SQLite database (default: bot_data.db)")
    parser.add_argument("--days", type=int, default=7, help="Number of Istanbul days to include (default: 7)")
    parser.add_argument("--today", default=None, help="Override end date in YYYY-MM-DD (Istanbul)")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.days < 1:
        print("Hata: --days en az 1 olmalıdır.", file=sys.stderr)
        return 2

    if args.today is not None:
        try:
            today = date.fromisoformat(args.today)
        except ValueError:
            print(f"Hata: geçersiz --today tarihi (YYYY-MM-DD bekleniyor): {args.today}", file=sys.stderr)
            return 2
    else:
        today = datetime.now(ISTANBUL).date()

    db_path = Path(args.db)
    try:
        conn = open_readonly_connection(db_path)
    except (FileNotFoundError, sqlite3.Error, OSError) as exc:
        print(f"Hata: veritabanı açılamadı: {exc}", file=sys.stderr)
        return 1

    try:
        all_posts = load_posts(conn)
    except sqlite3.Error as exc:
        print(f"Hata: veritabanı sorgusu başarısız: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    report = build_report(all_posts=all_posts, db_path=db_path, days=args.days, today=today)
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
