import type { Blueprint } from "./blueprint";

// A browser-tab editing buffer survives instrument navigation until the page reloads.
export const studioSession: { draft?: Blueprint; selected: string; dirty: boolean } = {
  selected: "analysis",
  dirty: false,
};
