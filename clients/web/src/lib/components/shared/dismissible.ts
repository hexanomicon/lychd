import type { Attachment } from "svelte/attachments";

/**
 * Closes an open `<details>` popover on an outside click or Escape, returning focus
 * to its summary on Escape. Escape is claimed with `preventDefault` so outer layers
 * (the narrow sidebar, the Bridge modal) leave it alone.
 */
export const dismissibleDetails: Attachment<HTMLDetailsElement> = (node) => {
  function dismissOutside(event: MouseEvent) {
    if (node.open && !event.composedPath().includes(node)) node.open = false;
  }
  function dismissOnEscape(event: KeyboardEvent) {
    if (event.key !== "Escape" || event.defaultPrevented || !node.open) return;
    node.open = false;
    node.querySelector("summary")?.focus();
    event.preventDefault();
  }
  window.addEventListener("click", dismissOutside);
  window.addEventListener("keydown", dismissOnEscape);
  return () => {
    window.removeEventListener("click", dismissOutside);
    window.removeEventListener("keydown", dismissOnEscape);
  };
};
