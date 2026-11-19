<script lang="ts">
  let { name, size = 22 }: { name: string; size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  {#if name === "atlas"}<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Z M9 3v16 M15 5v16" />
  {:else if name === "orb"}<circle cx="12" cy="12" r="9" stroke-dasharray="42 5" /><path d="m15 3 3 1-2 3" />
  {:else if name === "loom" || name === "connect"}<path d="m7 17 10-10 M7 7l10 10" /><circle cx="5" cy="5" r="2" /><circle cx="19" cy="5" r="2" /><circle cx="5" cy="19" r="2" /><circle cx="19" cy="19" r="2" />
  {:else if name === "nexus"}<rect x="6" y="6" width="12" height="12" rx="2" /><rect x="9" y="9" width="6" height="6" rx="1" /><path d="M8 2v4 M12 2v4 M16 2v4 M8 18v4 M12 18v4 M16 18v4 M2 8h4 M2 12h4 M2 16h4 M18 8h4 M18 12h4 M18 16h4" />
  {:else if name === "applications"}<path d="M3 3h6v6H3z M15 3h6v6h-6z M3 15h6v6H3z M15 15h6v6h-6z" />
  {:else if name === "atelier"}<path d="m4 19 5-11 9-5 3 3-5 9-12 4Z M5 18l8-8"/><circle cx="14" cy="9" r="1.5"/>
  {:else if name === "panel"}<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M9 5v14"/>
  {:else if name === "broadcast"}<circle cx="12" cy="10" r="2"/><path d="M7 5a7 7 0 0 0 0 10m10-10a7 7 0 0 1 0 10M10 21l2-8 2 8"/>
  {:else if name === "riffmaw"}<path d="M4 10v4m4-8v12m4-15v18m4-14v10m4-7v5"/>
  {:else if name === "language"}<path d="M3 4h8l2 2 2-2h6v15h-6l-2 2-2-2H3Z M13 7v12"/>
  {:else if name === "files"}<path d="M3 6h6l2 2h10v12H3Z"/>
  {:else if name === "terminal"}<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3m6 0h5"/>
  {:else if name === "web"}<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>
  {:else if name === "seances"}<path d="M4 4h16v12H9l-5 4Z M8 8h8 M8 12h5" />
  {:else if name === "bridge"}<path d="M2 16h20 M6 4v16 M18 4v16 M2 10l4-4q6 12 12 0l4 4 M10 12v4 M14 12v4" />
  {:else if name === "canvas"}<rect x="3" y="4" width="18" height="14" rx="1" /><path d="M8 22l4-4 4 4 M12 2v2" />
  {:else if name === "draw"}<path d="m16 3 5 5-12 12-6 1 1-6Z M13 6l5 5" />
  {:else if name === "scavenger"}<circle cx="10" cy="10" r="7" /><path d="m15 15 6 6" />
  {:else if name === "pin"}<path d="m15 3 6 6-3 1-4 4 1 3-2 2-3-5-5-3 2-2 3 1 4-4Z M9 15l-6 6" />
  {:else if name === "select"}<path d="M8 3H3v5 M16 3h5v5 M21 16v5h-5 M8 21H3v-5" stroke-dasharray="3 2" />
  {:else if name === "lasso"}<path d="M8 19C-2 15 3 3 13 3c13 0 11 15-1 16-4 0-7-3-4-5 4-2 6 4 1 8" />
  {:else if name === "node"}<rect x="4" y="4" width="16" height="16" />
  {:else if name === "pan"}<path d="M8 12V5c0-3 3-3 3 0v6-8c0-3 3-3 3 0v8-6c0-3 3-3 3 0v7-4c0-3 3-3 3 0v8c0 9-11 9-14 4L2 14c-2-3 1-5 3-2l3 4" />
  {:else if name === "undo"}<path d="m8 4-5 5 5 5 M3 9h11a7 7 0 0 1 0 14" />
  {:else if name === "redo"}<path d="m16 4 5 5-5 5 M21 9H10a7 7 0 0 0 0 14" />
  {:else}<path d="m6 9 6 6 6-6" />{/if}
</svg>
