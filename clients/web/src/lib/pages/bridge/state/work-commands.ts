/** Shell-local presentation routing. This is neither a tool executor nor durable authority. */
export const workCommandKey = Symbol("lychd.work-commands");
export const workCommandMaximumLength = 4000;

export type WorkInstrument = "canvas" | "loom" | "orb";
export interface CommandSnapshot {
  readonly revisionKey: string;
  readonly selectionKey?: string;
  readonly commands: readonly string[];
}
export interface CommandTarget extends CommandSnapshot {
  readonly instrument: WorkInstrument;
  readonly id: string;
  readonly label: string;
  readonly mountGeneration: symbol;
}
export interface CommandResult {
  /** `applied` means a presentation operation only. Canvas must return `preview`. */
  readonly status: "preview" | "applied" | "unsupported" | "stale" | "unavailable";
  readonly summary: string;
}
export interface WorkCommandSurface {
  readonly instrument: WorkInstrument;
  readonly id: string;
  readonly label: string;
  /** Pure read: return fresh values or immutable state; never register or mutate here. */
  snapshot(): CommandSnapshot;
  /** Deterministic closed parser; revalidate captured immediately before any mutation. */
  execute(text: string, captured: CommandTarget): Promise<CommandResult> | CommandResult;
}
export interface WorkCommandRegistry {
  register(surface: WorkCommandSurface): () => void;
  subscribe(listener: (target: CommandTarget | null) => void): () => void;
  current(): CommandTarget | null;
  capture(): CommandTarget | null;
  isCurrent(target: CommandTarget | null): boolean;
  execute(text: string, captured: CommandTarget | null): Promise<CommandResult>;
  /** Call after a revision, selection or declared-command change. Does not remount. */
  refresh(): void;
  /** Fence pending captures while retaining the mounted surface. */
  invalidate(): void;
  /** Route exit: remove the active surface and fence all pending captures. */
  clear(): void;
}

interface Entry {
  readonly instrument: WorkInstrument;
  readonly id: string;
  readonly label: string;
  readonly mountGeneration: symbol;
  readonly snapshot: () => CommandSnapshot;
  readonly execute: WorkCommandSurface["execute"];
  epoch: object;
  published: CommandSnapshot | null;
}
interface Capture { readonly entry: Entry; readonly epoch: object }

function copySnapshot(value: CommandSnapshot): CommandSnapshot | null {
  if (!value || typeof value.revisionKey !== "string" ||
      (value.selectionKey !== undefined && typeof value.selectionKey !== "string") ||
      !Array.isArray(value.commands) || value.commands.some((command) => typeof command !== "string")) {
    return null;
  }
  return Object.freeze({
    revisionKey: value.revisionKey,
    ...(value.selectionKey === undefined ? {} : { selectionKey: value.selectionKey }),
    commands: Object.freeze([...value.commands])
  });
}

function sameSnapshot(a: CommandSnapshot | null, b: CommandSnapshot | null): boolean {
  return a === b || (a !== null && b !== null && a.revisionKey === b.revisionKey &&
    a.selectionKey === b.selectionKey && a.commands.length === b.commands.length &&
    a.commands.every((command, index) => command === b.commands[index]));
}

const stale = (): CommandResult => ({ status: "stale", summary: "The work target changed. Capture the current target again." });
const unavailable = (): CommandResult => ({ status: "unavailable", summary: "This work command is unavailable." });

export function createWorkCommandRegistry(): WorkCommandRegistry {
  let active: Entry | null = null;
  let notificationVersion = 0;
  const captures = new WeakMap<CommandTarget, Capture>();
  const listeners = new Set<(target: CommandTarget | null) => void>();

  function read(entry: Entry): CommandSnapshot | null {
    try { return copySnapshot(entry.snapshot()); }
    catch { return null; }
  }

  function capture(): CommandTarget | null {
    const entry = active;
    if (!entry) return null;
    const epoch = entry.epoch;
    const snapshot = read(entry);
    if (!snapshot || active !== entry || entry.epoch !== epoch) return null;
    const target = Object.freeze({
      ...snapshot,
      instrument: entry.instrument,
      id: entry.id,
      label: entry.label,
      mountGeneration: entry.mountGeneration
    });
    captures.set(target, { entry, epoch });
    return target;
  }

  function isCurrent(target: CommandTarget | null): boolean {
    if (!target || typeof target !== "object") return false;
    const captured = captures.get(target);
    if (!captured || active !== captured.entry || captured.entry.epoch !== captured.epoch) return false;
    const snapshot = read(captured.entry);
    return active === captured.entry && captured.entry.epoch === captured.epoch &&
      target.mountGeneration === captured.entry.mountGeneration && sameSnapshot(target, snapshot);
  }

  function publish(): void {
    const version = ++notificationVersion;
    const target = capture();
    for (const listener of [...listeners]) {
      // A subscriber can synchronously replace the surface. Never follow that with an old update.
      if (version !== notificationVersion) break;
      if (listeners.has(listener)) listener(target);
    }
  }

  return {
    register(surface) {
      if (!surface || !["canvas", "loom", "orb"].includes(surface.instrument) ||
          typeof surface.id !== "string" || !surface.id.trim() ||
          typeof surface.label !== "string" || !surface.label.trim() ||
          typeof surface.snapshot !== "function" || typeof surface.execute !== "function") {
        throw new TypeError("Invalid work command surface");
      }
      const entry: Entry = {
        instrument: surface.instrument, id: surface.id, label: surface.label,
        mountGeneration: Symbol("work-command-mount"), epoch: {}, published: null,
        snapshot: surface.snapshot.bind(surface), execute: surface.execute.bind(surface)
      };
      active = entry;
      entry.published = read(entry);
      if (active === entry) publish();
      return () => {
        if (active !== entry) return;
        active = null;
        publish();
      };
    },
    subscribe(listener) {
      // Each subscription owns its cleanup, even when callers reuse the same callback.
      const subscription = (target: CommandTarget | null) => listener(target);
      listeners.add(subscription);
      subscription(capture());
      return () => { listeners.delete(subscription); };
    },
    current: capture,
    capture,
    isCurrent,
    async execute(text, target) {
      if (typeof text !== "string" || text.length > workCommandMaximumLength || !text.trim()) {
        return { status: "unsupported", summary: "Enter a command of 1 to 4000 characters." };
      }
      if (!target) return unavailable();
      if (!isCurrent(target)) return stale();
      // Read the exact validated entry, never whichever surface is active after an await.
      const captured = captures.get(target)!;
      try {
        const result = await captured.entry.execute(text, target);
        if (captured.entry.instrument === "canvas" && result.status === "applied") {
          return { status: "unsupported", summary: "Canvas commands require an explicit preview and Apply." };
        }
        return result;
      } catch {
        // No retry: a throwing handler may already have performed a presentation operation.
        return unavailable();
      }
    },
    refresh() {
      const entry = active;
      if (!entry) return;
      const snapshot = read(entry);
      if (active !== entry || sameSnapshot(entry.published, snapshot)) return;
      entry.published = snapshot;
      entry.epoch = {};
      publish();
    },
    invalidate() {
      if (!active) return;
      active.epoch = {};
      publish();
    },
    clear() {
      if (!active) return;
      active = null;
      publish();
    }
  };
}
