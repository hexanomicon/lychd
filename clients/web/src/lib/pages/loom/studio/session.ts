import type { Blueprint } from "./blueprint";
import type { Recipe } from "$lib/compositions/video";

export type StudioKey = Recipe | "sdlc";
interface EditingBuffer { draft?: Blueprint; selected: string; dirty: boolean; }
const buffers = new Map<StudioKey, EditingBuffer>();

// Each local document survives navigation independently until this browser tab reloads.
export const studioSession = {
  buffer(key: StudioKey): EditingBuffer {
    let buffer = buffers.get(key);
    if (!buffer) {
      buffer = { selected: key === "sdlc" ? "analysis" : "direction", dirty: false };
      buffers.set(key, buffer);
    }
    return buffer;
  },
  get dirty() { return [...buffers.values()].some(buffer => buffer.dirty); }
};
