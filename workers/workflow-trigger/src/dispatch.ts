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
      readonly elapsedMs: number; readonly httpStatus?: number; readonly requestComponent?:
        "url" | "body" | "headers" | "request_init_url" | "method" | "redirect" | "request_headers" | "request_body" | "signal" | "request_init_combination" };

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

type RequestComponent = "url" | "body" | "headers" | "request_init_url" | "method" | "redirect"
  | "request_headers" | "request_body" | "signal" | "request_init_combination";

function requestFailure(error: unknown, requestComponent: RequestComponent,
  startedAt: number, now: () => number): Extract<DispatchResult, { readonly status: "unknown" }> {
  const causeCode = safeCauseCode(error);
  return { status: "unknown", reason: "request_error", phase: "request", errorName: safeErrorName(error),
    ...(causeCode ? { causeCode } : {}), elapsedMs: elapsedSince(startedAt, now), requestComponent };
}

function diagnoseRequestInit(url: URL, headers: Headers, body: string): RequestComponent {
  const signal = AbortSignal.timeout(5000);
  const checks: readonly [RequestComponent, RequestInit][] = [
    ["request_init_url", {}], ["method", { method: "POST" }],
    ["redirect", { method: "POST", redirect: "manual" }],
    ["request_headers", { method: "POST", headers }], ["request_body", { method: "POST", body }],
    ["signal", { method: "POST", signal }],
  ];
  for (const [component, init] of checks) {
    try { new Request(url, init); }
    catch { return component; }
  }
  return "request_init_combination";
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
  const { workflow, ...inputs } = plan;
  let url: URL;
  try {
    url = new URL(`${WORKFLOW_URL}${workflow}/dispatches`);
  } catch (error) {
    return requestFailure(error, "url", startedAt, now);
  }
  let body: string;
  try {
    body = JSON.stringify({ ref: "main", inputs });
  } catch (error) {
    return requestFailure(error, "body", startedAt, now);
  }
  let headers: Headers;
  try {
    headers = new Headers({ Accept: "application/vnd.github+json", Authorization: `Bearer ${runtime.token}`,
      "X-GitHub-Api-Version": "2026-03-10", "User-Agent": "zamanin-bugunu-workflow-trigger",
      "Content-Type": "application/json" });
  } catch (error) {
    return requestFailure(error, "headers", startedAt, now);
  }
  let request: Request;
  try {
    request = new Request(url, { method: "POST", redirect: "manual", signal: AbortSignal.timeout(5000), headers, body });
  } catch (error) {
    // Request initialization may include credentials; report only the fixed component label.
    return requestFailure(error, diagnoseRequestInit(url, headers, body), startedAt, now);
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
