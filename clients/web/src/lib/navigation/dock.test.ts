import { describe, expect, it } from "vitest";
import { boundedDockWidth, defaultDockLayout, parseDockLayout } from "./dock";

describe("Bridge layout preferences", () => {
  it("bounds width and ignores stored content or authority fields", () => {
    expect(parseDockLayout(JSON.stringify({ width: 9999, side: "left", open: false, draft: "private", sessionId: "session-b", consent: "approve" })))
      .toEqual({ width: 720, side: "left", open: false });
    expect(boundedDockWidth(-90)).toBe(320);
  });
  it("keeps an explicitly saved right side and falls back to left for a missing side", () => {
    expect(defaultDockLayout.side).toBe("left");
    expect(parseDockLayout('{"width":400,"side":"right","open":false}')).toEqual({ width: 400, side: "right", open: false });
    expect(parseDockLayout('{"width":400,"open":false}')).toEqual({ width: 400, side: "left", open: false });
    expect(parseDockLayout('{"width":400,"side":"elsewhere","open":false}')).toEqual({ width: 400, side: "left", open: false });
  });
  it.each([null, "invalid", "null", "[]", '{"width":"700","side":"elsewhere","open":"yes"}'])("uses safe defaults for %s", (raw) => {
    expect(parseDockLayout(raw)).toEqual(defaultDockLayout);
  });
});
