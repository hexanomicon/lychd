import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { OrbEventEnvelope } from "$lib/api/models";
import { fixtureRun } from "./__fixtures__/snapshot";
import { incompleteCreation } from "./__fixtures__/creation";
import { coldPreferredRoute } from "./__fixtures__/preference";
import { getOrbCatalogue, listenToOrb, type OrbLiveCallbacks } from "./live";

class Source extends EventTarget {
  static CLOSED = 2;
  static instances: Source[] = [];
  readyState = 1;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  close = vi.fn(() => { this.readyState = Source.CLOSED; });
  constructor(readonly url: string) { super(); Source.instances.push(this); }
  emit(kind: string, frame: unknown, id?: string) { this.dispatchEvent(new MessageEvent(kind, { data: JSON.stringify(frame), lastEventId: id ?? String((frame as OrbEventEnvelope).cursor) })); }
}
const callbacks = (): OrbLiveCallbacks => ({ onFrame: vi.fn(), onConnection: vi.fn(), onReset: vi.fn(), onFault: vi.fn() });
function frame(changes: Partial<OrbEventEnvelope> = {}): OrbEventEnvelope {
  const snapshot = fixtureRun();
  snapshot.evidence = [{ ...snapshot.evidence[0]!, seq: 1, event_id: "live-1" }];
  snapshot.ledger_head_seq = 1;
  return { schema_version: 1, run_id: "run-a", kind: "evidence", after_seq: 0, cursor: 1, snapshot, ...changes };
}
beforeEach(() => { Source.instances = []; vi.stubGlobal("EventSource", Source); });
afterEach(() => vi.unstubAllGlobals());

describe("Orb retained-ledger feed", () => {
  it("uses the selected Run and retained head; ignores replay, accepts metadata and closes only on settled", () => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const source = Source.instances[0]!;
    expect(source.url).toBe("/api/v1/orb/runs/run-a/events?after_seq=0");
    source.onopen?.(); expect(cb.onConnection).toHaveBeenLastCalledWith("connected");
    const event = frame(); event.snapshot.run.status = "done";
    source.emit("evidence", event);
    expect(source.close).not.toHaveBeenCalled();
    source.emit("evidence", event);
    expect(cb.onFrame).toHaveBeenCalledOnce();
    source.emit("settled", frame({ kind: "settled", after_seq: 1, cursor: 1, snapshot: { ...event.snapshot, evidence: [] } }));
    expect(cb.onFrame).toHaveBeenCalledTimes(2);
    expect(source.close).toHaveBeenCalledOnce();
    expect(cb.onConnection).toHaveBeenLastCalledWith("settled");
  });
  it.each(["foreign", "cursor", "range", "schema", "oversize"])("closes on invalid %s without publishing data", (failure) => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const value = frame();
    if (failure === "foreign") value.snapshot.run.run_id = "other";
    if (failure === "cursor") value.after_seq = 2;
    if (failure === "range") value.snapshot.evidence[0]!.seq = 5;
    if (failure === "schema") Object.assign(value, { schema_version: 2 });
    if (failure === "oversize") value.snapshot.evidence = Array.from({ length: 101 }, (_, i) => ({ ...value.snapshot.evidence[0]!, event_id: String(i), seq: i + 1 }));
    Source.instances[0]!.emit("evidence", value);
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(cb.onFault).toHaveBeenCalledOnce();
    expect(Source.instances[0]!.close).toHaveBeenCalledOnce();
  });
  it("treats a reset before monotonic-cursor validation and leaves replacement to its owner", () => {
    const cb = callbacks(); listenToOrb("run-a", 50, cb);
    Source.instances[0]!.emit("reset", frame({ kind: "reset", after_seq: 50, cursor: 0, snapshot: fixtureRun() }));
    expect(cb.onReset).toHaveBeenCalledOnce();
    expect(cb.onFault).not.toHaveBeenCalled();
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(Source.instances[0]!.close).toHaveBeenCalledOnce();
  });
  it("fences callbacks after teardown and distinguishes reconnecting from settlement", () => {
    const cb = callbacks(); const stop = listenToOrb("run-a", 0, cb);
    const source = Source.instances[0]!;
    source.onerror?.(); expect(cb.onConnection).toHaveBeenLastCalledWith("reconnecting");
    expect(cb.onFrame).not.toHaveBeenCalled();
    stop(); source.emit("evidence", frame()); source.onopen?.(); source.onerror?.();
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(cb.onConnection).toHaveBeenLastCalledWith("reconnecting");
  });
  it("stops native retries after a hard connection refusal", () => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const source = Source.instances[0]!; source.readyState = Source.CLOSED; source.onerror?.();
    expect(cb.onConnection).toHaveBeenLastCalledWith("closed");
    expect(cb.onFault).toHaveBeenCalledOnce();
  });
});

it.each([401, 403])("preserves catalogue refusal %i so its owner can clear protected history", async (status) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status }));
  const refused = getOrbCatalogue();
  await expect(refused).rejects.toThrow("cannot read");
  await expect(refused).rejects.toMatchObject({ status });
});

describe("Creation metadata transport", () => {
  it("retains authorized metadata without bodies and clears it at the same ledger cursor", () => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame(); event.snapshot.creation = { ...incompleteCreation };
    Object.assign(event.snapshot.creation, { private_response: "must not enter client state" });
    Source.instances[0]!.emit("evidence", event);
    expect(cb.onFrame).toHaveBeenLastCalledWith(expect.objectContaining({ snapshot: expect.objectContaining({ creation: incompleteCreation }) }));
    const received = vi.mocked(cb.onFrame).mock.calls[0]![0].snapshot.creation;
    expect(received).not.toHaveProperty("private_response");
    Source.instances[0]!.emit("evidence", frame({ after_seq: 1, cursor: 1, snapshot: { ...event.snapshot, evidence: [], creation: null } }));
    expect(vi.mocked(cb.onFrame).mock.calls[1]![0].snapshot.creation).toBeNull();
    expect(cb.onFault).not.toHaveBeenCalled();
  });

  it.each(["foreign_run", "invalid_status", "invalid_deadline", "oversize_reason"])("refuses %s metadata before publication", (failure) => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame(); event.snapshot.creation = { ...incompleteCreation };
    if (failure === "foreign_run") event.snapshot.creation.run_id = "foreign";
    if (failure === "invalid_status") Object.assign(event.snapshot.creation, { native_status: "successful" });
    if (failure === "invalid_deadline") event.snapshot.creation.deadline = "yesterday";
    if (failure === "oversize_reason") event.snapshot.creation.reason_code = "x".repeat(65);
    Source.instances[0]!.emit("evidence", event);
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(cb.onFault).toHaveBeenCalledOnce();
    expect(Source.instances[0]!.close).toHaveBeenCalledOnce();
  });
});

describe("Routing preference metadata transport", () => {
  it("retains supplied observations, strips bodies, and accepts a metadata-only clear", () => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame(); event.snapshot.bridge_preference = structuredClone(coldPreferredRoute);
    Object.assign(event.snapshot.bridge_preference, { private_body: "must not enter client state" });
    Source.instances[0]!.emit("evidence", event);
    const received = vi.mocked(cb.onFrame).mock.calls[0]![0].snapshot.bridge_preference;
    expect(received).toEqual(coldPreferredRoute);
    expect(received).not.toHaveProperty("private_body");
    Source.instances[0]!.emit("evidence", frame({ after_seq: 1, cursor: 1,
      snapshot: { ...event.snapshot, evidence: [], bridge_preference: null }
    }));
    expect(vi.mocked(cb.onFrame).mock.calls[1]![0].snapshot.bridge_preference).toBeNull();
    expect(cb.onFault).not.toHaveBeenCalled();
  });

  it("retains a disabled route without a phase or timestamp", () => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame(); event.snapshot.bridge_preference = { ...coldPreferredRoute,
      routes: [{ ...coldPreferredRoute.routes[0]!, weight: 0, phase: null, observed_at: null,
        admission_open: false, exclusion_code: "disabled" }, coldPreferredRoute.routes[1]!]
    };
    Source.instances[0]!.emit("evidence", event);
    expect(vi.mocked(cb.onFrame).mock.calls[0]![0].snapshot.bridge_preference).toEqual(event.snapshot.bridge_preference);
    expect(cb.onFault).not.toHaveBeenCalled();
  });

  it.each(["extra_route", "missing_route", "duplicate_route", "negative_weight", "fractional_weight", "oversize_weight", "unknown_phase", "unknown_exclusion", "invalid_time", "empty_key", "oversize_key", "invalid_digest", "version"])("refuses malformed %s before publishing it", (failure) => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame(); const preference = structuredClone(coldPreferredRoute);
    if (failure === "extra_route") preference.routes.push({ ...preference.routes[0]! });
    if (failure === "missing_route") preference.routes.pop();
    if (failure === "duplicate_route") preference.routes[1]!.capability_key = preference.routes[0]!.capability_key;
    if (failure === "negative_weight") preference.routes[0]!.weight = -1;
    if (failure === "fractional_weight") preference.routes[0]!.weight = 0.5;
    if (failure === "oversize_weight") preference.routes[0]!.weight = 1_000_001;
    if (failure === "unknown_phase") Object.assign(preference.routes[0]!, { phase: "ready" });
    if (failure === "unknown_exclusion") Object.assign(preference.routes[0]!, { exclusion_code: "not_preferred" });
    if (failure === "invalid_time") preference.routes[0]!.observed_at = "yesterday";
    if (failure === "empty_key") preference.routes[0]!.capability_key = "";
    if (failure === "oversize_key") preference.routes[0]!.capability_key = "x".repeat(513);
    if (failure === "invalid_digest") preference.policy_digest = "not-a-policy-digest";
    if (failure === "version") Object.assign(preference, { policy_schema_version: 2 });
    event.snapshot.bridge_preference = preference;
    Source.instances[0]!.emit("evidence", event);
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(cb.onFault).toHaveBeenCalledOnce();
    expect(Source.instances[0]!.close).toHaveBeenCalledOnce();
  });
});

it("retains nullable Bridge and an explicit application return in validated live snapshots", () => {
  const cb = callbacks(); listenToOrb("run-a", 0, cb); const value = frame();
  value.snapshot.run.bridge_path = null;
  value.snapshot.run.application_path = "/scavenger?observation=00000000-0000-4000-8000-000000000001";
  Source.instances[0]!.emit("evidence", value);
  expect(cb.onFault).not.toHaveBeenCalled();
  expect(vi.mocked(cb.onFrame).mock.calls[0]?.[0].snapshot.run.application_path).toBe(value.snapshot.run.application_path);
});


describe("Historical consent reference transport", () => {
  it.each(["consent-a", "a".repeat(128), null, undefined])("preserves the bounded optional historical reference %s", (consentId) => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame();
    Object.assign(event.snapshot.evidence[0]!, { kind: "consent", consent_id: consentId,
      tool_name: "private tool", native_review: { private_body: "must not enter history" } });
    Source.instances[0]!.emit("evidence", event);
    const received = vi.mocked(cb.onFrame).mock.calls[0]?.[0].snapshot.evidence[0];
    expect(received).toBeDefined();
    expect(received?.consent_id).toBe(consentId);
    expect(received).not.toHaveProperty("tool_name");
    expect(received).not.toHaveProperty("native_review");
    expect(cb.onFault).not.toHaveBeenCalled();
    expect(Source.instances[0]!.close).not.toHaveBeenCalled();
  });

  it.each([123, true, {}, [], "", "a".repeat(129), "../foreign", "bad id", "consent-a\n"])("closes on malformed consent reference %j before publishing data", (consentId) => {
    const cb = callbacks(); listenToOrb("run-a", 0, cb);
    const event = frame();
    Object.assign(event.snapshot.evidence[0]!, { kind: "consent", consent_id: consentId });
    const source = Source.instances[0]!;
    source.emit("evidence", event);
    expect(cb.onFrame).not.toHaveBeenCalled();
    expect(cb.onFault).toHaveBeenCalledOnce();
    expect(cb.onConnection).toHaveBeenLastCalledWith("closed");
    expect(source.close).toHaveBeenCalledOnce();
    source.emit("evidence", frame());
    expect(cb.onFrame).not.toHaveBeenCalled();
  });
});
