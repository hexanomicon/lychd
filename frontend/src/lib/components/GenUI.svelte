<script lang="ts">
  type Descriptor = {
    kind?: unknown;
    props?: unknown;
  };

  let { descriptor } = $props<{ descriptor: Descriptor }>();

  let kind = $derived(typeof descriptor.kind === "string" ? descriptor.kind : "genui.unknown");
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

{#if kind === "genui.plan_checklist"}
  <div class="genui" data-fragment={kind}>
    <div class="genui-head">
      <span>{String(descriptorProps.title ?? "Plan")}</span>
      <span class="glyph">descriptor · client-projected</span>
    </div>
    <ol class="genui-body checklist">
      {#each steps as step}<li>{step}</li>{/each}
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
        {#each rows as row}
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
