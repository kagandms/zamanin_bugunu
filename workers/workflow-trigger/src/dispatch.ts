import type { DispatchPlan } from "./policy.js";

const WORKFLOW_URL = "https://api.github.com/repos/kagandms/zamanin_bugunu/actions/workflows/";
export interface DispatchRuntime {
  readonly fetch: typeof fetch;
  readonly token: string;
}
export type DispatchResult =
  | { readonly status: "accepted"; readonly httpStatus: number; readonly runId: number | null }
  | { readonly status: "rejected"; readonly httpStatus: number; readonly retryAfterMs: number | null }
  | { readonly status: "unknown"; readonly reason: "network_or_timeout" | "server_error"; readonly httpStatus?: number };

/** Parse only a documented positive run ID; never forward an untrusted response URL or message. */
function readRunId(payload: unknown): number | null {
  if (typeof payload !== "object" || payload === null || !("workflow_run_id" in payload)) return null;
  const runId = payload.workflow_run_id;
  return typeof runId === "number" && Number.isSafeInteger(runId) && runId > 0 ? runId : null;
}

async function readAcceptance(response: Response): Promise<number | null> {
  try { return readRunId(await response.json()); }
  catch {
    // HTTP accepted the mutation even if the details body was unavailable; never replay it.
    return null;
  }
}

/** Accept numeric Retry-After up to two seconds; longer/date/missing values defer to next cron. */
function retryDelay(response: Response): number | null {
  const header = response.headers.get("Retry-After");
  if (!header || !/^\d+(\.\d+)?$/.test(header)) return null;
  const milliseconds = Number(header) * 1000;
  return milliseconds <= 2000 ? milliseconds : null;
}

/** Dispatch once to an allowlisted repo/workflow/ref. Timeout/5xx are ambiguous and never auto-replayed. */
export async function dispatchOnce(plan: DispatchPlan, runtime: DispatchRuntime): Promise<DispatchResult> {
  if (!["schedule.yml", "analytics.yml"].includes(plan.workflow))
    return { status: "rejected", httpStatus: 0, retryAfterMs: null };
  try {
    const { workflow, ...inputs } = plan;
    const response = await runtime.fetch(`${WORKFLOW_URL}${workflow}/dispatches`, {
      method: "POST", redirect: "error", signal: AbortSignal.timeout(5000),
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${runtime.token}`,
        "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "zamanin-bugunu-workflow-trigger",
        "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main", inputs }),
    });
    if (response.status === 204) return { status: "accepted", httpStatus: 204, runId: null };
    if (response.status === 200) return { status: "accepted", httpStatus: 200, runId: await readAcceptance(response) };
    const result: DispatchResult = response.status >= 500
      ? { status: "unknown", reason: "server_error", httpStatus: response.status }
      : { status: "rejected", httpStatus: response.status,
        retryAfterMs: response.status === 429 ? retryDelay(response) : null };
    await response.body?.cancel();
    return result;
  } catch {
    // Request/body exceptions may contain the Authorization header; only a fixed code leaves this edge.
    return { status: "unknown", reason: "network_or_timeout" };
  }
}
