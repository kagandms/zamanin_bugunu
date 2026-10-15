import { dispatchOnce, type DispatchResult } from "./dispatch.js";
import { planDispatch, type CronEvent } from "./policy.js";

export interface Environment {
  readonly DISPATCH_ENABLED?: string;
  readonly GITHUB_DISPATCH_TOKEN?: string;
}
export interface Runtime {
  readonly now: () => number;
  readonly fetch: typeof fetch;
  readonly sleep: (milliseconds: number) => Promise<void>;
  readonly log: (record: Readonly<Record<string, unknown>>) => void;
}
const runtime: Runtime = {
  now: Date.now, fetch: globalThis.fetch.bind(globalThis),
  sleep: (milliseconds: number): Promise<void> => new Promise(resolve => setTimeout(resolve, milliseconds)),
  log: (record: Readonly<Record<string, unknown>>): void => console.info(JSON.stringify(record)),
};

/** Execute cron with injected time/network/logger. Only explicit 429 permits one bounded retry. */
export async function handleScheduled(event: CronEvent, env: Environment, edge: Runtime): Promise<void> {
  edge.log({ stage: "cron_observed", scheduled_time_ms: Number.isFinite(event.scheduledTime) ? event.scheduledTime : null,
    observed_time_ms: edge.now() });
  if (env.DISPATCH_ENABLED !== "true" || !env.GITHUB_DISPATCH_TOKEN?.trim()) {
    edge.log({ stage: "noop", reason: "disabled_or_missing_secret" });
    return;
  }
  const planned = planDispatch(event, edge.now());
  if (planned.status === "noop") { edge.log(planned); return; }
  edge.log({ stage: "dispatch_planned", correlation_id: planned.plan.correlation_id,
    intended_at: planned.plan.intended_at, observed_at: new Date(edge.now()).toISOString(),
    intended_day: planned.plan.intended_day, intended_slot: planned.plan.intended_slot });
  let result = await dispatchOnce(planned.plan, { fetch: edge.fetch, token: env.GITHUB_DISPATCH_TOKEN });
  logResult(planned.plan.correlation_id, result, edge);
  if (result.status !== "rejected" || result.httpStatus !== 429 || result.retryAfterMs === null) return;
  await edge.sleep(result.retryAfterMs);
  const retry = planDispatch(event, edge.now());
  if (retry.status === "noop") { edge.log({ stage: "retry_skipped", reason: retry.reason }); return; }
  result = await dispatchOnce(retry.plan, { fetch: edge.fetch, token: env.GITHUB_DISPATCH_TOKEN });
  logResult(retry.plan.correlation_id, result, edge);
}

function logResult(correlation: string, result: DispatchResult, edge: Runtime): void {
  edge.log({ stage: "dispatch_result", correlation_id: correlation,
    observed_at: new Date(edge.now()).toISOString(), ...result });
}

/** HTTP has no dispatch surface. Query parameters, body and paths never select a target. */
export async function rejectHttp(request: Request): Promise<Response> {
  return new Response("Not found", { status: ["GET", "HEAD"].includes(request.method) ? 404 : 405 });
}

export default {
  fetch: rejectHttp,
  async scheduled(event: CronEvent, env: Environment): Promise<void> {
    await handleScheduled(event, env, runtime);
  },
};
