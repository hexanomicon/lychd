/** Only build-owned, bundled assets can become image URLs. Remote data supplies a key. */
const bundled = import.meta.glob<string>("../assets/runtime/*.svg", { eager: true, query: "?url", import: "default" });
const icons = new Map(Object.entries(bundled).map(([path, url]) => [`icons/${path.split("/").at(-1)}`, url]));

export function runtimeIcon(asset: string | null | undefined): string | undefined {
  return asset ? icons.get(asset) : undefined;
}
