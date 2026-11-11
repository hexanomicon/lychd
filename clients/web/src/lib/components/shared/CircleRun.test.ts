import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

import type { LiveTurn } from "$lib/bridge/projection";
import CircleRun from "./CircleRun.svelte";

function projection(changes: Partial<LiveTurn> = {}): LiveTurn {
  return {
    sessionId: "session-a", runId: "run-a", cursor: 1, authorityGeneration: 0,
    content: "A retained reply", runStatus: "running", activity: "weaving", state: "streaming",
    fragments: [], patternId: "bridge_chat", patternRevision: "2",
    loomPath: "/loom/bridge_chat/2", orbPath: "/orb/run-a", evidenceCapture: "process_local",
    occurrenceId: null, dispatchOccurrenceId: null, grantId: null, capabilityKey: null,
    transitionOccurrenceId: null, transitionRequestId: null, transitionPhase: null,
    delegatedJobId: null, delegatedRuntime: null, delegatedProfile: null, delegatedStatus: null,
    ...changes
  };
}

describe("Circle Run disclosure", () => {
  it("keeps Run evidence available when collapsed and carries exact Run and job to the score", async () => {
    render(CircleRun, { runId: "run-a", turn: projection({ delegatedJobId: "job-a" }) });
    const toggle = screen.getByRole("button", { name: "Circle details for Run run-a" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("link", { name: "Look into the Orb" }).getAttribute("href")).toBe("/orb/run-a?job=job-a");
    expect(screen.queryByRole("link", { name: "View declared score" })).toBeNull();
    await fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByRole("link", { name: "View declared score" }).getAttribute("href")).toBe("/loom/bridge_chat/2?run=run-a&job=job-a");
    expect(screen.getByText("job-a")).toBeTruthy();
  });

  it("discloses complete long identities without requiring hover", async () => {
    const runId = `run-${"a".repeat(120)}`;
    const revision = `revision-${"b".repeat(100)}`;
    render(CircleRun, { runId, turn: projection({ runId, orbPath: `/orb/${runId}`, patternRevision: revision, loomPath: `/loom/bridge_chat/${revision}` }) });
    await fireEvent.click(screen.getByRole("button", { name: `Circle details for Run ${runId}` }));
    expect(screen.getByText(runId).tagName).toBe("CODE");
    expect(screen.getByText(revision).tagName).toBe("CODE");
    expect(screen.getByText(runId).closest("[hidden]")).toBeNull();
    expect(screen.getByText(runId).getAttribute("title")).toBeNull();
  });

  it("does not infer a status or declared score from an archived reply", async () => {
    render(CircleRun, { runId: "run-a" });
    expect(screen.getByText("Retained reply")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Cancel run/ })).toBeNull();
    expect(screen.getByRole("link", { name: "Look into the Orb" }).getAttribute("href")).toBe("/orb/run-a");
    await fireEvent.click(screen.getByRole("button", { name: /Circle details/ }));
    expect(screen.getAllByText("Not retained in this reply")).toHaveLength(2);
    expect(screen.queryByRole("link", { name: "View declared score" })).toBeNull();
  });

  it.each([null, "/loom/bridge_chat", "/loom/other/2", "/loom/bridge_chat/3", "https://example.org/loom/bridge_chat/2", "javascript:alert(1)"])(
    "does not offer an absent, unsafe or different score destination (%s)", async (loomPath) => {
      render(CircleRun, { runId: "run-a", turn: projection({ loomPath }) });
      await fireEvent.click(screen.getByRole("button", { name: /Circle details/ }));
      expect(screen.queryByRole("link", { name: "View declared score" })).toBeNull();
      expect(screen.getByText("Declared score link unavailable")).toBeTruthy();
    }
  );

  it.each(["/orb/other-run", "https://example.org/orb/run-a", "javascript:alert(1)"])(
    "does not navigate evidence to an unsafe or different Run (%s)", (orbPath) => {
      render(CircleRun, { runId: "run-a", turn: projection({ orbPath }) });
      expect(screen.queryByRole("link", { name: "Look into the Orb" })).toBeNull();
      expect(screen.getByText("Evidence link unavailable")).toBeTruthy();
    }
  );

  it("discards an invalid delegated selection while preserving the exact destinations", async () => {
    render(CircleRun, { runId: "run-a", turn: projection({ delegatedJobId: "../other?job=wrong" }) });
    expect(screen.getByRole("link", { name: "Look into the Orb" }).getAttribute("href")).toBe("/orb/run-a");
    await fireEvent.click(screen.getByRole("button", { name: /Circle details/ }));
    expect(screen.getByRole("link", { name: "View declared score" }).getAttribute("href")).toBe("/loom/bridge_chat/2?run=run-a");
  });

  it("retains the caller's cancellation semantics and visibly labels the action", async () => {
    const oncancel = vi.fn();
    const view = render(CircleRun, { runId: "run-a", turn: projection({ state: "stale" }), oncancel });
    const button = screen.getByRole("button", { name: "Cancel run run-a" }) as HTMLButtonElement;
    expect(button.textContent).toContain("Cancel Run");
    await fireEvent.click(button);
    expect(oncancel).toHaveBeenCalledOnce();
    await view.rerender({ cancelling: true });
    expect(button.disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe("true");
    button.click();
    expect(oncancel).toHaveBeenCalledOnce();
  });

  it.each(["done", "failed", "cancelled"] as const)("offers no cancellation for terminal state %s", (state) => {
    render(CircleRun, { runId: "run-a", turn: projection({ state }), oncancel: vi.fn() });
    expect(screen.queryByRole("button", { name: /Cancel run/ })).toBeNull();
  });

  it("updates status and destinations when the owner replaces the projection", async () => {
    const view = render(CircleRun, { runId: "run-a", turn: projection(), oncancel: vi.fn() });
    await fireEvent.click(screen.getByRole("button", { name: /Circle details/ }));
    await view.rerender({ turn: projection({ runStatus: "cancelled", activity: "cancelled", state: "cancelled", loomPath: null }) });
    expect(screen.getByText("cancelled")).toBeTruthy();
    expect(screen.queryByText("weaving")).toBeNull();
    expect(screen.queryByRole("button", { name: /Cancel run/ })).toBeNull();
    expect(screen.queryByRole("link", { name: "View declared score" })).toBeNull();
  });

  it("fences a projection belonging to a different Run", async () => {
    render(CircleRun, { runId: "run-b", turn: projection(), oncancel: vi.fn() });
    expect(screen.getByText("The supplied projection belongs to another Run.")).toBeTruthy();
    expect(screen.queryByText("running")).toBeNull();
    expect(screen.queryByText("weaving")).toBeNull();
    expect(screen.queryByRole("button", { name: /Cancel run/ })).toBeNull();
    expect(screen.queryByRole("link", { name: "Look into the Orb" })).toBeNull();
    await fireEvent.click(screen.getByRole("button", { name: /Circle details/ }));
    expect(screen.queryByRole("link", { name: "View declared score" })).toBeNull();
    expect(screen.getByText("run-b")).toBeTruthy();
    expect(screen.queryByText("bridge_chat")).toBeNull();
  });
});
