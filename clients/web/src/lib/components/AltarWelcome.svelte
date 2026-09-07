<script lang="ts">
  import { resolve } from "$app/paths";
  import workingAltar from "$lib/assets/altar/working-altar.png";

  let { onbegin, pending = false }: { onbegin: () => void; pending?: boolean } = $props();
  const headingId = $props.id();
</script>

<section class="altar-welcome" aria-labelledby={headingId}>
  <div class="altar-welcome__body">
    <div class="altar-welcome__copy">
      <p class="altar-welcome__eyebrow">LychD · The Altar</p>
      <h2 id={headingId}>Begin a séance.</h2>
      <p class="altar-welcome__intro">
        Open a conversation in Bridge with a question, a task, or an idea to explore.
      </p>

      <button
        class="rune-btn altar-welcome__begin"
        type="button"
        onclick={onbegin}
        disabled={pending}
        aria-busy={pending}
      >
        <span aria-hidden="true">✦</span>
        {pending ? "Opening séance…" : "New Séance"}
      </button>

      <div class="altar-welcome__continuity">
        <p>For work that spans conversations</p>
        <a href={resolve("/atlas")}>Open Atlas <span aria-hidden="true">→</span></a>
      </div>
    </div>

    <div class="altar-welcome__art">
      <img src={workingAltar} alt="" width="1536" height="1024" decoding="async" />
    </div>
  </div>
</section>

<style>
  .altar-welcome {
    container-type: inline-size;
    width: 100%;
    max-width: 58rem;
    margin: auto;
    border: 1px solid var(--color-engraving);
    border-radius: var(--radius-panel);
    background: var(--color-obsidian);
  }

  .altar-welcome__body {
    display: grid;
    overflow: hidden;
    border-radius: inherit;
  }

  .altar-welcome__copy {
    min-width: 0;
    padding: 1.5rem;
    align-self: center;
  }

  .altar-welcome__eyebrow {
    margin: 0 0 0.75rem;
    color: var(--color-rune);
    font: var(--text-2xs)/1.5 var(--font-glyph);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  h2 {
    max-width: 15ch;
    margin: 0;
    color: var(--color-bone);
    font: 400 1.875rem/1.12 var(--font-rune);
    letter-spacing: -0.02em;
    text-wrap: balance;
  }

  .altar-welcome__intro {
    max-width: 35ch;
    margin: 0.8rem 0 1.125rem;
    color: var(--color-parchment);
    font-size: var(--text-sm);
    line-height: 1.6;
  }

  .altar-welcome__begin {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    gap: 0.7rem;
    min-height: 2.75rem;
    padding: 0.7rem 1.1rem;
    border-color: color-mix(in srgb, var(--color-rune) 60%, var(--color-engraving));
    color: var(--color-frost);
    line-height: 1.4;
    letter-spacing: 0.035em;
  }

  .altar-welcome__begin:disabled {
    opacity: 0.65;
  }

  .altar-welcome__continuity {
    margin-top: 1.25rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-engraving);
    font-size: var(--text-xs);
  }

  .altar-welcome__continuity p {
    margin: 0 0 0.25rem;
    color: var(--color-parchment);
    line-height: 1.5;
  }

  .altar-welcome__continuity a {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    min-height: 2.25rem;
    color: var(--color-rune);
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 0.25em;
  }

  .altar-welcome__art {
    height: 60cqw;
    overflow: hidden;
    border-top: 1px solid var(--color-engraving);
    background: var(--color-void);
  }

  .altar-welcome__art img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: 40% center;
  }

  @container (min-width: 36rem) {
    .altar-welcome__body {
      grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
    }

    .altar-welcome__copy {
      padding: 1.5rem;
    }

    h2 {
      font-size: 2.125rem;
    }

    .altar-welcome__art {
      height: auto;
      min-height: 22rem;
      border-top: 0;
      border-left: 1px solid var(--color-engraving);
    }

    .altar-welcome__art img {
      object-position: 38% center;
    }
  }

  @media (forced-colors: active) {
    .altar-welcome,
    .altar-welcome__begin,
    .altar-welcome__continuity,
    .altar-welcome__art {
      border-color: CanvasText;
    }
  }
</style>
