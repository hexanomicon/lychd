import { afterEach, expect, it, vi } from "vitest";
import { blankDocument } from "$lib/canvas/engine";
afterEach(() => { vi.unstubAllGlobals(); document.cookie = "canvas-csrf=; Max-Age=0"; });

it("protects exact Canvas creation and bootstrap through generated paths", async () => {
  const Native = globalThis.Request;
  vi.stubGlobal("Request", class extends Native {
    constructor(input: RequestInfo | URL, init?: RequestInit) { super(typeof input === "string" ? new URL(input, "http://localhost") : input, init); }
  });
  const requests: Request[] = [];
  vi.stubGlobal("fetch", vi.fn(async (request: Request) => {
    if (request.url.endsWith("/altar/status")) return Response.json({ csrf: { cookie_name: "canvas-csrf", header_name: "X-Canvas-CSRF" } });
    requests.push(request); return Response.json({});
  }));
  vi.resetModules(); const api = await import("./client"); document.cookie = "canvas-csrf=only-csrf";
  const body = { id: "00000000-0000-4000-8000-000000000001", canvas_document: blankDocument() };
  await api.createCanvasProject(body); await api.bootstrapCanvasWorkspace();
  expect(requests.map((request) => [new URL(request.url).pathname, request.method])).toEqual([
    ["/api/v1/canvas/projects", "POST"], ["/api/v1/canvas/workspace/bootstrap", "POST"]
  ]);
  expect(await requests[0]!.json()).toEqual(body); expect(requests[1]!.body).toBeNull();
  for (const request of requests) expect(request.headers.get("X-Canvas-CSRF")).toBe("only-csrf");
});
