import { describe, expect, it, vi } from "vitest";
import {
  createWorkCommandRegistry, workCommandMaximumLength,
  type CommandResult, type CommandSnapshot, type CommandTarget,
  type WorkCommandRegistry, type WorkCommandSurface
} from "./work-commands";

function fixture(registry: WorkCommandRegistry = createWorkCommandRegistry()) {
  let snapshot: CommandSnapshot = { revisionKey: "rev-1", selectionKey: "a", commands: ["inspect"] };
  const execute = vi.fn((_text: string, _target: CommandTarget): CommandResult => ({ status: "applied", summary: "Inspected." }));
  const surface: WorkCommandSurface = { instrument: "loom", id: "run-1", label: "Run one", snapshot: () => snapshot, execute };
  const cleanup = registry.register(surface);
  return { registry, surface, execute, cleanup, setSnapshot(value: CommandSnapshot) { snapshot = value; } };
}

describe("shell work command registry", () => {
  it("captures without dispatch, publication, or mutation of supplied snapshots", () => {
    const state = { revisionKey: "r1", commands: ["inspect"] };
    const { registry, surface, execute } = fixture();
    registry.register({ ...surface, snapshot: () => state });
    const listener = vi.fn();
    registry.subscribe(listener);
    const target = registry.capture()!;
    registry.current();
    expect(listener).toHaveBeenCalledTimes(1);
    expect(execute).not.toHaveBeenCalled();
    expect(Object.isFrozen(state)).toBe(false);
    expect(Object.isFrozen(state.commands)).toBe(false);
    expect(Object.isFrozen(target)).toBe(true);
    expect(Object.isFrozen(target.commands)).toBe(true);
    state.commands.push("focus");
    expect(target.commands).toEqual(["inspect"]);
    expect(registry.isCurrent(target)).toBe(false);
  });

  it.each([
    { revisionKey: "rev-2", selectionKey: "a", commands: ["inspect"] },
    { revisionKey: "rev-1", selectionKey: "b", commands: ["inspect"] },
    { revisionKey: "rev-1", commands: ["inspect"] },
    { revisionKey: "rev-1", selectionKey: "a", commands: ["focus"] }
  ])("fences a changed snapshot before refresh: %j", async (next) => {
    const { registry, setSnapshot, execute } = fixture();
    const target = registry.capture();
    setSnapshot(next);
    expect((await registry.execute("inspect", target)).status).toBe("stale");
    expect(execute).not.toHaveBeenCalled();
  });

  it("refreshes without changing mount generation and invalidates captures across selection round trips", async () => {
    const { registry, setSnapshot } = fixture();
    const target = registry.capture()!;
    const listener = vi.fn();
    registry.subscribe(listener);
    registry.refresh();
    expect(listener).toHaveBeenCalledTimes(1);
    setSnapshot({ revisionKey: "rev-1", selectionKey: "b", commands: ["inspect"] });
    registry.refresh();
    const current = registry.current()!;
    expect(current.mountGeneration).toBe(target.mountGeneration);
    expect(current.selectionKey).toBe("b");
    expect(listener).toHaveBeenCalledTimes(2);
    setSnapshot({ revisionKey: "rev-1", selectionKey: "a", commands: ["inspect"] });
    registry.refresh();
    expect((await registry.execute("inspect", target)).status).toBe("stale");
    expect(registry.isCurrent(registry.capture())).toBe(true);
  });

  it("never dispatches an old mount token to a same-ID remount", async () => {
    const { registry, surface, cleanup, execute } = fixture();
    const old = registry.capture()!;
    const newer = vi.fn((): CommandResult => ({ status: "applied", summary: "New mount" }));
    const cleanupNew = registry.register({ ...surface, execute: newer });
    const current = registry.capture()!;
    expect(current.id).toBe(old.id);
    expect(current.mountGeneration).not.toBe(old.mountGeneration);
    cleanup();
    expect(registry.isCurrent(current)).toBe(true);
    expect((await registry.execute("inspect", old)).status).toBe("stale");
    expect(execute).not.toHaveBeenCalled();
    expect(newer).not.toHaveBeenCalled();
    expect((await registry.execute("inspect", current)).status).toBe("applied");
    expect(newer).toHaveBeenCalledExactlyOnceWith("inspect", current);
    cleanupNew();
    cleanupNew();
    expect(registry.current()).toBeNull();
    expect((await registry.execute("inspect", current)).status).toBe("stale");
  });

  it("clears on route exit and supports explicit invalidation with the surface retained", async () => {
    const { registry, execute } = fixture();
    const old = registry.capture();
    registry.invalidate();
    const fresh = registry.capture();
    expect((await registry.execute("inspect", old)).status).toBe("stale");
    expect(registry.isCurrent(fresh)).toBe(true);
    registry.clear();
    expect(registry.current()).toBeNull();
    expect((await registry.execute("inspect", fresh)).status).toBe("stale");
    expect((await registry.execute("inspect", null)).status).toBe("unavailable");
    expect(execute).not.toHaveBeenCalled();
  });

  it("rejects forged, copied and foreign-registry targets", async () => {
    const { registry, execute } = fixture();
    const original = registry.capture()!;
    const foreign = fixture().registry.capture();
    for (const target of [{ ...original }, foreign, { ...original, instrument: "orb" as const }]) {
      expect((await registry.execute("inspect", target)).status).toBe("stale");
    }
    expect(execute).not.toHaveBeenCalled();
  });

  it("captures surface identity and methods at registration", async () => {
    const { registry, surface, execute } = fixture();
    const target = registry.capture()!;
    const replacement = vi.fn();
    Object.assign(surface, { id: "other", instrument: "orb", execute: replacement });
    expect(registry.capture()?.id).toBe("run-1");
    await registry.execute("inspect", target);
    expect(execute).toHaveBeenCalledOnce();
    expect(replacement).not.toHaveBeenCalled();
  });

  it.each(["", " ", "a".repeat(workCommandMaximumLength + 1), null, 17, {}])("bounds command input without calling the handler", async (text) => {
    const { registry, execute } = fixture();
    expect((await registry.execute(text as string, registry.capture())).status).toBe("unsupported");
    expect(execute).not.toHaveBeenCalled();
  });

  it("admits exactly 4000 characters without rewriting text", async () => {
    const { registry, execute } = fixture();
    const text = "a".repeat(workCommandMaximumLength);
    const target = registry.capture();
    await registry.execute(text, target);
    expect(execute).toHaveBeenCalledExactlyOnceWith(text, target);
  });

  it("rejects unknown instruments without replacing a valid registration", () => {
    const { registry, surface } = fixture();
    const target = registry.capture();
    expect(() => registry.register({ ...surface, instrument: "shell" } as unknown as WorkCommandSurface)).toThrow(TypeError);
    expect(registry.isCurrent(target)).toBe(true);
  });

  it("supports independent subscription cleanup and publishes active registration changes", () => {
    const registry = createWorkCommandRegistry();
    const listener = vi.fn();
    const stopFirst = registry.subscribe(listener);
    const stopSecond = registry.subscribe(listener);
    expect(listener.mock.calls).toEqual([[null], [null]]);
    const { cleanup } = fixture(registry);
    expect(listener).toHaveBeenCalledTimes(4);
    stopFirst();
    stopFirst();
    registry.invalidate();
    expect(listener).toHaveBeenCalledTimes(5);
    stopSecond();
    cleanup();
    expect(listener).toHaveBeenCalledTimes(5);
  });

  it("does not emit an older target after a subscriber replaces it", () => {
    const registry = createWorkCommandRegistry();
    const observations: (string | undefined)[] = [];
    registry.subscribe((target) => {
      if (target?.id === "run-1") registry.register({ instrument: "orb", id: "orb-1", label: "Orb", snapshot: () => ({ revisionKey: "r", commands: [] }), execute: () => ({ status: "unsupported", summary: "No command" }) });
    });
    registry.subscribe((target) => { observations.push(target?.id); });
    fixture(registry);
    expect(observations).toEqual([undefined, "orb-1"]);
  });

  it("does not retarget an in-flight handler that registers a replacement", async () => {
    const { registry, surface } = fixture();
    const replacement = vi.fn((): CommandResult => ({ status: "applied", summary: "Replacement" }));
    const handler = vi.fn((_text: string, target: CommandTarget): CommandResult => {
      registry.register({ ...surface, execute: replacement });
      return registry.isCurrent(target) ? { status: "applied", summary: "Wrong" } : { status: "stale", summary: "Replaced before operation" };
    });
    registry.register({ ...surface, execute: handler });
    expect((await registry.execute("inspect", registry.capture())).status).toBe("stale");
    expect(handler).toHaveBeenCalledOnce();
    expect(replacement).not.toHaveBeenCalled();
  });

  it("rechecks identity when a misbehaving snapshot replaces its own entry", async () => {
    const { registry, surface, execute } = fixture();
    let replace = false;
    registry.register({ ...surface, snapshot() {
      if (replace) { replace = false; registry.register(surface); }
      return surface.snapshot();
    } });
    const target = registry.capture();
    replace = true;
    expect((await registry.execute("inspect", target)).status).toBe("stale");
    expect(execute).not.toHaveBeenCalled();
  });

  it("lets asynchronous handlers independently fence mutations after an await", async () => {
    const { registry, surface } = fixture();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const mutate = vi.fn();
    registry.register({ ...surface, async execute(_text, captured) {
      await gate;
      if (!registry.isCurrent(captured)) return { status: "stale", summary: "Target changed" };
      mutate();
      return { status: "applied", summary: "Presentation changed" };
    } });
    const pending = registry.execute("inspect", registry.capture());
    registry.clear();
    release();
    expect((await pending).status).toBe("stale");
    expect(mutate).not.toHaveBeenCalled();
  });

  it("reports handler failure without retrying or using a newer surface", async () => {
    const { registry, surface } = fixture();
    const execute = vi.fn(() => { throw new Error("private detail"); });
    registry.register({ ...surface, execute });
    expect(await registry.execute("inspect", registry.capture())).toEqual({ status: "unavailable", summary: "This work command is unavailable." });
    expect(execute).toHaveBeenCalledOnce();
  });

  it("leaves invalid or failed snapshot reads unavailable", () => {
    const { registry, surface } = fixture();
    registry.register({ ...surface, snapshot: () => { throw new Error("unavailable"); } });
    expect(registry.capture()).toBeNull();
    registry.register({ ...surface, snapshot: () => ({ revisionKey: "r", commands: [1] } as unknown as CommandSnapshot) });
    expect(registry.capture()).toBeNull();
  });

  it("keeps Canvas as a preview-only contract", async () => {
    const { registry, surface } = fixture();
    registry.register({ ...surface, instrument: "canvas", execute: () => ({ status: "preview", summary: "Review proposed nodes" }) });
    expect((await registry.execute("create node", registry.capture())).status).toBe("preview");
    registry.register({ ...surface, instrument: "canvas" });
    expect((await registry.execute("create node", registry.capture())).status).toBe("unsupported");
  });
});
