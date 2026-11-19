/** Applications shown on the Altar rail. Pins only change local navigation. */
export const applications = [
  {
    id: "scavenger",
    name: "Scavenger",
    area: "Stewardship & Acquisition",
    detail: "Review source observations from the market.",
    href: "/scavenger",
    action: "Open market",
  },
  {
    id: "atelier",
    name: "Atelier",
    area: "Creative Works",
    detail: "Prepare a short-video brief and review a local cut.",
    href: "/atelier",
    action: "Open studio",
  },
  {
    id: "canvas",
    name: "Canvas",
    area: "Creative Works",
    detail: "Draw and revise a project board.",
    href: "/canvas",
    action: "Open boards",
  },
  {
    id: "broadcast",
    name: "Broadcast",
    area: "Creative Works",
    detail: "Prepare an edition for its outlet.",
    href: "https://hexanomicon.dev/compositions/broadcast/",
    action: "View design",
  },
  {
    id: "riffmaw",
    name: "Riffmaw",
    area: "Creative Works",
    detail: "Arrange music, cues and mixes.",
    href: "https://hexanomicon.dev/compositions/riffmaw/",
    action: "View design",
  },
  {
    id: "language",
    name: "Language Edition",
    area: "Creative Works",
    detail: "Plan dialogue, narration and timed captions.",
    href: "https://hexanomicon.dev/compositions/language-edition/",
    action: "View design",
  },
] as const;

export type Application = (typeof applications)[number];
export type ApplicationId = Application["id"];
export const defaultAppPins: ApplicationId[] = ["scavenger", "atelier"];
export const appPinsKey = "lychd.altar.application-pins.v1";
export function readAppPins(raw: string | null): ApplicationId[] {
  try {
    const items: unknown = raw && JSON.parse(raw);
    if (
      Array.isArray(items) &&
      items.length <= applications.length &&
      items.every((id) => applications.some((app) => app.id === id))
    ) {
      return [...new Set(items)] as ApplicationId[];
    }
  } catch {
    /* Fall back when a preference cannot be decoded. */
  }
  return [...defaultAppPins];
}
