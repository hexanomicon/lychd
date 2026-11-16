import { afterEach, expect, it, vi } from "vitest";
import { admissionId, request } from "$lib/pages/observationsScavenger/state/observation.fixtures";

afterEach(() => { vi.unstubAllGlobals(); document.cookie = "scavenger-csrf=; Max-Age=0"; });

it("uses generated same-origin routes, exact unchanged POST bodies and existing CSRF without private URL/query data", async () => {
  const NativeRequest = globalThis.Request;
  class BrowserRequest extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(typeof input === "string" ? new URL(input, "http://localhost") : input, init); }
  }
  vi.stubGlobal("Request", BrowserRequest);
  const sent: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (r: Request) => {
    if (r.url.endsWith("/altar/status")) return Response.json({ csrf: { cookie_name: "scavenger-csrf", header_name: "X-Scavenger-Csrf" } });
    sent.push(r); return Response.json({ admission_id: admissionId });
  }));
  document.cookie = "scavenger-csrf=only-csrf";
  vi.resetModules(); const api = await import("./client"); const abort = new AbortController();
  await api.getScavengerState(abort.signal); await api.submitMarketObservation(request());
  await api.readMarketObservation(admissionId, abort.signal); await api.getMarketObservationConsent(admissionId, abort.signal);
  await api.filterMarketObservation(admissionId, { revision: "literal-casefold@1", query: "Private filter é" }, abort.signal);
  await api.deleteMarketObservation(admissionId, { request_digest: "a".repeat(64), observation_digest: null });
  expect(sent.map((r) => [r.method, new URL(r.url).pathname])).toEqual([
    ["GET", "/api/v1/scavenger"], ["POST", "/api/v1/scavenger/observations"],
    ["GET", `/api/v1/scavenger/observations/${admissionId}`], ["GET", `/api/v1/scavenger/observations/${admissionId}/consent`],
    ["POST", `/api/v1/scavenger/observations/${admissionId}/view`], ["POST", `/api/v1/scavenger/observations/${admissionId}/delete`]
  ]);
  expect(await sent[1]!.text()).toBe(JSON.stringify(request()));
  expect(await sent[4]!.text()).toBe(JSON.stringify({ revision: "literal-casefold@1", query: "Private filter é" }));
  for (const r of sent) {
    expect(new URL(r.url).search).toBe(""); expect(r.headers.has("Authorization")).toBe(false);
    if (r.method === "POST") expect(r.headers.get("X-Scavenger-Csrf")).toBe("only-csrf");
  }
  abort.abort(); for (const i of [0, 2, 3, 4]) expect(sent[i]!.signal.aborted).toBe(true);
});
