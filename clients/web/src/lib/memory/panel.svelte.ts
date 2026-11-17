import { createContext, tick } from "svelte";
import { availableFocusTarget } from "./focus";

export type MemorySection = "working" | "notes" | "recall";

/** Shell presentation only. Each section retains its own authority and lifetime. */
export function createMemoryPanel(onOpen?: () => void) {
  let isOpen = $state(false);
  let section = $state<MemorySection>("working");
  let notesSelection = $state("manage");
  let initialized = $state<Record<MemorySection, boolean>>({ working: false, notes: false, recall: false });
  let opener: HTMLElement | null = null;
  let focusVersion = 0;
  let notesGuard: ((selection: string) => boolean) | null = null;
  let approvedNotesNavigation: string | null = null;
  let applyNotesSelection: ((selection: string) => void) | null = null;
  return {
    get isOpen() { return isOpen; },
    get section() { return section; },
    get notesSelection() { return notesSelection; },
    get initialized() { return initialized; },
    open(next: MemorySection = section, from?: HTMLElement | null) {
      ++focusVersion;
      if (!isOpen) {
        opener = from ?? (typeof document !== "undefined" && document.activeElement instanceof HTMLElement ? document.activeElement : null);
        onOpen?.();
      }
      section = next;
      initialized = { ...initialized, [next]: true };
      isOpen = true;
    },
    selectNotes(selection: string, from?: HTMLElement | null) {
      const approved = approvedNotesNavigation === selection;
      approvedNotesNavigation = null;
      if (!approved && selection !== "recall" && selection !== notesSelection && notesGuard && !notesGuard(selection)) { this.open("notes", from); return false; }
      if (selection !== "recall" && selection !== notesSelection) { notesSelection = selection; applyNotesSelection?.(selection); }
      this.open(selection === "recall" ? "recall" : "notes", from);
      return true;
    },
    clearNotesNavigationApproval() { approvedNotesNavigation = null; },
    authorizeNotesNavigation(selection: string) {
      approvedNotesNavigation = null;
      if (selection !== "recall" && selection !== notesSelection && notesGuard && !notesGuard(selection)) { this.open("notes"); return false; }
      approvedNotesNavigation = selection;
      return true;
    },
    registerNotesGuard(guard: (selection: string) => boolean, apply: (selection: string) => void) { notesGuard = guard; applyNotesSelection = apply; return () => { if (notesGuard === guard) { notesGuard = null; applyNotesSelection = null; } }; },
    retainNotesSelection(selection: string) { if (selection !== notesSelection) { notesSelection = selection; applyNotesSelection?.(selection); } },
    close() {
      isOpen = false;
      const version = ++focusVersion, target = opener;
      opener = null;
      void tick().then(() => {
        if (version !== focusVersion || isOpen) return;
        const destination = availableFocusTarget(target) ? target : [...document.querySelectorAll<HTMLElement>("[data-memory-opener],#bridge-toggle,#altar-main")].find(availableFocusTarget);
        destination?.focus({ preventScroll: true });
      });
    }
  };
}
export type MemoryPanelState = ReturnType<typeof createMemoryPanel>;
export const [getMemoryPanel, setMemoryPanel, hasMemoryPanel] = createContext<MemoryPanelState>();
