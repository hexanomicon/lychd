<script lang="ts">
  import { alternatives, localReference, fieldTypes, objectValue, parseSchema, properties, renameField, requiredField, typeLabel, type Schema } from "./schema-fields";
  let { source, onchange, title = "Output schema" }: { source: string; onchange?: (source: string) => void; title?: string } = $props();
  let schema = $derived(parseSchema(source));
  let error = $state("");
  function save(next: Schema) {
    error = "";
    onchange?.(JSON.stringify(next));
  }
  function add(group: Schema, replace: (value: Schema) => void) {
    const fields = properties(group);
    let key = "parameter";
    for (let n = 2; Object.hasOwn(fields, key); n++) key = "parameter_" + n;
    replace({ ...group, properties: { ...fields, [key]: { type: "string" } } });
  }
  function rename(group: Schema, key: string, input: HTMLInputElement, replace: (value: Schema) => void) {
    try { replace(renameField(group, key, input.value.trim())); }
    catch (e) { error = e instanceof Error ? e.message : "Invalid parameter name."; input.value = key; }
  }
  function remove(group: Schema, key: string, replace: (value: Schema) => void) {
    const fields = { ...properties(group) };
    delete fields[key];
    replace({ ...requiredField(group, key, false), properties: fields });
  }
</script>

{#snippet fields(group: Schema, replace: (value: Schema) => void, depth: number, editable: boolean, visited: string[])}
  {@const values = properties(group)}
  {#each Object.entries(values) as [key, raw] (key)}
    {@const field = objectValue(raw) ? raw : {}}
    {@const isRequired = Array.isArray(group.required) && group.required.includes(key)}
    {@const patch = (next: Schema) => replace({ ...group, properties: { ...values, [key]: next } })}
    <details class="parameter">
      <summary><strong>{key}</strong><code>{typeLabel(raw)}</code><span>{isRequired ? "Required" : "Optional"}</span></summary>
      <div class="field-body">
        {#if editable && objectValue(raw)}
          <div class="edit-grid">
            <label>Name<input value={key} onchange={(e) => rename(group, key, e.currentTarget, replace)} /></label>
            {#if !field.$ref && !alternatives(field).length}<label>Type<select value={typeof field.type === "string" ? field.type : ""} onchange={(e) => patch({ ...field, type: e.currentTarget.value })}>
              <option value="" disabled>As declared</option>
              {#each fieldTypes as t (t)}<option value={t}>{t}</option>{/each}
            </select></label>{/if}
          </div>
          <label>Description<input value={typeof field.description === "string" ? field.description : ""} oninput={(e) => patch({ ...field, description:e.currentTarget.value })} /></label>
          <div class="field-actions"><label><input type="checkbox" checked={isRequired} onchange={(e) => replace(requiredField(group, key, e.currentTarget.checked))} /> Required</label><button type="button" onclick={() => remove(group, key, replace)}>Remove</button></div>
        {:else if typeof field.description === "string"}<p>{field.description}</p>{/if}
        {@render structure(field, patch, depth + 1, editable, visited)}
        {#if Array.isArray(field.enum)}<p>Allowed · {field.enum.map(value => JSON.stringify(value)).join(", ")}</p>{/if}
      </div>
    </details>
  {/each}
  {#if editable}<button type="button" class="add" onclick={() => add(group, replace)}>＋ Add parameter</button>{/if}
{/snippet}

{#snippet structure(field: Schema, replace: (value: Schema) => void, depth: number, editable: boolean, visited: string[])}
  {#if depth >= 10}
    <p>Further levels are available in the exported definition.</p>
  {:else if typeof field.$ref === "string"}
    {@const ref = field.$ref}
    {@const definition = schema && localReference(schema, ref)}
    {#if !definition}<p>Reference · <code>{ref}</code></p>
    {:else if visited.includes(ref)}<p>Recursive reference · <code>{ref}</code></p>
    {:else}<p>Shared definition · <code>{ref}</code></p>
      {@render structure(definition, replace, depth + 1, false, [...visited, ref])}
    {/if}
  {:else if alternatives(field).length}
    {#each alternatives(field) as alternative, i (i)}
      <details class="parameter"><summary><strong>{field.allOf ? "Constraint" : "Alternative"} {i+1}</strong><code>{typeLabel(alternative)}</code></summary>
        {#if objectValue(alternative)}<div class="field-body">{@render structure(alternative, replace, depth+1, false, visited)}</div>{/if}
      </details>
    {/each}
  {:else if field.type === "array" || field.items}
    {@const item = objectValue(field.items) ? field.items : {}}
    {@const itemIsSimple = !item.$ref && !alternatives(item).length && !Array.isArray(field.items) && field.items !== false}
    <p>Items · {typeLabel(field.items)}</p>
    {#if editable && itemIsSimple}
      <label>Item type<select value={typeof item.type === "string" ? item.type : ""} onchange={(event) => replace({ ...field, items: { ...item, type: event.currentTarget.value } })}>
        <option value="" disabled>As declared</option>{#each fieldTypes as t (t)}<option value={t}>{t}</option>{/each}
      </select></label>
    {/if}
    {@render structure(item, next => replace({ ...field, items: next }), depth+1, editable && itemIsSimple, visited)}
  {:else if field.type === "object" || objectValue(field.properties) || (depth === 0 && !field.type)}
    {#if Array.isArray(field.required)}
      {@const names = field.required.filter(name => typeof name === "string" && !Object.hasOwn(properties(field), name))}
      {#if names.length}<p>Required with unspecified type · {names.join(", ")}</p>{/if}
    {/if}
    {@render fields(field, replace, depth, editable, visited)}
  {/if}
{/snippet}

<section class="schema-fields" aria-label={title}>
  <header><h3>{title}</h3>{#if schema}<code>{typeLabel(schema)}</code>{/if}</header>
  {#if schema}
    {#if typeof schema.title === "string"}<p class="schema-title">{schema.title}</p>{/if}
    {#if !Object.keys(properties(schema)).length && schema.type === "object" && !Array.isArray(schema.required)}<p>No named parameters declared.</p>{/if}
    {#if schema.type && !["array","object"].includes(String(schema.type))}<div class="scalar"><strong>Result</strong><code>{typeLabel(schema)}</code></div>{/if}
    {@render structure(schema, save, 0, !!onchange, [])}
  {:else}<p>The supplied schema could not be read.</p>{/if}
  {#if error}<p role="alert">{error}</p>{/if}
</section>
<style>
  .schema-fields{min-width:0;color:var(--color-bone);font:12px/1.5 var(--font-body)}
  header,.scalar,.field-actions{display:flex;align-items:center;justify-content:space-between;gap:.6rem}
  header{padding:.2rem 0 .45rem} h3{font:600 .82rem/1.3 var(--font-body);margin:0}
  .parameter{border-top:1px solid var(--color-engraving)} summary{display:flex;align-items:baseline;gap:.5rem;padding:.5rem .1rem;list-style:none;cursor:pointer}
  summary::before{content:"›";color:var(--color-ash)} details[open]>summary::before{transform:rotate(90deg)}
  summary strong{flex:1;overflow-wrap:anywhere;font-weight:550} summary span{font-size:10px;color:var(--color-ash)}
  code{font:10px var(--font-glyph);color:var(--color-frost);overflow-wrap:anywhere}
  .field-body{padding:.2rem .2rem .5rem .8rem;display:grid;gap:.4rem} .edit-grid{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(5rem,1fr);gap:.5rem}
  label{display:grid;gap:.2rem;color:var(--color-ash);font-size:11px} input:not([type="checkbox"]),select{width:100%;min-width:0;box-sizing:border-box;background:var(--color-void);color:var(--color-bone);border:1px solid var(--color-engraving);border-radius:4px;padding:.25rem}
  .field-actions label{display:flex;align-items:center;gap:.3rem}.field-actions button,.add{font:inherit;color:var(--color-parchment);background:transparent;border:0;cursor:pointer}.add{padding:.45rem 0;color:var(--color-frost)}
  p{margin:0 0 .4rem;font-size:11px;color:var(--color-ash)}.scalar{padding:.4rem 0;border-top:1px solid var(--color-engraving)}
</style>
