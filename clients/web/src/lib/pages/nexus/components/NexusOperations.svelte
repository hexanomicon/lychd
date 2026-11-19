<script lang="ts">
  import { resolvePath as resolve } from "$lib/navigation/paths";
  import type { NexusSnapshot } from "$lib/api/models";
  import type { Operation } from "../state/operations";
  import NexusInventory from "./NexusInventory.svelte";

  let { area, snapshot }: { area: Operation; snapshot: NexusSnapshot } = $props();
  const config = $derived(snapshot.configuration);
  const operator = $derived(snapshot.operator);
  const managed = $derived(snapshot.board.covens.flatMap(([, rows]) => rows));
  const configuredRoutes = $derived([...(config?.bridge_preference ?? [])].sort((a, b) => b.weight - a.weight || (a.capability_key < b.capability_key ? -1 : 1)));
  let routeKey = $state("");
  let candidates = $state.raw<string[]>([]);
  let addMessage = $state("");
  let routeSource = $state("");
  let priority = $state<number | undefined>();
  const sourceRule = $derived(config?.routing.find(rule => rule.source === routeSource) ?? config?.routing[0]);
  let queue = $state("");
  let interactive = $state<number | undefined>();
  let background = $state<number | undefined>();
  let producer = $state("Ecstatic Harmonizer");
  let receiver = $state("Exploration");
  let influence = $state(50);
  let affectRoutes = $state.raw<{ producer: string; receiver: string; weight_percent: number }[]>([]);
  let question = $state("");
  let criterion = $state("");
  let probes = $state(3);
  let skill = $state("");
  let skillSchema = $state("");
  let disclosure = $state("");
  let peer = $state("");
  let peerSchema = $state("");
  let purpose = $state("");
  let principal = $state("");
  let group = $state("");
  let role = $state("");
  let action = $state("altar:read");
  let object = $state("");
  let reason = $state("");
  let minutes = $state(15);

  function addCandidate() {
    const key = routeKey.trim();
    if (!key) return;
    if (candidates.includes(key)) {
      addMessage = "This capability is already in the order.";
      return;
    }
    candidates = [...candidates, key];
    addMessage = "";
    routeKey = "";
  }

  function move(key: string, delta: number) {
    const from = candidates.indexOf(key);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= candidates.length) return;
    const ordered = [...candidates];
    ordered.splice(from, 1);
    ordered.splice(to, 0, key);
    candidates = ordered;
  }

  function recordRoute() {
    const updated = { producer, receiver, weight_percent: influence };
    affectRoutes = [...affectRoutes.filter(route => route.producer !== producer || route.receiver !== receiver), updated];
  }

  const proposal = $derived.by(() => {
    switch (area.id) {
      case "installation": {
        if (!config || (interactive === undefined && background === undefined)) return null;
        const jobs = { interactive_concurrency: interactive ?? config.interactive_concurrency, background_concurrency: background ?? config.background_concurrency };
        return Object.values(jobs).every(value => Number.isInteger(value) && value >= 1 && value <= 128) ? { jobs } : null;
      }
      case "orchestration": {
        if (!sourceRule || (!queue && priority === undefined)) return null;
        const selected = priority ?? sourceRule.priority;
        return Number.isInteger(selected) && selected >= 0 && selected <= 100 ? { source: sourceRule.source, queue: queue || sourceRule.queue, priority: selected } : null;
      }
      case "fallback": return candidates.length ? { ordered_capabilities: candidates, selection: "before_admission", on_exhaustion: "decline", after_dispatch: "retain_exact_binding" } : null;
      case "affect": return affectRoutes.length ? { routes: affectRoutes, baseline: "positive", evaluation: "independent_evidence" } : null;
      case "exploration": return question.trim() && criterion.trim() && Number.isInteger(probes) && probes >= 1 && probes <= 100 ? { question: question.trim(), evidence_criterion: criterion.trim(), probe_ceiling: probes, stop_on: ["saturation", "budget_exhausted"] } : null;
      case "skills": return skill.trim() && skillSchema.trim() && disclosure.trim() ? { public_skill: skill.trim(), task_schema: skillSchema.trim(), audience: disclosure.trim() } : null;
      case "peers": return peer.trim() && peerSchema.trim() && purpose.trim() ? { peer_identity: peer.trim(), task_schema: peerSchema.trim(), purpose: purpose.trim() } : null;
      case "access": return principal.trim() && object.trim() && reason.trim() && Number.isInteger(minutes) && minutes >= 1 && minutes <= 1440 ? { subject: principal.trim(), group: group.trim() || null, role: role.trim() || null, action, object: object.trim(), audience: "Nexus", duration_minutes: minutes, justification: reason.trim() } : null;
      default: return null;
    }
  });
  const documentText = $derived(proposal ? JSON.stringify({ kind: "nexus-operator-proposal", area: area.id, proposal }, null, 2) : "");
</script>

{#if area.id === "inventory"}
  <NexusInventory {snapshot} />
{:else if area.id === "installation"}
  <p class="intro">Startup settings for this Vessel.</p>
  {#if config}
    <dl class="facts"><dt>Persistence</dt><dd>{config.database_profile}</dd><dt>Server port</dt><dd>{config.server_port}</dd><dt>Built-in extensions</dt><dd>{config.builtin_extensions.join(", ") || "None enabled"}</dd><dt>Crypt extensions</dt><dd>{config.crypt_extensions.join(", ") || "None enabled"}</dd></dl>
    <h3>Worker capacity</h3>
    <table><thead><tr><th>Pool</th><th>Configured jobs</th></tr></thead><tbody><tr><td>Interactive</td><td>{config.interactive_concurrency}</td></tr><tr><td>Background</td><td>{config.background_concurrency}</td></tr></tbody></table>
    <h3>Propose job limits</h3>
    <div class="fields"><label>Interactive jobs<input type="number" min="1" max="128" placeholder={String(config.interactive_concurrency)} bind:value={interactive} /></label><label>Background jobs<input type="number" min="1" max="128" placeholder={String(config.background_concurrency)} bind:value={background} /></label></div>
  {:else}<p>This snapshot does not include the startup configuration.</p>{/if}
{:else if area.id === "orchestration"}
  {#if config}
    <h3>Routing defaults</h3>
    <table><thead><tr><th>Source</th><th>Queue</th><th>Priority</th></tr></thead><tbody>{#each config.routing as rule (rule.source)}<tr><td>{rule.source}</td><td>{rule.queue}</td><td>{rule.priority}</td></tr>{/each}</tbody></table>
    <h3>Runtime switching</h3>
    <dl class="facts"><dt>Actuator</dt><dd>{config.actuator}</dd><dt>Policy</dt><dd>{config.switching_policy}</dd><dt>Minimum hard-swap priority</dt><dd>{config.hard_swap_priority}</dd><dt>Plan / drain / warmup</dt><dd>{config.planning_timeout_s} s / {config.drain_timeout_s} s / {config.warmup_timeout_s} s</dd></dl>
    {#if sourceRule}<h3>Propose a routing default</h3>
      <div class="fields"><label>Source<select value={sourceRule.source} onchange={(event) => { routeSource = event.currentTarget.value; priority = undefined; queue = ""; }}>{#each config.routing as rule (rule.source)}<option value={rule.source}>{rule.source}</option>{/each}</select></label>
      <label>Queue<select value={queue || sourceRule.queue} onchange={(event) => { queue = event.currentTarget.value; }}><option value="runs">runs</option><option value="rites">rites</option></select></label>
      <label>Priority<input type="number" min="0" max="100" placeholder={String(sourceRule.priority)} bind:value={priority} /></label></div>
    {/if}
  {:else}<p>This snapshot does not include orchestration settings.</p>{/if}
{:else if area.id === "fallback"}
  <h3>Current Bridge casting</h3>
  {#if !config}<p>Configuration unavailable.</p>
  {:else if !config.bridge_revision}<p>No explicit Bridge casting selected at startup.</p>
  {:else}<p>Revision <strong>{config.bridge_revision}</strong>{#if config.bridge_capability_key} · <code>{config.bridge_capability_key}</code>{/if}</p>
    {#if configuredRoutes.length}<ol class="order">{#each configuredRoutes as route (route.capability_key)}<li><code>{route.capability_key}</code> · weight {route.weight}{route.weight === 0 ? " · disabled" : ""}</li>{/each}</ol>{/if}
  {/if}
  <h3>Proposed fallback order</h3>
  <p class="intro">List candidates in the order you would consider them before admission. Bridge revision 2 currently ranks two eligible local Chat capabilities by weight and binds one for the Run.</p>
  {#if !candidates.length && (configuredRoutes.length || config?.bridge_capability_key)}
    <button type="button" onclick={() => { candidates = configuredRoutes.length ? configuredRoutes.filter(route => route.weight > 0).map(route => route.capability_key) : config?.bridge_capability_key ? [config.bridge_capability_key] : []; }}>Start from current binding</button>
  {/if}
  <form onsubmit={(event) => { event.preventDefault(); addCandidate(); }}><div class="fields"><label>Capability key<input list="nexus-keys" maxlength="512" bind:value={routeKey} placeholder="animator:family:model" /></label><button type="submit" disabled={!routeKey.trim()}>Add candidate</button></div></form>
  <datalist id="nexus-keys">{#each managed as row (row.capability_key)}<option value={row.capability_key}>{row.runtime} · {row.state}</option>{/each}</datalist>
  {#if addMessage}<p role="status">{addMessage}</p>{/if}
  <ol class="order">{#each candidates as key, index (key)}<li><span>{index === 0 ? "Primary" : "Fallback " + index}</span><code>{key}</code><div class="small-buttons"><button disabled={index === 0} aria-label={'Move ' + key + ' earlier'} onclick={() => move(key, -1)}>↑</button><button disabled={index === candidates.length - 1} aria-label={'Move ' + key + ' later'} onclick={() => move(key, 1)}>↓</button><button aria-label={'Remove ' + key} onclick={() => { candidates = candidates.filter(other => other !== key); }}>Remove</button></div></li>{/each}</ol>
{:else if area.id === "affect"}
  <p class="intro">Design how a proposed signal would influence a receiver. The Ecstatic Harmonizer supplies a positive baseline through rest, disagreement and learning. Evidence of improvement is evaluated independently.</p>
  <div class="fields"><label>Signal producer<select bind:value={producer}><option>Ecstatic Harmonizer</option><option>Current appraisal</option><option>Evidence gain</option></select></label><label>Receiver<select bind:value={receiver}><option>Exploration</option><option>Context selection</option><option>Local appraisal</option></select></label></div>
  <label class="range">Proposed influence · {influence}%<input type="range" min="0" max="100" bind:value={influence} /></label>
  <button onclick={recordRoute}>{affectRoutes.some(route => route.producer === producer && route.receiver === receiver) ? "Update signal route" : "Add signal route"}</button>
  {#if affectRoutes.length}<table><thead><tr><th>Producer → receiver</th><th>Influence</th><th></th></tr></thead><tbody>{#each affectRoutes as route (route.producer + "/" + route.receiver)}<tr><td>{route.producer} → {route.receiver}</td><td>{route.weight_percent}%</td><td><button aria-label={'Remove ' + route.producer + ' to ' + route.receiver} onclick={() => { affectRoutes = affectRoutes.filter(other => other !== route); }}>Remove</button></td></tr>{/each}</tbody></table>{/if}
  <a class="reference" href="https://hexanomicon.dev/divination/transcendence/illumination/#ananda">Read the Harmonizer design ↗</a>
{:else if area.id === "exploration"}
  <p class="intro">Plan a bounded inquiry. A probe can earn another probe when it produces evidence that changes the decision. The budget stays fixed.</p>
  <div class="form-stack"><label>Question<textarea bind:value={question} maxlength="1000" placeholder="Which uncertainty could change this decision?"></textarea></label><label>Evidence criterion<textarea bind:value={criterion} maxlength="1000" placeholder="What observation would settle it?"></textarea></label><label>Maximum probes<input type="number" min="1" max="100" bind:value={probes} /></label></div>
  <p>Stop on evidence saturation or budget exhaustion. Carry unresolved questions to review.</p>
{:else if area.id === "skills"}
  <h3>Agent Card</h3><p class="intro">This Vessel has no published Agent Card. A future card can advertise explicitly public expertise, reusable material and the task schemas the receiver accepts.</p>
  <h3>Propose an advertised skill</h3>
  <div class="form-stack"><label>Public skill or material<input bind:value={skill} maxlength="240" /></label><label>Task schema and version<input bind:value={skillSchema} maxlength="180" /></label><label>Intended audience<input bind:value={disclosure} maxlength="180" /></label></div>
  <a class="reference" href="https://hexanomicon.dev/adr/26-a2a/#advertised-expertise-and-reusable-knowledge">Public skill and disclosure contract ↗</a>
{:else if area.id === "peers"}
  <h3>Private task enrollment</h3><p class="intro">The Intercom operator session owns enrolled peers. Outbound public tasks require an enrolled workload identity, an exact endpoint and an allowed task schema. Nexus has no live task-peer roster.</p>
  <h3>Prepare a peer review</h3>
  <div class="form-stack"><label>Remote workload identity<input bind:value={peer} maxlength="180" /></label><label>Task schema and version<input bind:value={peerSchema} maxlength="180" /></label><label>Purpose<input bind:value={purpose} maxlength="240" /></label></div>
  <a class="reference" href="https://hexanomicon.dev/sepulcher/intercom/#prepare-the-two-identities">Prepare peer identities and enrollment ↗</a>
{:else if area.id === "principals" || area.id === "access"}
  {#if operator}<h3>Authenticated local operator</h3><dl class="facts"><dt>Subject</dt><dd>{operator.subject}</dd><dt>Request Sigil</dt><dd>{operator.sigil}</dd><dt>Scope claims</dt><dd>{operator.scopes.join(", ") || "None"}</dd></dl>
  {:else}<p>The current request identity is unavailable in this snapshot.</p>{/if}
  {#if area.id === "principals"}
    <h3>Users, groups and roles</h3><p class="intro">This installation uses the trusted local operator. The designed Ward directory binds a human account to a Principal. Group membership and named roles supply policy inputs. The Vessel does not serve a multi-user directory.</p>
    <a class="reference" href="https://hexanomicon.dev/adr/38-iam/#people-accounts-and-instances">Account and group bindings ↗</a>
  {:else}
    <h3>Review a privilege elevation</h3><p class="intro">Describe a time-limited request for Ward review. A Sigil records attribution. Each protected effect requires the authority for its action and object.</p>
    <div class="fields"><label>Principal<input bind:value={principal} maxlength="180" placeholder={operator?.subject ?? "Principal identity"} /></label><label>Group (optional)<input bind:value={group} maxlength="180" /></label><label>Role (optional)<input bind:value={role} maxlength="180" /></label></div>
    <div class="fields"><label>Requested action<select bind:value={action}><option value="altar:read">Read Nexus</option><option value="nexus:share-presence">Share availability</option><option value="orchestrator:transition">Request a transition</option></select></label><label>Exact object<input bind:value={object} maxlength="240" /></label><label>Duration (minutes)<input type="number" min="1" max="1440" bind:value={minutes} /></label></div>
    <label>Reason<textarea bind:value={reason} maxlength="1000"></textarea></label>
    <a class="reference" href={resolve("/bridge?attention=pending")}>Review pending Run consents in Bridge →</a>
  {/if}
{/if}

{#if ["installation", "orchestration", "fallback", "affect", "exploration", "skills", "peers", "access"].includes(area.id)}
  <section class="export" aria-label="Local proposal">
    <h3>Local proposal</h3><p>Edits stay on this page. Export a review copy before leaving. Applying a change requires its owner.</p>
    {#if documentText}
      <details><summary>Review JSON</summary><pre>{documentText}</pre></details>
      <a class="download" href={'data:application/json;charset=utf-8,' + encodeURIComponent(documentText)} download={'nexus-' + area.id + '-proposal.json'}>Export proposal</a>
    {/if}
  </section>
{/if}

<style>
  p, label, table, dl, li, a, button, summary { font-size: var(--text-sm); }
  p { color: var(--color-parchment); line-height: 1.55; margin: .35rem 0 .85rem; max-width: 70ch; }
  .intro { margin-bottom: 1rem; }
  h3 { margin: 1.2rem 0 .65rem; font: 600 var(--text-base)/1.4 var(--font-body); color: var(--color-bone); }
  h3:first-child { margin-top: 0; }
  .facts { display: grid; grid-template-columns: minmax(7rem, max-content) minmax(0,1fr); gap: .65rem 1.25rem; margin: .5rem 0 1rem; }
  dt, th { color: var(--color-ash); } dd { margin: 0; overflow-wrap: anywhere; }
  table { width: 100%; max-width: 52rem; border-collapse: collapse; margin: .75rem 0; }
  th, td { padding: .55rem .65rem; border-bottom: 1px solid var(--color-engraving); text-align: left; overflow-wrap: anywhere; }
  th { font-weight: 550; }
  .fields { display: flex; flex-wrap: wrap; align-items: end; gap: .75rem; margin: .65rem 0; }
  .fields label { flex: 1 1 9rem; } .form-stack { display: grid; gap: .8rem; max-width: 36rem; }
  label { display: grid; gap: .35rem; min-width: 0; color: var(--color-parchment); } .range { max-width: 26rem; margin: 1rem 0; }
  input, select, textarea, button, .download { min-width: 0; border: 1px solid var(--color-control-border); border-radius: var(--radius-glyph); background: var(--color-obsidian-2); color: var(--color-bone); font: inherit; }
  input, select, textarea { width: 100%; min-height: 2.55rem; padding: .4rem .6rem; } textarea { resize: vertical; min-height: 4.4rem; }
  input[type="range"] { accent-color: var(--color-rune); padding: 0; }
  button, .download { min-height: 2.35rem; padding: .35rem .7rem; cursor: pointer; font-size: var(--text-sm); }
  button:disabled { opacity: .55; cursor: default; }
  .order { margin: 1rem 0; padding: 0; list-style: none; }
  .order li { display: flex; flex-wrap: wrap; align-items: center; gap: .45rem 1rem; padding: .5rem 0; border-bottom: 1px solid var(--color-engraving); }
  .order li > span { min-width: 4rem; color: var(--color-ash); } code { overflow-wrap: anywhere; } .small-buttons { margin-left: auto; display: flex; gap: .3rem; }
  .reference, .download { display: inline-block; margin-top: .75rem; color: var(--color-rune); }
  .export { margin-top: 1.25rem; padding: 1rem 0; border-top: 1px solid var(--color-engraving); } .export h3 { margin: 0; }
  .export p { color: var(--color-ash); } summary { cursor: pointer; } pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: .75rem; background: var(--color-obsidian-2); }
  :is(a, button, input, select, textarea, summary):focus-visible { outline: 2px solid var(--color-rune); outline-offset: 2px; }
</style>
