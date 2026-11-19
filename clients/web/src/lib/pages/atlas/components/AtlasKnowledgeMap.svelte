<script lang="ts">
  import { onMount, type Snippet } from "svelte";
  import {
    ApiError,
    getArchiveRunRecall,
    getAtlasProject,
    getAtlasProjects,
    getBridgeSessions,
    getBridgeSnapshot,
  } from "$lib/api/client";
  import type { ArchiveRunRecall, AtlasProject } from "$lib/api/models";
  import {
    catalogueMap,
    scopedMap,
    turnSources,
    type AtlasMap,
    type Session,
    type TurnSource,
  } from "$lib/atlas/brain-map";
  import { atlasMapHref } from "$lib/atlas/navigation";
  import { atlasGlyph } from "$lib/atlas/glyph";
  import GraphCanvas from "$lib/graph/components/GraphCanvas.svelte";
  import { navigationId } from "$lib/navigation/instruments";
  import { getSeancesWorkspace, hasSeancesWorkspace } from "$lib/seances/workspace.svelte";

  let { projectId, sessionId }: { projectId: string | null; sessionId: string | null } = $props();
  const work = hasSeancesWorkspace() ? getSeancesWorkspace() : null;
  type Scope = {
    project: AtlasProject | null;
    session: Session | null;
    sources: TurnSource[];
    catalogue?: AtlasMap;
  };
  let scope = $state.raw<Scope | null>(null);
  let error = $state("");
  let loading = $state(true);
  let selectedId = $state<string | null>(null);
  let focusId = $state<string | null>(null);
  let focusRevision = $state(0);
  let mode = $state<"Map" | "List">("Map");
  let query = $state("");
  let recalls = $state.raw<ArchiveRunRecall[]>([]);
  let recallRequest = $state<string | null>(null);
  let recallError = $state<{ run: string; message: string } | null>(null);
  let controller: AbortController | undefined;
  let recallController: AbortController | undefined;

  const map = $derived(
    scope?.catalogue ??
      (scope
        ? scopedMap(
            scope.project,
            scope.session,
            scope.sources,
            scope.session ? (work?.materials.get(scope.session.id) ?? []) : [],
            recalls,
          )
        : null),
  );
  const objects = $derived(new Map(map?.nodes.map((node) => [node.id, node])));
  const selected = $derived(
    objects.get(selectedId ?? "") ??
      objects.get(scope?.session ? `session:${scope.session.id}` : "") ??
      map?.nodes[0],
  );
  const connections = $derived(
    map?.edges.filter((edge) => edge.source === selected?.id || edge.target === selected?.id) ?? [],
  );
  const visible = $derived(
    (map?.nodes ?? []).filter((item) =>
      `${item.kind} ${item.label}`.toLowerCase().includes(query.trim().toLowerCase()),
    ),
  );
  const kinds = $derived([...new Set(visible.map((item) => item.kind))]);
  const heading = $derived(scope?.session?.title ?? scope?.project?.title ?? "Knowledge map");
  const scopeName = $derived(sessionId ? "Séance map" : projectId ? "Project map" : "Atlas catalogue");

  function clearScope() {
    controller?.abort();
    recallController?.abort();
    scope = null;
    recalls = [];
    recallRequest = null;
    recallError = null;
  }
  function accessRefused() {
    clearScope();
    loading = false;
    error = "Access to this map was refused. Read again after access is restored.";
  }
  onMount(() => {
    void load();
    const stop = work?.onRefusal(accessRefused);
    return () => {
      stop?.();
      controller?.abort();
      recallController?.abort();
    };
  });
  async function load() {
    clearScope();
    const request = new AbortController();
    controller = request;
    const { signal } = request;
    loading = true;
    error = "";
    try {
      if (
        (projectId !== null && navigationId(projectId) !== projectId) ||
        (sessionId !== null && navigationId(sessionId) !== sessionId)
      )
        throw new Error("The requested map identity is invalid.");
      const project = projectId ? await getAtlasProject(projectId, signal) : null;
      if (signal.aborted) return;
      if (projectId && project?.id !== projectId) throw new Error("The requested Project was unavailable.");
      if (
        sessionId &&
        project &&
        !project.references.some((ref) => ref.kind === "session" && ref.target_id === sessionId)
      ) {
        throw new Error("This Project has no saved reference to the requested séance.");
      }
      let session: Session | null = null;
      let sources: TurnSource[] = [];
      let catalogue: AtlasMap | undefined;
      if (sessionId) {
        const result = await getBridgeSnapshot(sessionId);
        if (signal.aborted) return;
        if (result.session?.id !== sessionId) throw new Error("The requested séance was unavailable.");
        session = result.session;
        sources = await turnSources(session.turns ?? []);
      } else if (!project) {
        const [projects, sessions] = await Promise.all([
          getAtlasProjects({ signal }),
          getBridgeSessions(undefined, signal),
        ]);
        catalogue = catalogueMap(projects, sessions);
      }
      if (!signal.aborted) scope = { project, session, sources, catalogue };
    } catch (cause) {
      if (signal.aborted) return;
      if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
        accessRefused();
        work?.refuseAccess();
      } else error = cause instanceof Error ? cause.message : "The map could not be loaded.";
    } finally {
      if (!signal.aborted) loading = false;
    }
  }
  function select(id: string, center = false) {
    selectedId = id;
    if (center) {
      focusId = id;
      focusRevision++;
    }
  }
  async function readRecall(run: string) {
    recallController?.abort();
    const current = new AbortController();
    recallController = current;
    recallRequest = run;
    recallError = null;
    recalls = recalls.filter((item) => item.run_id !== run);
    try {
      const result = await getArchiveRunRecall(run, current.signal);
      if (current.signal.aborted) return;
      if (result.run_id !== run || (result.status === "recorded" && result.receipt?.run_id !== run)) {
        throw new Error("The receipt did not match this Run.");
      }
      recalls = [...recalls.filter((item) => item.run_id !== run), result];
    } catch (cause) {
      if (!current.signal.aborted)
        recallError = {
          run,
          message: cause instanceof Error ? cause.message : "Archive could not read this Run.",
        };
    } finally {
      if (!current.signal.aborted) recallRequest = null;
    }
  }
</script>

<svelte:head><title>Knowledge map · Atlas — LychD</title></svelte:head>

<div class="atlas-map">
  <header class="map-heading">
    <div>
      <nav class="crumbs" aria-label="Map scope">
        <a href="/atlas">Atlas</a><span aria-hidden="true">/</span>
        {#if projectId || sessionId}<a href={atlasMapHref()}>Knowledge map</a><span aria-hidden="true">/</span
          >{/if}
        {#if projectId && sessionId}<a href={atlasMapHref(projectId)}>{scope?.project?.title ?? "Project"}</a
          ><span aria-hidden="true">/</span>{/if}
        <span>{scopeName}</span>
      </nav>
      <h1>{heading}</h1>
    </div>
    <div class="view-switch" role="group" aria-label="Map presentation">
      {#each ["Map", "List"] as item (item)}
        <button aria-pressed={mode === item} onclick={() => (mode = item === "Map" ? "Map" : "List")}
          >{item}</button
        >
      {/each}
    </div>
  </header>
  {#if loading}
    <p class="message" role="status">Reading map sources…</p>
  {:else if error}
    <div class="message" role="alert">
      <p>{error}</p>
      <button onclick={load}>Retry map</button>
    </div>
  {:else if map}
    <div class="map-workspace">
      {#if mode === "Map"}
        <div class="field-wrap">
          <div class="field-meta">
            <b>{scopeName}</b><span>{map.nodes.length} objects · {map.edges.length} relations</span>
          </div>
          <GraphCanvas
            projection={map}
            label="Atlas knowledge map"
            presentation="atlas"
            hideMinimap
            selectedId={selected?.id}
            onselect={(id) => select(id)}
            {focusId}
            {focusRevision}
          >
            {#snippet navigator(minimap: Snippet)}
              <aside class="map-rail" aria-label="Map navigation">
                <div class="rail-head">
                  <h2>Explorer</h2>
                  <span>{map?.nodes.length}</span>
                </div>
                <label class="search"
                  ><span aria-hidden="true">⌕</span><input
                    type="search"
                    placeholder="Find an object"
                    aria-label="Find an object"
                    bind:value={query}
                  /></label
                >
                <nav class="object-tree" aria-label="Objects by type">
                  {#each kinds as kind (kind)}
                    <details open>
                      <summary
                        >{kind}<small>{visible.filter((item) => item.kind === kind).length}</small></summary
                      >
                      {#each visible.filter((item) => item.kind === kind) as item (item.id)}
                        <button
                          title={item.label}
                          aria-pressed={selected?.id === item.id}
                          onclick={() => select(item.id, true)}
                          ><i aria-hidden="true">{atlasGlyph(item.kind)}</i><span>{item.label}</span></button
                        >
                      {/each}
                    </details>
                  {:else}<p>No matching objects.</p>{/each}
                </nav>
                <section class="navigator" aria-label="Camera navigator">
                  <h2>Navigator</h2>
                  {@render minimap()}
                </section>
              </aside>
            {/snippet}
          </GraphCanvas>
        </div>
      {:else}
        <section class="map-list" aria-label="Map object list">
          <div class="list-head">
            <h2>Objects and relations</h2>
            <label class="search"
              ><input
                type="search"
                placeholder="Find an object"
                aria-label="Find an object"
                bind:value={query}
              /></label
            >
          </div>
          {#each visible as item (item.id)}
            <button class="object-row" aria-pressed={selected?.id === item.id} onclick={() => select(item.id)}
              ><i aria-hidden="true">{atlasGlyph(item.kind)}</i><strong>{item.label}</strong><small
                >{item.kind}</small
              ></button
            >
          {:else}<p>No matching objects.</p>{/each}
        </section>
      {/if}
      <aside class="inspector" aria-label="Map inspector">
        {#if selected}
          <header>
            <h2>Inspector</h2>
            <span class="type-symbol" aria-hidden="true">{atlasGlyph(selected.kind)}</span>
          </header>
          <div class="inspect-body">
            <p class="object-kind">{selected.kind}</p>
            {#if selected.kind === "source turn"}
              <h3>
                {selected.facts?.find(([name]) => name === "Role")?.[1] === "user"
                  ? "User turn"
                  : "Agent turn"}
              </h3>
              <blockquote>{selected.detail || "No text retained."}</blockquote>
            {:else}
              <h3>{selected.label}</h3>
              {#if selected.detail && selected.detail !== selected.label}<p class="detail">
                  {selected.detail}
                </p>{/if}
            {/if}
            {#each selected.links ?? [] as link (link.href)}<a class="destination" href={link.href}
                >{link.label} <span aria-hidden="true">↗</span></a
              >{/each}
            {#if mode === "Map"}<button
                class="focus"
                onclick={() => {
                  if (selected) select(selected.id, true);
                }}>Focus object</button
              >{/if}
            <h4>Provenance</h4>
            <dl>
              <dt>Source</dt>
              <dd>{selected.origin}</dd>
              {#each selected.facts ?? [] as [name, value] (name)}<dt>{name}</dt>
                <dd>{value || "None recorded"}</dd>{/each}
            </dl>
            <h4>Relations <small>{connections.length}</small></h4>
            {#each connections as edge (edge.id)}
              {@const outgoing = selected.id === edge.source}
              {@const other = objects.get(outgoing ? edge.target : edge.source)}
              {#if other}<button class="relation" onclick={() => select(other.id)}
                  ><small>{outgoing ? "→" : "←"} {edge.label}</small><span>{other.label}</span></button
                >{/if}
            {:else}<p>No relations in this scope.</p>{/each}
            {#if selected.recallRun}
              {@const run = selected.recallRun}
              {@const result = recalls.find((item) => item.run_id === run)}
              <h4>Memory</h4>
              {#if result}<p>
                  {result.status === "recorded"
                    ? `${result.receipt?.selected.length ?? 0} public-source revisions selected.`
                    : result.status === "not_applicable"
                      ? "Recall does not apply to this Run."
                      : "No matching Recall receipt was recorded."}
                </p>{/if}
              {#if recallError?.run === run}<p role="alert">{recallError.message}</p>{/if}
              <button disabled={recallRequest === run} onclick={() => readRecall(run)}
                >{recallRequest === run ? "Reading Recall…" : "Inspect Recall"}</button
              >
            {/if}
          </div>
        {/if}
      </aside>
    </div>
  {/if}
</div>

<style>
  .atlas-map {
    --graph-map-width: clamp(158px, 15vw, 210px);
    --atlas-height: clamp(500px, calc(100dvh - 175px), 930px);
    width: 100%;
    min-width: 0;
    color: var(--color-bone);
    font: 14px/1.5 var(--font-body);
  }
  .map-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1.05rem clamp(1rem, 2vw, 2rem) 1.15rem;
  }
  .crumbs {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    color: var(--color-ash);
    font: 11px/1.5 var(--font-glyph);
  }
  a {
    color: var(--color-rune);
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
  h1 {
    margin: 0.26rem 0 0;
    font: 500 clamp(23px, 2.3vw, 35px)/1.18 var(--font-rune);
    overflow-wrap: anywhere;
  }
  h2,
  h3,
  h4,
  p,
  dl,
  blockquote {
    margin: 0;
  }
  button,
  input {
    font: inherit;
  }
  button {
    color: var(--color-parchment);
    border: 1px solid var(--color-control-border);
    border-radius: 5px;
    background: var(--color-obsidian);
    padding: 0.34rem 0.62rem;
    cursor: pointer;
  }
  button:hover,
  a:hover {
    color: var(--color-frost);
  }
  .view-switch {
    display: flex;
    padding: 3px;
    border: 1px solid var(--color-engraving);
    border-radius: 6px;
    flex: none;
  }
  .view-switch button {
    padding: 4px 13px;
    border: 0;
    font-size: 12px;
    background: transparent;
  }
  .view-switch button[aria-pressed="true"],
  .object-tree button[aria-pressed="true"],
  .object-row[aria-pressed="true"] {
    background: color-mix(in srgb, var(--color-rune) 13%, var(--color-obsidian));
    color: var(--color-frost);
  }
  .map-workspace {
    display: grid;
    grid-template-columns: minmax(0, 1fr) clamp(190px, 19vw, 310px);
    min-width: 0;
    border-block: 1px solid var(--color-engraving);
  }
  .field-wrap {
    position: relative;
    min-width: 0;
  }
  .field-wrap :global(.svelte-flow) {
    background-color: var(--color-void);
    background-image: radial-gradient(
      circle,
      color-mix(in srgb, var(--color-rune-dim) 29%, transparent) 0.8px,
      transparent 1px
    );
    background-size: 20px 20px;
  }
  .field-meta {
    position: absolute;
    z-index: 1;
    pointer-events: none;
    top: 15px;
    left: calc(var(--graph-map-width) + 16px);
    display: flex;
    flex-direction: column;
    padding: 5px 9px;
    border-left: 2px solid var(--color-accent);
    background: color-mix(in srgb, var(--color-void) 86%, transparent);
    font: 10px/1.5 var(--font-glyph);
    color: var(--color-ash);
  }
  .field-meta b {
    color: var(--color-parchment);
    font-weight: 500;
  }
  .map-rail,
  .inspector,
  .map-list {
    background: var(--color-obsidian);
    min-width: 0;
  }
  .map-rail {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    border-right: 1px solid var(--color-engraving);
    padding: 14px 12px;
  }
  .rail-head,
  .inspector header,
  .list-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  h2,
  h4 {
    color: var(--color-parchment);
    font: 600 11px/1.45 var(--font-glyph);
    text-transform: uppercase;
    letter-spacing: 0.11em;
  }
  small,
  .rail-head > span {
    color: var(--color-ash);
    font: 10px/1.4 var(--font-glyph);
  }
  .search {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    border: 1px solid var(--color-engraving);
    border-radius: 4px;
    background: var(--color-void);
    padding: 4px 7px;
    margin: 0.7rem 0 0.5rem;
  }
  .search input {
    width: 100%;
    min-width: 0;
    background: transparent;
    border: 0;
    color: var(--color-bone);
    font-size: 12px;
  }
  .object-tree {
    overflow: auto;
    min-height: 0;
    flex: 1;
  }
  .object-tree details {
    padding: 4px 0 5px;
  }
  summary {
    cursor: pointer;
    font: 500 10px/1.6 var(--font-glyph);
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--color-ash);
  }
  summary small {
    float: right;
    letter-spacing: 0;
  }
  .object-tree button {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 2px 0;
    padding: 6px 5px;
    border: 0;
    text-align: left;
    font-size: 12px;
  }
  .object-tree button span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  i,
  .type-symbol {
    color: var(--color-accent);
    font-style: normal;
  }
  .navigator {
    padding-top: 12px;
    border-top: 1px solid var(--color-engraving);
  }
  .navigator h2 {
    margin-bottom: 7px;
  }
  .inspector {
    height: var(--atlas-height);
    overflow: auto;
    border-left: 1px solid var(--color-engraving);
  }
  .inspector header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-engraving);
  }
  .type-symbol {
    font-size: 18px;
  }
  .inspect-body {
    padding: 17px 16px;
    overflow-wrap: anywhere;
  }
  .object-kind {
    font: 500 10px/1.4 var(--font-glyph);
    color: var(--color-accent);
    text-transform: uppercase;
    letter-spacing: 0.09em;
  }
  h3 {
    margin: 0.4rem 0 0.7rem;
    font: 500 21px/1.21 var(--font-rune);
  }
  .detail,
  .inspect-body p,
  .object-tree p {
    font-size: 12px;
    color: var(--color-parchment);
  }
  .inspect-body .object-kind {
    color: var(--color-accent);
    font-size: 10px;
  }
  blockquote {
    margin: 0.8rem 0;
    padding: 5px 0 5px 10px;
    border-left: 2px solid var(--color-rune);
    font-size: 14px;
    white-space: pre-wrap;
  }
  .destination,
  .focus {
    display: block;
    margin-top: 8px;
    font-size: 12px;
  }
  .destination span {
    margin-left: 4px;
  }
  h4 {
    margin: 1rem 0 0.5rem;
    padding-top: 0.8rem;
    border-top: 1px solid var(--color-engraving);
  }
  dt,
  .relation small {
    color: var(--color-ash);
    font: 10px/1.4 var(--font-glyph);
  }
  dd {
    margin: 0 0 0.45rem;
    font-size: 12px;
    overflow-wrap: anywhere;
  }
  .relation {
    display: flex;
    flex-direction: column;
    gap: 2px;
    width: 100%;
    text-align: left;
    margin: 3px 0;
    padding: 0.35rem 0.45rem;
    border-color: var(--color-engraving);
    font-size: 12px;
  }
  .relation span {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .map-list {
    height: var(--atlas-height);
    overflow: auto;
    padding: 15px;
  }
  .list-head {
    margin-bottom: 0.8rem;
  }
  .object-row {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    margin: 3px 0;
    text-align: left;
  }
  .object-row strong {
    flex: 1;
    font-weight: 500;
    overflow-wrap: anywhere;
  }
  .message {
    margin: 1rem;
  }
  @media (max-width: 850px) {
    .atlas-map {
      --graph-map-width: 145px;
    }
    .map-workspace {
      grid-template-columns: minmax(0, 1fr) 180px;
    }
    .map-rail,
    .inspect-body {
      padding: 10px;
    }
  }
  @media (max-width: 650px) {
    .atlas-map {
      --graph-map-width: 115px;
      --atlas-height: 480px;
    }
    .map-workspace {
      grid-template-columns: minmax(0, 1fr);
    }
    .map-rail {
      padding: 8px;
    }
    .inspector {
      height: auto;
      border-left: 0;
      border-top: 1px solid var(--color-engraving);
    }
    .map-heading {
      padding: 0.75rem;
    }
    .field-meta {
      left: calc(var(--graph-map-width) + 6px);
      top: 6px;
    }
    .view-switch button {
      padding: 3px 8px;
    }
  }
</style>
