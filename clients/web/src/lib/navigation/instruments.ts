/**
 * Local review destinations under ADR 15's five-instrument contract.
 * Parsing preserves bounded identity hints only. Destination readers must still
 * validate Run ownership and the entire pinned Pattern before offering a return.
 */
export type OrbDestination = "/orb" | `/orb/${string}`;
export interface AltarNavigation { orbPath: OrbDestination }
export const altarNavigationContext = Symbol("altar-navigation");

/** Navigation hints are bounded identities, never admission or evidence authority. */
export function navigationId(value?: string | null): string | null {
  return value && /^[A-Za-z0-9][A-Za-z0-9._~-]{0,127}$/.test(value) ? value : null;
}

function pathIds(path: string, prefix: string, count: number): string[] | null {
  if (!path.startsWith(`${prefix}/`)) return null;
  const parts = path.slice(prefix.length + 1).split("/");
  if (parts.length !== count) return null;
  try {
    const ids = parts.map((part) => navigationId(decodeURIComponent(part)));
    return ids.every((id): id is string => id !== null) ? ids : null;
  } catch { return null; }
}

function selection(search: string): URLSearchParams {
  const result = new URLSearchParams();
  if (search.length > 1024) return result;
  const source = new URLSearchParams(search);
  for (const key of ["event", "job"]) {
    const value = navigationId(source.get(key));
    if (value) result.set(key, value);
  }
  return result;
}

export function orbReturnHref(runId: string, search = ""): `/orb/${string}` | null {
  const id = navigationId(runId);
  if (!id) return null;
  const query = selection(search).toString();
  return `/orb/${encodeURIComponent(id)}${query ? `?${query}` : ""}`;
}

export function selectedOrbHref(pathname: string, search: string, base = "/orb"): `/orb/${string}` | null {
  const ids = pathIds(pathname, base, 1);
  const id = ids?.[0];
  return id ? orbReturnHref(id, search) : null;
}

/** Carry review context; this syntactic check does not establish manifest equality. */
export function loomOriginHref(path: string, runId: string, search = ""): `/loom/${string}/${string}` | null {
  const ids = pathIds(path.split("?")[0] ?? "", "/loom", 2);
  const pattern = ids?.[0];
  const revision = ids?.[1];
  const run = navigationId(runId);
  if (!pattern || !revision || !run) return null;
  const query = new URLSearchParams({ run });
  for (const [key, value] of selection(search)) query.set(key, value);
  return `/loom/${encodeURIComponent(pattern)}/${encodeURIComponent(revision)}?${query}`;
}

export function bridgeRunHref(path: string, runId: string): `/bridge/${string}` | null {
  const ids = pathIds(path, "/bridge", 1);
  const run = navigationId(runId);
  const session = ids?.[0];
  return session && run ? `/bridge/${encodeURIComponent(session)}?run=${encodeURIComponent(run)}` : null;
}
