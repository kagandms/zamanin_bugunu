export const PUBLICATION_CRON = "7,27,47 * * * *";
export const ANALYTICS_CRON = "37 * * * *";
export const MAX_EVENT_AGE_MS = 10 * 60_000;

export interface CronEvent {
  readonly cron: string;
  readonly scheduledTime: number;
}
export interface Slot {
  readonly day: string;
  readonly key: "morning" | "evening";
}
export interface DispatchPlan {
  readonly workflow: "schedule.yml" | "analytics.yml";
  readonly trigger_source: "cloudflare";
  readonly correlation_id: string;
  readonly intended_at: string;
  readonly intended_day: string;
  readonly intended_slot: string;
}
export type PlanResult =
  | { readonly status: "ready"; readonly plan: DispatchPlan }
  | { readonly status: "noop"; readonly reason: string };

/** Return the existing half-open Istanbul slot for an epoch time; invalid clocks return null. */
export function findSlot(timestamp: number): Slot | null {
  if (!Number.isFinite(timestamp)) return null;
  const local = new Date(timestamp + 3 * 3_600_000);
  if (!Number.isFinite(local.getTime())) return null;
  const minutes = local.getUTCHours() * 60 + local.getUTCMinutes();
  const key = minutes >= 547 && minutes < 667 ? "morning"
    : minutes >= 1207 && minutes < 1327 ? "evening" : null;
  return key ? { day: local.toISOString().slice(0, 10), key } : null;
}

/** Match intended cron occurrence AND real clock. No old event may select a new slot/day. */
export function planDispatch(event: CronEvent, observedTime: number): PlanResult {
  const age = observedTime - event.scheduledTime;
  if (!Number.isSafeInteger(event.scheduledTime) || !Number.isFinite(age) || age < 0 || age > MAX_EVENT_AGE_MS)
    return { status: "noop", reason: "stale_or_invalid_event" };
  const minute = new Date(event.scheduledTime).getUTCMinutes();
  const isPublication = event.cron === PUBLICATION_CRON && [7, 27, 47].includes(minute);
  const isAnalytics = event.cron === ANALYTICS_CRON && minute === 37;
  if (!isPublication && !isAnalytics) return { status: "noop", reason: "unrecognized_cron" };
  const intended = findSlot(event.scheduledTime);
  const observed = findSlot(observedTime);
  if (isPublication && (!intended || !observed || intended.day !== observed.day || intended.key !== observed.key))
    return { status: "noop", reason: "outside_intended_window" };
  return { status: "ready", plan: {
    workflow: isPublication ? "schedule.yml" : "analytics.yml", trigger_source: "cloudflare",
    correlation_id: `cf-${isPublication ? "publication" : "analytics"}-${event.scheduledTime}`,
    intended_at: new Date(event.scheduledTime).toISOString(),
    intended_day: isPublication ? intended?.day ?? "" : "",
    intended_slot: isPublication ? intended?.key ?? "" : "",
  } };
}
