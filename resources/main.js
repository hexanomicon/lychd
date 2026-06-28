import './main.css';
import 'htmx.org';
import 'htmx-ext-sse';
import Alpine from 'alpinejs';
import mermaid from 'mermaid';

window.Alpine = Alpine;
Alpine.start();

mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  theme: 'base',
  themeVariables: {           // mirror of the CSS tokens in fable-v1-spec §10
    background: '#1a1a20',
    primaryColor: '#212129',
    primaryTextColor: '#d9d7e4',
    primaryBorderColor: '#7c4dff',
    lineColor: '#5a4a8a',
    tertiaryColor: '#16161c',
    fontFamily: 'ui-monospace, monospace',
  },
});

const renderMermaid = (root) => {
  const nodes = root.querySelectorAll('.mermaid:not([data-processed])');
  if (nodes.length) mermaid.run({ nodes });
};

document.addEventListener('DOMContentLoaded', () => renderMermaid(document));
document.body.addEventListener('htmx:afterSwap', (e) => renderMermaid(e.detail.elt));
