<script lang="ts">
  let { name, size = 22 }: { name: string; size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  {#if name === "atlas"}<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Z M9 3v16 M15 5v16" />
  {:else if name === "orb"}<circle cx="12" cy="12" r="9" stroke-dasharray="42 5" /><path d="m15 3 3 1-2 3" />
  {:else if name === "loom" || name === "connect"}<path d="m7 17 10-10 M7 7l10 10" /><circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
  {:else if name === "nexus"}<ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 4 16 4 16 0V5 M4 12c0 4 16 4 16 0" />
  {:else if name === "applications"}<path d="M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h6v6h-6z" />
  {:else if name === "bridge"}<path d="M21 11c0 5-4 8-9 8H7l-5 3 2-6a8 8 0 0 1-1-5c0-5 4-8 9-8s9 3 9 8Z" />
  {:else if name === "canvas" || name === "draw"}<path d="m16 3 5 5-12 12-6 1 1-6Z M13 6l5 5" />
  {:else if name === "scavenger"}<circle cx="10" cy="10" r="7" /><path d="m15 15 6 6" />
  {:else if name === "select"}<path d="M8 3H3v5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5" stroke-dasharray="3 2" />
  {:else if name === "lasso"}<path d="M8 19C-2 15 3 3 13 3c13 0 11 15-1 16-4 0-7-3-4-5 4-2 6 4 1 8" />
  {:else if name === "node"}<rect x="4" y="4" width="16" height="16" />
  {:else if name === "pan"}<path d="M8 12V5c0-3 3-3 3 0v6-8c0-3 3-3 3 0v8-6c0-3 3-3 3 0v7-4c0-3 3-3 3 0v8c0 9-11 9-14 4L2 14c-2-3 1-5 3-2l3 4" />
  {:else if name === "undo"}<path d="m8 4-5 5 5 5 M3 9h11a7 7 0 0 1 0 14" />
  {:else if name === "redo"}<path d="m16 4 5 5-5 5 M21 9H10a7 7 0 0 0 0 14" />
  {:else}<path d="m6 9 6 6 6-6" />{/if}
</svg>
