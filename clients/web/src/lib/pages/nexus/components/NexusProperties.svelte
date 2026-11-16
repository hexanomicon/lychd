<script lang="ts">
  import type { NexusMapObject } from "$lib/pages/nexus/state/map";

  let {
    object,
    busy,
    allowPreview,
    previewTarget = null,
    onpreview,
    oninspect
  }: {
    object: NexusMapObject;
    busy: boolean;
    allowPreview: boolean;
    previewTarget?: string | null;
    onpreview: (key: string, opener: HTMLElement) => void;
    oninspect: (managedCapabilityKey: string, opener: HTMLElement) => void;
  } = $props();
</script>

<div class="nexus-properties">
  {#if object.kind === "capability"}
    {@const row = object.row}
    <p class="object-kind">{object.scope === "managed" ? "Managed capability" : "Portal capability · read only"}</p>
    <dl class="property-identity"><dt>Capability</dt><dd><code>{row.capability_key}</code></dd></dl>
    <dl class="property-grid">
      <dt>Animator</dt><dd><code>{row.animator_name || "not reported"}</code></dd>
      <dt>Model</dt><dd><code>{row.model_id}</code></dd>
      <dt>Runtime</dt><dd>{row.runtime}</dd>
      <dt>State</dt><dd>{row.state}</dd>
      <dt>Health</dt><dd>{row.health}</dd>
      <dt>Reason</dt><dd>{row.reason ?? "none reported"}</dd>
      <dt>Checked</dt>
      <dd>{#if row.checked_at}<time datetime={row.checked_at}>{new Date(row.checked_at).toLocaleString()}</time>{:else}freshness unknown{/if}</dd>
    </dl>
    <details class="more-properties"><summary>More properties</summary><dl class="property-grid">
      <dt>Family</dt><dd>{row.family}</dd>
      <dt>Active</dt><dd>{row.is_active ? "yes" : "no"}</dd>
      <dt>Warm</dt><dd>{row.warm ? "yes" : "no"}</dd>
      <dt>Dedicated</dt><dd>{row.dedicated ? "yes" : "no"}</dd>
      <dt>Persistent resident</dt><dd>{row.persistent_resident ? "yes" : "no"}</dd>
      <dt>Registrant</dt><dd><code>{row.registrant_id ?? "not reported"}</code></dd>
    </dl></details>
    {#if object.scope === "portal"}
      <p class="property-note">Remote observation · read only.</p>
    {:else if allowPreview}
      <button class="property-action" type="button" disabled={busy} aria-controls="nexus-preview" aria-expanded={previewTarget === row.capability_key}
        onclick={(event) => onpreview(row.capability_key, event.currentTarget)}>Preview</button>
    {/if}
  {:else if object.kind === "animator"}
    <p class="object-kind">Animator</p>
    <dl class="property-identity"><dt>Animator</dt><dd><code>{object.animator}</code></dd></dl>
    <dl class="property-grid">
      <dt>Capabilities</dt><dd>{object.rows.length} reported</dd>
      <dt>Display groups</dt><dd>{object.groups.length} reported</dd>
    </dl>
    <h3>Display groups</h3>
    <ul class="property-list">
      {#each object.groups as group (group)}<li>{group}</li>{:else}<li>none reported</li>{/each}
    </ul>
    <h3>Owned capabilities</h3>
    <ul class="owned-capabilities">
      {#each object.rows as row (row.capability_key)}
        <li><button type="button" onclick={(event) => oninspect(row.capability_key, event.currentTarget)}
          aria-label={`Inspect managed capability ${row.capability_key}`}><code>{row.capability_key}</code><span>{row.state} · health {row.health}</span></button></li>
      {:else}<li>No capabilities reported.</li>{/each}
    </ul>
  {:else}
    <p class="object-kind">Delegated runtime · read only</p>
    <dl class="property-identity"><dt>Display name</dt><dd>{object.runtime.display_name}</dd></dl>
    <dl class="property-grid">
      <dt>Runtime</dt><dd><code>{object.runtime.runtime_id}</code></dd>
      <dt>Registrant</dt><dd><code>{object.runtime.registrant_id}</code></dd>
      <dt>Transport</dt><dd>{object.runtime.transport}</dd>
      <dt>Delivery</dt><dd>{object.runtime.delivery}</dd>
      <dt>Runnable</dt><dd>{object.runtime.runnable ? "yes" : "no"}</dd>
      <dt>Provider Gate</dt><dd><code>{object.runtime.provider_gate}</code></dd>
      <dt>Coffin profiles</dt><dd>{object.runtime.coffin_profiles.length ? object.runtime.coffin_profiles.join(" · ") : "none reported"}</dd>
      <dt>Capacity posture</dt><dd><code>{object.runtime.capacity_posture}</code></dd>
    </dl>
    <p class="property-note">Capacity posture is reported configuration, not a live capacity measurement.</p>
    <h3>Limitations</h3>
    <ul class="property-list">
      {#each object.runtime.limitations as limitation (limitation)}<li>{limitation}</li>{:else}<li>No limitations reported.</li>{/each}
    </ul>
  {/if}
</div>

<style>
  .nexus-properties { min-width: 0; padding: 0 1.25rem 1.5rem; color: var(--color-parchment); font-size: var(--text-sm); }
  .object-kind { color: var(--color-ash); margin: 0 0 .5rem; }
  .property-identity { display: grid; gap: .35rem; margin: 0 0 1.5rem; padding-bottom: 1.25rem; border-bottom: 1px solid var(--color-engraving); }
  .property-identity dt { color: var(--color-ash); font-size: var(--text-sm); }
  .property-identity dd { margin: 0; color: var(--color-accent); font-size: 1.125rem; line-height: 1.5; overflow-wrap: anywhere; }
  .property-identity code { font-size: inherit; }
  .property-grid { display: grid; grid-template-columns: minmax(5rem, 0.8fr) minmax(0, 1.2fr); gap: 0.65rem 0.9rem; margin: 0; }
  .property-grid dt { color: var(--color-ash); }
  .property-grid dd { margin: 0; color: var(--color-bone); }
  .property-grid :is(dt, dd), code, time, li { min-width: 0; overflow-wrap: anywhere; white-space: normal; }

  code { font-family: var(--font-glyph); font-size: var(--text-sm); }
  h3 { color: var(--color-bone); margin: 1.25rem 0 0.65rem; font: 500 var(--text-sm)/1.4 var(--font-body); }
  .property-note { color: var(--color-ash); margin: 1rem 0 0; line-height: 1.5; }
  .more-properties { margin-top: 1.25rem; border-top: 1px solid var(--color-engraving); padding-top: .5rem; }
  .more-properties summary { min-height: 2rem; cursor: pointer; padding-block: .35rem; color: var(--color-parchment); }
  .more-properties .property-grid { padding-top: .5rem; }
  .property-list { margin: 0; padding-inline-start: 1.1rem; line-height: 1.5; }
  .property-list li + li { margin-top: 0.4rem; }
  .owned-capabilities { display: grid; gap: 0.5rem; margin: 0; padding: 0; list-style: none; }
  .owned-capabilities button { display: grid; gap: 0.35rem; width: 100%; text-align: start; }
  .owned-capabilities button span { color: var(--color-ash); font-size: var(--text-xs); }
  button { min-height: 2.75rem; border: 1px solid var(--color-control-border); border-radius: var(--radius-rune); background: var(--color-obsidian-2); color: var(--color-rune); padding: 0.65rem 0.8rem; font: inherit; overflow-wrap: anywhere; }
  .property-action { margin-top: 1.25rem; color: var(--color-void); background: var(--color-bone); border-color: var(--color-bone); font-weight: 600; }
  button:hover:not(:disabled) { border-color: var(--color-rune); }
  button:disabled { color: var(--color-ash); cursor: wait; }
  button:focus-visible { outline: 2px solid var(--color-rune); outline-offset: 3px; }
  @media (max-width: 480px) { .property-grid { grid-template-columns: minmax(4.5rem, 0.85fr) minmax(0, 1.15fr); gap: 0.65rem; } }
</style>
