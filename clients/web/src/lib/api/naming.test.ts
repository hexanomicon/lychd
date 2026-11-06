import { afterEach, expect, it, vi } from "vitest";
import type { NamingAcceptance } from "./models";
afterEach(() => { vi.unstubAllGlobals(); document.cookie = "naming-csrf=; Max-Age=0"; });
function browserRequests() {
  const Native = globalThis.Request;
  vi.stubGlobal("Request", class extends Native {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(typeof input === "string" ? new URL(input, "http://localhost") : input, init); }
  });
}
it("reads names and local suggestions without mutation and submits exact CAS names with server CSRF names", async () => {
  browserRequests(); const requests: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => {
    if (request.url.endsWith("/altar/status")) return Response.json({ csrf: { cookie_name: "naming-csrf", header_name: "X-Naming-CSRF" } });
    requests.push(request); return Response.json({ current: null });
  }));
  vi.resetModules(); const api = await import("./client"); document.cookie = "naming-csrf=csrf-only";
  const controller = new AbortController();
  const body: NamingAcceptance = { expected_revision: 4, names: { magus_name: "Aster Vale", primus_name: "Ember Dawn", magus_origin: "manual", primus_origin: "self_chosen" } };
  await api.getNaming(controller.signal); await api.getNamingSuggestions(controller.signal); await api.acceptNaming(body, controller.signal);
  expect(requests.map((r) => [new URL(r.url).pathname, r.method])).toEqual([
    ["/api/v1/altar/naming", "GET"], ["/api/v1/altar/naming/suggestions", "GET"], ["/api/v1/altar/naming", "PUT"]
  ]);
  expect(requests.slice(0, 2).every((r) => r.body === null)).toBe(true);
  expect(await requests[2]!.json()).toEqual(body);
  expect(requests[2]!.headers.get("X-Naming-CSRF")).toBe("csrf-only");
  expect(requests[2]!.headers.has("Authorization")).toBe(false);
  controller.abort(); expect(requests.every((r) => r.signal.aborted)).toBe(true);
});
it("preserves stale revision status for explicit reload instead of retrying acceptance", async () => {
  browserRequests(); const writes: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => {
    if (request.url.endsWith("/altar/status")) return Response.json({ csrf: { cookie_name: "naming-csrf", header_name: "X-Naming-CSRF" } });
    writes.push(request); return Response.json({ detail: "Stale" }, { status: 409 });
  }));
  vi.resetModules(); const api = await import("./client");
  const names: NamingAcceptance["names"] = { magus_name: "Aster Vale", primus_name: "Ember Dawn", magus_origin: "manual", primus_origin: "dictionary" };
  await expect(api.acceptNaming({ expected_revision: 3, names })).rejects.toMatchObject({ status: 409 });
  expect(writes).toHaveLength(1); expect(writes[0]!.method).toBe("PUT");
});
