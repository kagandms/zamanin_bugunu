import test from 'node:test';
import assert from 'node:assert/strict';
import { planDispatch, findSlot, PUBLICATION_CRON, ANALYTICS_CRON } from '../build/policy.js';
import { dispatchOnce } from '../build/dispatch.js';
import { handleScheduled, rejectHttp } from '../build/index.js';

const ENV = { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: 'mock-token-do-not-log' };
const epoch = value => Date.parse(`2026-10-15T${value}Z`);
function fixture(options = {}) {
  const requests = [], records = [], sleeps = [];
  let now = options.now ?? epoch('06:07:00');
  const edge = {
    now: () => now,
    fetch: async (...args) => {
      requests.push(args);
      if (options.failure) throw options.failure;
      return (options.responses ?? [new Response(null, { status: 204 })]).shift();
    },
    sleep: async delay => { sleeps.push(delay); now += delay + (options.extraDelay ?? 0); },
    log: record => records.push(record),
  };
  return { edge, requests, records, sleeps };
}
const event = (timestamp = epoch('06:07:00'), cron = PUBLICATION_CRON) => ({ cron, scheduledTime: timestamp });

for (const [time, expected] of [['06:06:59', null], ['06:07:00', 'morning'], ['08:06:59', 'morning'],
  ['08:07:00', null], ['17:06:59', null], ['17:07:00', 'evening'], ['19:06:59', 'evening'], ['19:07:00', null]]) {
  test(`half-open slot at ${time}`, () => assert.equal(findSlot(epoch(time))?.key ?? null, expected));
}

test('UTC/Istanbul midnight never opens a publication window', () => {
  for (const time of ['20:59:59', '21:00:00', '23:59:59', '00:00:00']) assert.equal(findSlot(epoch(time)), null);
});

test('one day has twelve nominal publication dispatches and twenty-four analytics dispatches', () => {
  let publication = 0, analytics = 0;
  for (let minute = 0; minute < 1440; minute++) {
    const now = epoch('00:00:00') + minute * 60_000;
    if (planDispatch(event(now), now).status === 'ready') publication++;
    if (planDispatch(event(now, ANALYTICS_CRON), now).status === 'ready') analytics++;
  }
  assert.equal(publication, 12);
  assert.equal(analytics, 24);
});

test('stale cron, future/invalid clock, unknown cron and old day all no-op', () => {
  for (const [scheduled, observed, cron] of [
    [epoch('06:07:00'), epoch('06:18:00'), PUBLICATION_CRON],
    [epoch('06:07:00'), epoch('06:06:59'), PUBLICATION_CRON],
    [NaN, epoch('06:07:00'), PUBLICATION_CRON],
    [epoch('06:07:00'), epoch('06:07:00'), '* * * * *'],
    [epoch('06:07:00') - 86400000, epoch('06:07:00'), PUBLICATION_CRON],
    [epoch('07:47:00'), epoch('08:07:00'), PUBLICATION_CRON],
  ]) assert.equal(planDispatch(event(scheduled, cron), observed).status, 'noop');
});

for (const env of [{}, { DISPATCH_ENABLED: 'false', GITHUB_DISPATCH_TOKEN: 'fake' },
  { DISPATCH_ENABLED: 'true' }, { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: '  ' }]) {
  test(`disabled/missing secret ${JSON.stringify(env)}`, async () => {
    const sample = fixture();
    await handleScheduled(event(), env, sample.edge);
    assert.equal(sample.requests.length, 0);
  });
}

test('fixed workflow repo and main ref, deterministic metadata on duplicate delivery', async () => {
  const sample = fixture({ responses: [new Response(null, { status: 204 }), new Response(null, { status: 204 })] });
  await handleScheduled(event(), ENV, sample.edge);
  await handleScheduled(event(), ENV, sample.edge);
  const [request] = sample.requests[0];
  const [duplicateRequest] = sample.requests[1];
  assert.equal(request.url, duplicateRequest.url);
  assert.equal(await request.clone().text(), await duplicateRequest.clone().text());
  assert.equal(request.url, 'https://api.github.com/repos/kagandms/zamanin_bugunu/actions/workflows/schedule.yml/dispatches');
  assert.equal(request.redirect, 'error');
  const payload = await request.clone().json();
  assert.equal(payload.ref, 'main');
  assert.equal(payload.inputs.intended_day, '2026-10-15');
  assert.equal(payload.inputs.intended_slot, 'morning');
  assert.equal(payload.inputs.correlation_id, `cf-publication-${epoch('06:07:00')}`);
  assert.equal(JSON.stringify(sample.records).includes(ENV.GITHUB_DISPATCH_TOKEN), false);
});

test('analytics dispatch has no slot and only targets analytics workflow', async () => {
  const now = epoch('21:37:00');
  const sample = fixture({ now });
  await handleScheduled(event(now, ANALYTICS_CRON), ENV, sample.edge);
  assert.match(sample.requests[0][0].url, /analytics.yml\/dispatches$/);
  assert.equal((await sample.requests[0][0].clone().json()).inputs.intended_slot, '');
});

test('documented 200 run details and legacy 204 are accepted independently of execution', async () => {
  for (const response of [Response.json({ workflow_run_id: 123, run_url: 'https://malicious.invalid/token' }),
    new Response(null, { status: 204 })]) {
    const sample = fixture({ responses: [response] });
    await handleScheduled(event(), ENV, sample.edge);
    assert.equal(sample.records.find(record => record.stage === 'dispatch_result').status, 'accepted');
    assert.equal(JSON.stringify(sample.records).includes('malicious'), false);
  }
});

for (const status of [401, 403, 404, 422, 429, 500, 502, 503]) {
  test(`HTTP ${status} has no unbounded/ambiguous replay or raw-body logs`, async () => {
    const sample = fixture({ responses: [new Response('secret-token-url', { status })] });
    await handleScheduled(event(), ENV, sample.edge);
    assert.equal(sample.requests.length, 1);
    assert.equal(sample.records.find(record => record.stage === 'dispatch_result').httpStatus, status);
    assert.equal(JSON.stringify(sample.records).includes('secret-token-url'), false);
  });
}

test('429 permits exactly one retry after short Retry-After and never loops', async () => {
  const response = () => new Response(null, { status: 429, headers: { 'Retry-After': '1' } });
  const sample = fixture({ responses: [response(), response()] });
  await handleScheduled(event(), ENV, sample.edge);
  assert.equal(sample.requests.length, 2);
  assert.deepEqual(sample.sleeps, [1000]);
});

test('long Retry-After and HTTP-date defer to next nominal check', async () => {
  for (const header of ['60', 'Wed, 21 Oct 2026 07:28:00 GMT', 'NaN']) {
    const sample = fixture({ responses: [new Response(null, { status: 429, headers: { 'Retry-After': header } })] });
    await handleScheduled(event(), ENV, sample.edge);
    assert.equal(sample.requests.length, 1);
    assert.equal(sample.sleeps.length, 0);
  }
});

test('retry revalidates actual clock after delay crosses a closing boundary', async () => {
  const sample = fixture({ now: epoch('08:06:59'), responses: [new Response(null,
    { status: 429, headers: { 'Retry-After': '2' } })] });
  await handleScheduled(event(epoch('07:57:00')), ENV, sample.edge);
  // This malformed nominal minute is rejected before networking.
  assert.equal(sample.requests.length, 0);
  const delayed = fixture({ responses: [new Response(null, { status: 429, headers: { 'Retry-After': '1' } })],
    now: epoch('07:47:00'), extraDelay: 20 * 60_000 });
  await handleScheduled(event(epoch('07:47:00')), ENV, delayed.edge);
  assert.equal(delayed.requests.length, 1);
  assert.equal(delayed.records.at(-1).stage, 'retry_skipped');
});

test('fetch rejection and timeout are separately labeled, sanitized and not retried', async () => {
  for (const failure of [new Error('Authorization: mock-token-do-not-log'), new DOMException('token-url', 'TimeoutError')]) {
    const sample = fixture({ failure });
    await handleScheduled(event(), ENV, sample.edge);
    assert.equal(sample.requests.length, 1);
    const result = sample.records.find(record => record.stage === 'dispatch_result');
    assert.equal(result.status, 'unknown');
    assert.equal(result.phase, 'fetch');
    assert.equal(result.reason, failure.name === 'TimeoutError' ? 'timeout' : 'fetch_rejected');
    assert.equal(typeof result.elapsedMs, 'number');
    assert.equal(JSON.stringify(sample.records).includes('token'), false);
  }
});

test('diagnostic allowlists tolerate hostile error properties without leaking them', async () => {
  const failure = Object.defineProperties({}, {
    name: { get() { throw new Error('credential in name getter'); } },
    cause: { get() { throw new Error('credential in cause getter'); } },
  });
  const sample = fixture({ failure });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.status, 'unknown');
  assert.equal(result.phase, 'fetch');
  assert.equal(result.reason, 'fetch_rejected');
  assert.equal(result.errorName, 'Other');
  assert.equal(JSON.stringify(sample.records).includes('credential'), false);
});

test('request-construction errors never call fetch and expose only fixed diagnostic fields', async () => {
  const requests = [], records = [];
  const errorToken = 'mock-secret-do-not-log';
  const eventAt = epoch('06:07:00');
  const env = { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: `${errorToken}\ninvalid-header` };
  await handleScheduled(event(eventAt), env, {
    now: () => eventAt, fetch: async request => { requests.push(request); return new Response(null, { status: 204 }); },
    sleep: async () => {}, log: record => records.push(record),
  });
  assert.equal(requests.length, 0);
  const result = records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.status, 'unknown');
  assert.equal(result.phase, 'request');
  assert.equal(result.reason, 'request_error');
  assert.equal(result.requestComponent, 'headers');
  assert.equal(result.errorName, 'TypeError');
  assert.equal(typeof result.elapsedMs, 'number');
  assert.equal(JSON.stringify(records).includes(errorToken), false);
  assert.equal(JSON.stringify(records).includes('invalid-header'), false);
});

test('direct request diagnostics keep HTTP response status separate from fetch errors', async () => {
  const plan = planDispatch(event(), epoch('06:07:00'));
  assert.equal(plan.status, 'ready');
  const result = await dispatchOnce(plan.plan, {
    token: 'mock-token-do-not-log', fetch: async () => new Response('sensitive body', { status: 403 }), now: () => 10,
  });
  assert.deepEqual(result, { status: 'rejected', httpStatus: 403, retryAfterMs: null, elapsedMs: 0 });
});

test('authorization header trims surrounding secret whitespace before Request construction', async () => {
  const plan = planDispatch(event(), epoch('06:07:00'));
  assert.equal(plan.status, 'ready');
  let authorizationHeader = '';
  const result = await dispatchOnce(plan.plan, {
    token: 'mock-token-do-not-log\r\n',
    fetch: async request => {
      authorizationHeader = request.headers.get('Authorization') ?? '';
      return new Response(null, { status: 204 });
    },
  });
  assert.equal(result.status, 'accepted');
  assert.equal(authorizationHeader, 'Bearer mock-token-do-not-log');
});

test('HTTP methods cannot dispatch even with arbitrary URL/body selectors', async () => {
  for (const [method, status] of [['GET', 404], ['HEAD', 404], ['POST', 405], ['PUT', 405], ['OPTIONS', 405]]) {
    const response = await rejectHttp(new Request('https://worker.invalid/dispatch?repo=evil&ref=branch', { method }));
    assert.equal(response.status, status);
  }
});

test('accepted response with unavailable details remains accepted and is never replayed', async () => {
  const sample = fixture({ responses: [new Response('bad-json', { status: 200 })] });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.status, 'accepted');
  assert.equal(result.runId, null);
  assert.equal(sample.requests.length, 1);
});

test('observed time and scheduledTime remain separate even on an outside-window noop', async () => {
  const sample = fixture({ now: epoch('20:07:30') });
  await handleScheduled(event(epoch('20:07:00')), ENV, sample.edge);
  assert.equal(sample.records[0].scheduled_time_ms, epoch('20:07:00'));
  assert.equal(sample.records[0].observed_time_ms, epoch('20:07:30'));
  assert.equal(sample.requests.length, 0);
  assert.deepEqual(sample.sleeps, []);
});

test('5xx preserves unknown acceptance state rather than asserting definitive rejection', async () => {
  const sample = fixture({ responses: [new Response(null, { status: 503 })] });
  await handleScheduled(event(), ENV, sample.edge);
  assert.equal(sample.records.find(record => record.stage === 'dispatch_result').status, 'unknown');
  assert.equal(sample.requests.length, 1);
});
