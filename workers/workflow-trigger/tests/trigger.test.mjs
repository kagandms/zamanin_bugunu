import test from 'node:test';
import assert from 'node:assert/strict';
import { planDispatch, findSlot, PUBLICATION_CRON, ANALYTICS_CRON } from '../build/policy.js';
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
  ['08:07:00', null], ['09:06:59', null], ['09:07:00', 'noon'], ['11:06:59', 'noon'], ['11:07:00', null],
  ['17:06:59', null], ['17:07:00', 'evening'], ['19:06:59', 'evening'], ['19:07:00', null]]) {
  test(`half-open slot at ${time}`, () => assert.equal(findSlot(epoch(time))?.key ?? null, expected));
}

test('UTC/Istanbul midnight never opens a publication window', () => {
  for (const time of ['20:59:59', '21:00:00', '23:59:59', '00:00:00']) assert.equal(findSlot(epoch(time)), null);
});

for (const [day, expectedPublication] of [
  ['2026-10-12', 12], // Monday
  ['2026-10-13', 12], // Tuesday
  ['2026-10-14', 12], // Wednesday
  ['2026-10-15', 18], // Thursday (noon)
  ['2026-10-16', 18], // Friday (noon)
  ['2026-10-17', 12], // Saturday
  ['2026-10-18', 18], // Sunday (noon)
]) {
  test(`${day} has ${expectedPublication} nominal publication dispatches and twenty-four analytics dispatches`, () => {
    const start = Date.parse(`${day}T00:00:00Z`);
    let publication = 0, analytics = 0;
    for (let minute = 0; minute < 1440; minute++) {
      const now = start + minute * 60_000;
      if (planDispatch(event(now), now).status === 'ready') publication++;
      if (planDispatch(event(now, ANALYTICS_CRON), now).status === 'ready') analytics++;
    }
    assert.equal(publication, expectedPublication);
    assert.equal(analytics, 24);
  });
}

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
  assert.deepEqual(sample.requests[0], sample.requests[1]);
  const [url, request] = sample.requests[0];
  assert.equal(url, 'https://api.github.com/repos/kagandms/zamanin_bugunu/actions/workflows/schedule.yml/dispatches');
  assert.equal(request.redirect, 'manual');
  const payload = JSON.parse(request.body);
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
  assert.match(sample.requests[0][0], /analytics.yml\/dispatches$/);
  assert.equal(JSON.parse(sample.requests[0][1].body).inputs.intended_slot, '');
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

test('network/timeout errors are unknown, sanitized and not retried', async () => {
  for (const failure of [new Error('Authorization: mock-token-do-not-log'), new DOMException('token-url', 'TimeoutError')]) {
    const sample = fixture({ failure });
    await handleScheduled(event(), ENV, sample.edge);
    assert.equal(sample.requests.length, 1);
    assert.equal(sample.records.find(record => record.stage === 'dispatch_result').status, 'unknown');
    assert.equal(JSON.stringify(sample.records).includes('token'), false);
  }
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

for (const [day, expected] of [
  ['2026-10-12', null],   // Monday
  ['2026-10-13', null],   // Tuesday
  ['2026-10-14', null],   // Wednesday
  ['2026-10-15', 'noon'], // Thursday
  ['2026-10-16', 'noon'], // Friday
  ['2026-10-17', null],   // Saturday
  ['2026-10-18', 'noon'], // Sunday
]) {
  test(`noon slot on ${day} at 09:07Z-11:06:59Z returns ${expected}`, () => {
    for (const time of ['09:07:00', '09:47:00', '10:27:00', '11:06:59']) {
      const slot = findSlot(Date.parse(`${day}T${time}Z`));
      assert.equal(slot?.key ?? null, expected);
      if (expected) assert.equal(slot.day, day);
    }
    assert.equal(findSlot(Date.parse(`${day}T09:06:59Z`)), null);
    assert.equal(findSlot(Date.parse(`${day}T11:07:00Z`)), null);
  });
}

test('planDispatch dispatches noon for existing 7,27,47 cron on Thu/Fri/Sun and no-ops otherwise', () => {
  for (const day of ['2026-10-15', '2026-10-16', '2026-10-18']) {
    for (const time of ['09:07:00', '09:27:00', '09:47:00', '10:07:00', '10:27:00', '10:47:00']) {
      const ts = Date.parse(`${day}T${time}Z`);
      const result = planDispatch(event(ts), ts);
      assert.equal(result.status, 'ready');
      assert.equal(result.plan.workflow, 'schedule.yml');
      assert.equal(result.plan.intended_day, day);
      assert.equal(result.plan.intended_slot, 'noon');
    }
  }
  for (const day of ['2026-10-12', '2026-10-13', '2026-10-14', '2026-10-17']) {
    const ts = Date.parse(`${day}T09:27:00Z`);
    assert.deepEqual(planDispatch(event(ts), ts), { status: 'noop', reason: 'outside_intended_window' });
  }
  const closed = Date.parse('2026-10-15T11:07:00Z');
  assert.deepEqual(planDispatch(event(closed), closed), { status: 'noop', reason: 'outside_intended_window' });
  const late = Date.parse('2026-10-15T10:47:00Z');
  assert.deepEqual(planDispatch(event(late), late + 20 * 60_000), { status: 'noop', reason: 'stale_or_invalid_event' });
});

test('handleScheduled sends intended_slot noon on Thursday noon cron', async () => {
  const now = Date.parse('2026-10-15T09:07:00Z');
  const sample = fixture({ now });
  await handleScheduled(event(now), ENV, sample.edge);
  assert.equal(sample.requests.length, 1);
  const payload = JSON.parse(sample.requests[0][1].body);
  assert.equal(payload.inputs.intended_day, '2026-10-15');
  assert.equal(payload.inputs.intended_slot, 'noon');
});

test('trims trailing whitespace and newline from token before setting Authorization header', async () => {
  const sample = fixture();
  await handleScheduled(event(), { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: 'mock-token-do-not-log\n ' }, sample.edge);
  assert.equal(sample.requests.length, 1);
  assert.equal(sample.requests[0][1].headers.Authorization, 'Bearer mock-token-do-not-log');
});

test('TypeError from fetch logs errorName TypeError without leaking message or token', async () => {
  const sample = fixture({ failure: new TypeError('Authorization: mock-token-do-not-log') });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.status, 'unknown');
  assert.equal(result.reason, 'network_or_timeout');
  assert.equal(result.errorName, 'TypeError');
  const serialized = JSON.stringify(sample.records);
  assert.equal(serialized.includes('mock-token-do-not-log'), false);
  assert.equal(serialized.includes('Authorization'), false);
});

test('catch classifies TimeoutError, AbortError, and other error names safely', async () => {
  for (const [failure, expectedErrorName] of [
    [new DOMException('token-url', 'TimeoutError'), 'TimeoutError'],
    [new DOMException('aborted', 'AbortError'), 'AbortError'],
    [new Error('x'), 'other'],
  ]) {
    const sample = fixture({ failure });
    await handleScheduled(event(), ENV, sample.edge);
    const result = sample.records.find(record => record.stage === 'dispatch_result');
    assert.equal(result.status, 'unknown');
    assert.equal(result.reason, 'network_or_timeout');
    assert.equal(result.errorName, expectedErrorName);
    assert.equal(JSON.stringify(sample.records).includes('token'), false);
  }
});

test('rejects tokens with invalid or non-ASCII characters before fetch without leaking secret', async () => {
  for (const badToken of [
    'mock-token\u200B-x',
    'mock-tokenİ-x',
    'mock-token\n-x',
    'mock-token\r-x',
    'mock\u0000token',
  ]) {
    const sample = fixture();
    await handleScheduled(event(), { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: badToken }, sample.edge);
    assert.equal(sample.requests.length, 0);
    const results = sample.records.filter(record => record.stage === 'dispatch_result');
    assert.equal(results.length, 1);
    assert.equal(results[0].status, 'rejected');
    assert.equal(results[0].httpStatus, 0);
    assert.equal(results[0].reason, 'invalid_secret_format');
    const serialized = JSON.stringify(sample.records);
    assert.equal(serialized.includes(badToken), false);
    assert.equal(serialized.includes('Authorization'), false);
  }
});

test('accepts valid token containing letters, digits, underscore, hyphen, and dot', async () => {
  const token = 'github_pat_AbC123_x-y.z';
  const sample = fixture();
  await handleScheduled(event(), { DISPATCH_ENABLED: 'true', GITHUB_DISPATCH_TOKEN: token }, sample.edge);
  assert.equal(sample.requests.length, 1);
  assert.equal(sample.requests[0][1].headers.Authorization, `Bearer ${token}`);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.status, 'accepted');
});

test('TypeError from fetch logs redacted errorMessage without leaking token or auth keywords', async () => {
  const sample = fixture({ failure: new TypeError('Failed to parse header: Authorization: Bearer mock-token-do-not-log in value') });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.reason, 'network_or_timeout');
  assert.equal(result.errorName, 'TypeError');
  assert.equal(result.errorMessage.includes('Failed to parse header'), true);
  assert.equal(result.errorMessage.includes('mock-token-do-not-log'), false);
  assert.equal(/token|authorization|bearer/i.test(result.errorMessage), false);
  assert.equal(result.errorMessage.length <= 120, true);
  assert.equal(JSON.stringify(sample.records).includes('mock-token-do-not-log'), false);
});

test('long thrown error message is truncated to at most 120 characters', async () => {
  const sample = fixture({ failure: new Error('a'.repeat(350)) });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.errorMessage.length <= 120, true);
});

test('control characters like newline and tab in error message are replaced by spaces', async () => {
  const sample = fixture({ failure: new Error('line1\nline2\tline3') });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.errorMessage.includes('\n'), false);
  assert.equal(result.errorMessage.includes('\t'), false);
  assert.equal(result.errorMessage, 'line1 line2 line3');
});

test('non-Error thrown value yields empty errorMessage and errorName other', async () => {
  const sample = fixture({ failure: 'boom' });
  await handleScheduled(event(), ENV, sample.edge);
  const result = sample.records.find(record => record.stage === 'dispatch_result');
  assert.equal(result.errorName, 'other');
  assert.equal(result.errorMessage, '');
});

test('dispatch fetch init uses a redirect value the Workers runtime accepts', async () => {
  const sample = fixture();
  await handleScheduled(event(), ENV, sample.edge);
  assert.equal(sample.requests.length, 1);
  const [, init] = sample.requests[0];
  assert.ok(['follow', 'manual'].includes(init.redirect));
  assert.notEqual(init.redirect, 'error');
});
