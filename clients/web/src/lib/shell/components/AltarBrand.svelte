<script lang="ts">
  import { asset } from "$app/paths";
  import { onMount } from "svelte";
  const key = "lychd.altar.brand.v1";
  const original = asset("altar-mark.svg");
  let name = $state("Altar"),
    mark = $state(""),
    notice = $state(""),
    menu: HTMLDetailsElement;
  let revision = 0;
  const raster = (s: unknown): s is string =>
    typeof s === "string" &&
    s.length < 90000 &&
    /^data:image\/(png|webp|jpeg);base64,[A-Za-z0-9+/]+=*$/.test(s);
  function favicon() {
    const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (link) {
      link.href = mark || original;
      link.type = mark ? mark.slice(5, mark.indexOf(";")) : "image/svg+xml";
    }
  }
  function save() {
    favicon();
    try {
      localStorage.setItem(key, JSON.stringify({ name, mark }));
      notice = "";
    } catch {
      notice = "Saved for this tab.";
    }
  }
  onMount(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(key) || "null");
      if (typeof stored?.name === "string") name = stored.name.trim().slice(0, 32) || "Altar";
      if (raster(stored?.mark)) mark = stored.mark;
    } catch {}
    favicon();
  });
  async function choose(event: Event) {
    const field = event.currentTarget as HTMLInputElement;
    const file = field.files?.[0];
    field.value = "";
    if (!file) return;
    const token = ++revision;
    if (!["image/png", "image/webp", "image/jpeg"].includes(file.type) || file.size > 65536) {
      notice = "Choose a PNG, WebP or JPEG up to 64 KiB.";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      if (token !== revision) return;
      if (raster(reader.result)) {
        mark = reader.result;
        save();
      } else notice = "This icon could not be read.";
    };
    reader.onerror = () => {
      if (token === revision) notice = "This icon could not be read.";
    };
    reader.readAsDataURL(file);
  }
</script>

<svelte:window
  onclick={(e) => {
    if (menu?.open && !e.composedPath().includes(menu)) menu.open = false;
  }}
  onkeydown={(e) => {
    if (menu?.open && e.key === "Escape") {
      e.preventDefault();
      menu.open = false;
      menu.querySelector("summary")?.focus();
    }
  }}
/>
<details bind:this={menu}>
  <summary aria-label="About Altar" title={name}
    ><img src={mark || original} width="31" height="31" alt="" /><strong>{name}</strong></summary
  >
  <div class="sheet">
    <h2>About the Altar</h2>
    <p>LychD · <a href={asset("THIRD_PARTY_NOTICES.txt")}>Licence notices</a></p>
    <p title={__LYCHD_ALTAR_VERSION__}>
      Altar {__LYCHD_ALTAR_VERSION__.slice(0, 12)} ·
      <a href={__LYCHD_SOURCE_URL__} rel="noreferrer">{__LYCHD_SOURCE_LABEL__}</a>
    </p>
    <label
      >Display name<input
        maxlength="32"
        value={name}
        onchange={(e) => {
          name = e.currentTarget.value.trim() || "Altar";
          save();
        }}
      /></label
    >
    <label
      >Icon and favicon<input type="file" accept="image/png,image/jpeg,image/webp" onchange={choose} /></label
    >
    <button
      type="button"
      onclick={() => {
        revision++;
        name = "Altar";
        mark = "";
        save();
      }}>Restore Altar identity</button
    >
    {#if notice}<p role="status">{notice}</p>{/if}
  </div>
</details>

<style>
  summary {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    list-style: none;
    cursor: pointer;
    color: var(--color-bone);
    min-height: 2.7rem;
    padding: 0.15rem;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  strong,
  h2 {
    font: 600 1.45rem/1.1 var(--font-rune);
  }
  strong {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  :global(.rail.folded) strong {
    display: none;
  }
  .sheet {
    position: fixed;
    inset: 0.45rem auto auto calc(var(--nav-size) + 0.4rem);
    z-index: 60;
    padding: 1rem;
    width: min(19rem, calc(100vw - var(--nav-size) - 1.4rem));
    max-height: 90dvh;
    overflow: auto;
    border-radius: 0.65rem;
    border: 1px solid var(--color-control-border);
    background: var(--color-obsidian);
    box-shadow: 0 0.6rem 2rem #0006;
  }
  .sheet label {
    display: grid;
    gap: 0.25rem;
    margin: 0.75rem 0;
  }
  .sheet p,
  .sheet label {
    font: var(--text-xs)/1.5 var(--font-body);
  }
  input,
  button {
    padding: 0.4rem;
    width: 100%;
    min-width: 0;
    background: var(--color-obsidian-2);
    color: var(--color-bone);
    border: 1px solid var(--color-control-border);
    border-radius: 5px;
  }
</style>
