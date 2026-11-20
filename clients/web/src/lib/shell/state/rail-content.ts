import { getContext, type Snippet } from "svelte";

export const railContentKey = Symbol("Altar navigation content");
export interface RailContent {
  section?: Snippet;
}
export const getRailContent = () => getContext<RailContent | undefined>(railContentKey);
