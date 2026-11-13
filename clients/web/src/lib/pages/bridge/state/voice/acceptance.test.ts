/** Synthetic port composition only: no microphone, browser UI or live speech qualification. */
import { describe, expect, it } from "vitest";
import type { DictationResult } from "$lib/api/models";
import { isCanvasCommandCurrent, planCanvasCommand } from "$lib/pages/canvas/state/commands";
import { commit, redo, undo, validateDocument } from "$lib/pages/canvas/state/engine";
import type { Document } from "$lib/pages/canvas/state/types";
import { createWorkCommandRegistry, type CommandResult, type CommandTarget } from "$lib/shell/state/work-commands";
import { createDictationCoordinator, type DictationDraft } from "./dictation";

const id = (number: number) => `00000000-0000-0000-0000-${number.toString().padStart(12, "0")}`;
const original = "add node Vessel then add database Postgress then connect Vessel to Postgress";
const corrected = "add node Vessel then add database Postgres then connect Vessel to Postgres";
const synthetic: DictationResult = {
  attempt_id: "019a4a18-3600-7000-8000-000000000001", status: "transcribed", original_text: original,
  source_digest: `sha256:${"a".repeat(64)}`, profile_digest: `sha256:${"b".repeat(64)}`,
  language: "en", reason: null
};

function fixture() {
  let document: Document = {
    format: "lychd.canvas.document/1", past: [], future: [],
    scene: {
      format: "lychd.canvas/1", id: id(900), title: "Synthetic acceptance", revision: 1,
      nodes: [{ id: id(1), label: "Unrelated", kind: "note", x: 700, y: 500,
        width: 160, height: 80, pinned: false, artwork: null, source_stroke_ids: [] }],
      edges: [], strokes: [{ id: id(2), points: [{ x: 1, y: 2 }, { x: 50, y: 60 }],
        width: 3, color: "#abcdef", archived: false }]
    }
  };
  const before = structuredClone(document);
  let selection: string[] = [];
  let state: DictationDraft = {
    sessionId: "synthetic-bridge", draftText: "", draftRevision: 0, mode: "work",
    contextEpoch: 0, targetEpoch: 0, composing: false, busy: false
  };
  const registry = createWorkCommandRegistry();
  let pending: { plan: ReturnType<typeof planCanvasCommand>; target: CommandTarget } | null = null;
  const submissions: Array<Promise<CommandResult>> = [];
  const unregister = registry.register({
    instrument: "canvas", id: document.scene.id, label: "Canvas",
    snapshot: () => ({ revisionKey: `${document.scene.id}:${document.scene.revision}`,
      selectionKey: JSON.stringify(selection), commands: ["add node", "add database", "connect"] }),
    execute(text, captured) {
      if (!registry.isCurrent(captured)) return { status: "stale", summary: "Changed" };
      pending = { plan: planCanvasCommand(document.scene, selection, text), target: captured };
      return { status: "preview", summary: pending.plan.summary };
    }
  });
  const coordinator = createDictationCoordinator({
    read: () => state,
    adopt(expected, text) {
      if (JSON.stringify(state) !== JSON.stringify(expected)) return null;
      state = { ...state, draftText: text, draftRevision: Number(state.draftRevision) + 1 };
      return state;
    },
    isTargetCurrent: registry.isCurrent,
    submit(draft, intent) {
      const delivery = registry.execute(draft.draftText, intent.target);
      submissions.push(delivery);
      return delivery;
    }
  });
  return {
    before, coordinator, registry, submissions,
    get document() { return document; },
    get pending() { return pending; },
    get state() { return state; },
    edit(text: string) {
      state = { ...state, draftText: text, draftRevision: Number(state.draftRevision) + 1 };
      coordinator.notifyChanged();
    },
    setBusy() { state = { ...state, busy: true }; coordinator.notifyChanged(); },
    select(ids: string[]) { selection = ids; registry.refresh(); },
    navigate() { registry.clear(); },
    apply() {
      const preview = pending;
      if (!preview || !registry.isCurrent(preview.target) ||
          !isCanvasCommandCurrent(preview.plan, document.scene, selection)) return false;
      document = commit(document, preview.plan.scene);
      pending = null;
      registry.refresh();
      return true;
    },
    undo() { document = undo(document); registry.refresh(); },
    redo() { document = redo(document); registry.refresh(); },
    close() { coordinator.destroy(); unregister(); }
  };
}

describe("synthetic dictation to existing Canvas document lifecycle", () => {
  it("corrects a retained original, submits once, previews inertly, applies one commit and reopens editable JSON", async () => {
    const f = fixture();
    try {
      const target = f.registry.capture();
      const capture = f.coordinator.beginCapture(synthetic.attempt_id, target);
      expect(f.coordinator.receive(capture, synthetic)).toBe(true);
      expect(f.coordinator.view.autosend).toBe(false);
      expect(f.state.draftText).toBe(original);
      f.edit(corrected);
      expect(f.coordinator.view.originalText).toBe(original);
      expect(f.coordinator.sendManual()).toBe(true);
      expect(f.coordinator.sendManual()).toBe(false);
      expect(f.coordinator.receive(capture, synthetic)).toBe(false);
      expect(await f.submissions[0]).toMatchObject({ status: "preview" });
      expect(f.submissions).toHaveLength(1);
      expect(f.document).toEqual(f.before);
      expect(f.pending?.plan.scene.nodes.slice(1).map((node) => [node.label, node.kind]))
        .toEqual([["Vessel", "box"], ["Postgres", "database"]]);
      expect(f.apply()).toBe(true);
      expect(f.apply()).toBe(false);
      expect(f.document.past).toHaveLength(1);
      expect(f.document.scene.nodes[0]).toEqual(f.before.scene.nodes[0]);
      expect(f.document.scene.strokes).toEqual(f.before.scene.strokes);
      const vessel = f.document.scene.nodes.find((node) => node.label === "Vessel")!;
      const database = f.document.scene.nodes.find((node) => node.label === "Postgres")!;
      expect(f.document.scene.edges).toEqual([expect.objectContaining({ source: vessel.id, target: database.id })]);
      expect([vessel, database].every((node) => node.artwork === null && node.source_stroke_ids.length === 0)).toBe(true);
      const applied = structuredClone(f.document.scene);
      f.undo();
      expect({ ...f.document.scene, revision: f.before.scene.revision }).toEqual(f.before.scene);
      f.redo();
      expect({ ...f.document.scene, revision: applied.revision }).toEqual(applied);
      // Same native document validation boundary used by export/import; no server save claim.
      const reopened = validateDocument(JSON.parse(JSON.stringify(f.document)));
      expect(reopened).toEqual(f.document);
      const rename = planCanvasCommand(reopened.scene, [database.id], "rename selected to PostgreSQL");
      expect(commit(reopened, rename.scene).scene.nodes.find((node) => node.id === database.id)?.label).toBe("PostgreSQL");
      expect(reopened.scene.nodes.find((node) => node.id === database.id)?.label).toBe("Postgres");
    } finally { f.close(); }
  });

  it.each(["selection", "navigation"] as const)("a %s change after preview refuses Apply without touching the document", async (change) => {
    const f = fixture();
    try {
      const capture = f.coordinator.beginCapture(synthetic.attempt_id, f.registry.capture());
      f.coordinator.receive(capture, synthetic);
      f.coordinator.sendManual();
      expect(await f.submissions[0]).toMatchObject({ status: "preview" });
      if (change === "selection") f.select([id(1)]); else f.navigate();
      expect(f.apply()).toBe(false);
      expect(f.document).toEqual(f.before);
    } finally { f.close(); }
  });

  it.each(["unknown", "refused", "unavailable"] as const)("%s transport output creates no draft or proposal", (status) => {
    const f = fixture();
    try {
      const capture = f.coordinator.beginCapture(synthetic.attempt_id, f.registry.capture());
      f.coordinator.receive(capture, { ...synthetic, status, original_text: null, reason: "outcome_unknown" });
      expect(f.state.draftText).toBe("");
      expect(f.coordinator.sendManual()).toBe(false);
      expect(f.submissions).toEqual([]);
      expect(f.pending).toBeNull();
      expect(f.document).toEqual(f.before);
    } finally { f.close(); }
  });

  it("unresolved Bridge delivery blocks work submission and route exit fences late output", () => {
    const f = fixture();
    try {
      const capture = f.coordinator.beginCapture(synthetic.attempt_id, f.registry.capture());
      f.coordinator.receive(capture, synthetic);
      f.setBusy();
      expect(f.coordinator.sendManual()).toBe(false);
      expect(f.submissions).toEqual([]);
      const late = f.coordinator.beginCapture("late-attempt", f.registry.capture());
      f.navigate();
      f.coordinator.receive(late, { ...synthetic, attempt_id: "late-attempt" });
      expect(f.coordinator.insert()).toBe(false);
      expect(f.submissions).toEqual([]);
      expect(f.document).toEqual(f.before);
    } finally { f.close(); }
  });
});
