import type { DispatchPlan } from "./policy.js";

const WORKFLOW_URL = "https://api.github.com/repos/kagandms/zamanin_bugunu/actions/workflows/";
export interface DispatchRuntime {
  readonly fetch: typeof fetch;
  readonly token: string;
  readonly now?: () => number;
}
export type DispatchResult =
  | { readonly status: "accepted"; readonly httpStatus: number; readonly runId: number | null; readonly elapsedMs: number }
  | { readonly status: "rejected"; readonly httpStatus: number; readonly retryAfterMs: number | null; readonly elapsedMs: number }
  | { readonly status: "unknown"; readonly reason: "request_error" | "fetch_rejected" | "response_error" | "timeout" | "server_error";
      readonly phase: "request" | "fetch" | "response"; readonly errorName?: string; readonly causeCode?: string;
      readonly elapsedMs: number; readonly httpStatus?: number };

const SAFE_ERROR_NAMES = new Set(["TypeError", "AbortError", "TimeoutError", "RangeError", "Error"]);
const SAFE_CAUSE_CODES = new Set(["ECONNRESET", "ETIMEDOUT", "ENOTFOUND", "EAI_AGAIN", "ECONNREFUSED"]);

function safeErrorName(error: unknown): string {
  try {
    const name = error instanceof Error ? error.name : "";
    return SAFE_ERROR_NAMES.has(name) ? name : "Other";
  } catch {
    return "Other";
  }
}

function safeCauseCode(error: unknown): string | undefined {
  try {
    if (typeof error !== "object" || error === null || !("cause" in error)) return undefined;
    const cause: unknown = error.cause;
    if (typeof cause !== "object" || cause === null || !("code" in cause)) return undefined;
    const code = cause.code;
    return typeof code === "string" && SAFE_CAUSE_CODES.has(code) ? code : undefined;
  } catch {
    return undefined;
  }
}

function elapsedSince(startedAt: number, now: () => number): number {
  const elapsed = now() - startedAt;
  return Number.isFinite(elapsed) ? Math.max(0, Math.floor(elapsed)) : 0;
}

function unknownFailure(error: unknown, phase: "request" | "fetch" | "response", startedAt: number,
  now: () => number): DispatchResult {
  const errorName = safeErrorName(error);
  const reason = phase === "request" ? "request_error"
    : phase === "response" ? "response_error"
    : errorName === "AbortError" || errorName === "TimeoutError" ? "timeout" : "fetch_rejected";
  const causeCode = safeCauseCode(error);
  return { status: "unknown", reason, phase, errorName, ...(causeCode ? { causeCode } : {}), elapsedMs: elapsedSince(startedAt, now) };
}

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
    return { status: "rejected", httpStatus: 0, retryAfterMs: null, elapsedMs: 0 };
  const now = runtime.now ?? Date.now;
  const startedAt = now();
  let request: Request;
  try {
    const { workflow, ...inputs } = plan;
    request = new Request(`${WORKFLOW_URL}${workflow}/dispatches`, {
      method: "POST", redirect: "error", signal: AbortSignal.timeout(5000),
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${runtime.token.trim()}`,
        "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "zamanin-bugunu-workflow-trigger",
        "Content-Type": "application/json" },
      body: JSON.stringify({ ref: "main", inputs }),
    });
  } catch (error) {
    // Request construction can include credentials; report fixed labels only.
    return unknownFailure(error, "request", startedAt, now);
  }
  let response: Response;
  try {
    response = await runtime.fetch(request);
  } catch (error) {
    return unknownFailure(error, "fetch", startedAt, now);
  }
  try {
    const elapsedMs = elapsedSince(startedAt, now);
    if (response.status === 204) return { status: "accepted", httpStatus: 204, runId: null, elapsedMs };
    if (response.status === 200) return { status: "accepted", httpStatus: 200, runId: await readAcceptance(response), elapsedMs };
    if (response.status >= 500) {
      await response.body?.cancel();
      return { status: "unknown", reason: "server_error", phase: "response", httpStatus: response.status, elapsedMs };
    }
    const result: DispatchResult = { status: "rejected", httpStatus: response.status,
      retryAfterMs: response.status === 429 ? retryDelay(response) : null, elapsedMs };
    await response.body?.cancel();
    return result;
  } catch (error) {
    // Response handling errors are separate from request construction and fetch rejection.
    return unknownFailure(error, "response", startedAt, now);
  }
}
