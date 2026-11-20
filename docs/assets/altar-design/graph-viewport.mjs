// Presentation primitives shared by the Loom and Orb design studies.
// The caller supplies its own graph projection and the current camera transform.
export function svgElement(tag, attributes = {}) {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
  return element;
}

export function appendMapLine(group, from, to, attributes = {}) {
  group.append(svgElement('line', {x1: from.x, y1: from.y, x2: to.x, y2: to.y, ...attributes}));
}

export function starPath(radius) {
  const x = radius * 1.16;
  const y = radius * 1.3;
  return `M 0 ${-y} Q .6 -.6 ${x} 0 Q .6 .6 0 ${y} Q -.6 .6 ${-x} 0 Q -.6 -.6 0 ${-y} Z`;
}

export function cameraBounds(transform, width, height) {
  const x = -transform.x / transform.zoom;
  const y = -transform.y / transform.zoom;
  const worldWidth = width / transform.zoom;
  const worldHeight = height / transform.zoom;
  return {
    x, y, width: worldWidth, height: worldHeight,
    center: {x: x + worldWidth / 2, y: y + worldHeight / 2}
  };
}
