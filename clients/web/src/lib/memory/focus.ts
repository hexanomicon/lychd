/** Native hidden, inert and closed-disclosure boundaries apply to focus as well as painting. */
export function availableFocusTarget(node: HTMLElement | null): node is HTMLElement {
  if (!node?.isConnected) return false;
  for (let ancestor: HTMLElement | null = node; ancestor; ancestor = ancestor.parentElement) {
    if (ancestor.hidden || ancestor.inert) return false;
    if (ancestor instanceof HTMLDetailsElement && !ancestor.open && !ancestor.querySelector(":scope > summary")?.contains(node)) return false;
  }
  return true;
}
