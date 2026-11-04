import { resolve } from "$app/paths";
import type { Path } from "$app/types";

/** Resolve an already encoded instrument pathname with SvelteKit's deployment base. */
export function resolvePath(pathname: `/${string}`): string {
  return resolve(pathname.slice(1) as Path);
}
