<script lang="ts">
  type Descriptor = {
    kind?: unknown;
    schema_version?: unknown;
    props?: unknown;
  };

  let { descriptor }: { descriptor: Descriptor } = $props();

  let kind = $derived(typeof descriptor.kind === "string" ? descriptor.kind : "genui.unknown");
  let schemaVersion = $derived(
    typeof descriptor.schema_version === "number" ? descriptor.schema_version : null
  );
  let descriptorProps = $derived(
    typeof descriptor.props === "object" && descriptor.props !== null
      ? (descriptor.props as Record<string, unknown>)
      : {}
  );
  let steps = $derived(
    Array.isArray(descriptorProps.steps)
      ? descriptorProps.steps.filter((item: unknown): item is string => typeof item === "string")
      : []
  );
  let rows = $derived(
    Array.isArray(descriptorProps.rows)
      ? descriptorProps.rows.filter(
          (item: unknown): item is Record<string, unknown> => typeof item === "object" && item !== null
        )
      : []
  );
</script>

{#if schemaVersion !== 1}
  <div class="genui" data-fragment={kind} data-state="fault" data-schema-version={schemaVersion ?? "unknown"}>
    <div class="genui-head">
      <span>Unsupported projection</span>
      <span class="glyph">schema {schemaVersion ?? "unknown"}</span>
    </div>
    <div class="genui-body">Retained inertly.</div>
  </div>
{:else if kind === "genui.plan_checklist"}
  <div class="genui" data-fragment={kind}>
    <div class="genui-head">
      <span>{String(descriptorProps.title ?? "Plan")}</span>
      <span class="glyph">descriptor · client-projected</span>
    </div>
    <ol class="genui-body checklist">
      {#each steps as step, index (index)}<li>{step}</li>{/each}
    </ol>
  </div>
{:else if kind === "genui.capability_table"}
  <div class="genui" data-fragment={kind}>
    <div class="genui-head">
      <span>Capability census</span>
      <span class="glyph">descriptor · client-projected</span>
    </div>
    <table>
      <thead><tr><th>Capability key</th><th>Family</th><th>State</th></tr></thead>
      <tbody>
        {#each rows as row, index (index)}
          <tr>
            <td class="glyph">{String(row.capability_key ?? "")}</td>
            <td>{String(row.family ?? "")}</td>
            <td><span class="chip" data-state={String(row.state ?? "cold")}>{String(row.state ?? "cold")}</span></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else if kind === "genui.vision_summary"}
  <div class="genui" data-fragment={kind}>
    <div class="genui-head">
      <span>{String(descriptorProps.title ?? "Vision")}</span>
      <span class="chip" data-state={String(descriptorProps.severity ?? "info")}>{String(descriptorProps.severity ?? "info")}</span>
    </div>
    <div class="genui-body">{String(descriptorProps.body ?? "")}</div>
  </div>
{:else}
  <div class="genui" data-fragment="genui.unknown" data-state="fault">
    <div class="genui-head"><span>Unknown projection</span><span class="glyph">{kind}</span></div>
    <div class="genui-body">The Vessel named no admitted component.</div>
  </div>
{/if}

<style>
  /* Generative-UI descriptor: Vessel-validated, client-projected. */
  .genui {
    margin-top: 11px;
    overflow: hidden;
    border: 1px solid var(--color-border-subtle);
    border-left: 2px solid var(--color-interactive-muted);
    border-radius: var(--radius-block);
    background: var(--color-surface-raised);
    animation: genui-rise var(--duration-rise) var(--ease-settle) both;
  }
  .genui-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 13px;
    border-bottom: 1px solid var(--color-border-subtle);
    color: var(--color-text-muted);
    font-size: var(--text-xs); letter-spacing: 0.08em; text-transform: uppercase;
  }
  .genui-body { padding: 11px 16px; color: var(--color-text-body); font-size: var(--text-sm); }
  .genui-body.checklist { padding: 10px 16px 12px 30px; }
  .genui-body.checklist li { padding: 3px 0; }
  .genui table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
  .genui th {
    padding: 7px 13px;
    border-bottom: 1px solid var(--color-border-subtle);
    color: var(--color-text-muted);
    font-size: var(--text-xs); font-weight: 500; letter-spacing: 0.07em; text-align: left; text-transform: uppercase;
  }
  .genui td { padding: 7px 13px; border-bottom: 1px solid color-mix(in srgb, var(--color-border-subtle) 55%, transparent); }
  .genui tr:last-child td { border-bottom: none; }
  @keyframes genui-rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .genui { animation: none; } }
</style>
