import type { DispatchPlan } from "./policy.js";

const WORKFLOW_URL = "https://api.github.com/repos/kagandms/zamanin_bugunu/actions/workflows/";
const SECRET_FORMAT = /^[A-Za-z0-9_.-]+$/;
export interface DispatchRuntime {
  readonly fetch: typeof fetch;
  readonly token: string;
}
export type DispatchErrorName = "TypeError" | "TimeoutError" | "AbortError" | "other";
export type DispatchResult =
  | { readonly status: "accepted"; readonly httpStatus: number; readonly runId: number | null }
  | { readonly status: "rejected"; readonly httpStatus: number; readonly retryAfterMs: number | null; readonly reason?: "invalid_secret_format" }
  | { readonly status: "unknown"; readonly reason: "network_or_timeout"; readonly errorName?: DispatchErrorName; readonly errorMessage?: string }
  | { readonly status: "unknown"; readonly reason: "server_error"; readonly httpStatus?: number };

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

const REDACTED_WORDS = /token|authorization|bearer/gi;
const CONTROL_CHARS = /[\u0000-\u001F\u007F]/g;

/** Redact secrets, auth keywords, and control characters from an error message and cap its length. */
function redactMessage(message: string, secrets: readonly string[]): string {
  let redacted = message;
  const uniqueSecrets = [...new Set(secrets)].filter(Boolean).sort((a, b) => b.length - a.length);
  for (const secret of uniqueSecrets) redacted = redacted.replaceAll(secret, "[redacted]");
  return redacted.replace(REDACTED_WORDS, "[redacted]").replace(CONTROL_CHARS, " ").slice(0, 120);
}

/** Classify thrown error by fixed name only; never expose message, stack, cause, or headers. */
function classifyError(error: unknown): DispatchErrorName {
  const name = typeof error === "object" && error !== null && "name" in error ? error.name : undefined;
  return name === "TypeError" || name === "TimeoutError" || name === "AbortError" ? name : "other";
}

/** Dispatch once to an allowlisted repo/workflow/ref. Timeout/5xx are ambiguous and never auto-replayed. */
export async function dispatchOnce(plan: DispatchPlan, runtime: DispatchRuntime): Promise<DispatchResult> {
  if (!["schedule.yml", "analytics.yml"].includes(plan.workflow))
    return { status: "rejected", httpStatus: 0, retryAfterMs: null };
  const rawToken = runtime.token;
  const token = rawToken.trim();
  try {
    const { workflow, ...inputs } = plan;
    if (!SECRET_FORMAT.test(token))
      return { status: "rejected", httpStatus: 0, retryAfterMs: null, reason: "invalid_secret_format" };
    const response = await runtime.fetch(`${WORKFLOW_URL}${workflow}/dispatches`, {
      method: "POST", redirect: "error", signal: AbortSignal.timeout(5000),
      headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${token}`,
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
  } catch (error: unknown) {
    // Request/body exceptions may contain the Authorization header; only a fixed code and redacted message leave this edge.
    const rawMessage = typeof error === "object" && error !== null && "message" in error && typeof error.message === "string"
      ? error.message
      : "";
    return { status: "unknown", reason: "network_or_timeout", errorName: classifyError(error),
      errorMessage: redactMessage(rawMessage, [rawToken, token]) };
  }
}
