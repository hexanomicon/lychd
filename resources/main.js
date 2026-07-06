import './main.css';
import htmx from 'htmx.org';
import 'htmx-ext-sse';
import Alpine from 'alpinejs';
import mermaid from 'mermaid';

/* ── htmx hygiene (§TD-3.6) ─────────────────────────────────────────── */
htmx.config.selfRequestsOnly = true;
htmx.config.allowScriptTags = false;

/* ── Alpine boundary — ephemeral, non-authoritative UI state only ────── */
window.Alpine = Alpine;

document.addEventListener('alpine:init', () => {
  // Composer: Enter-to-send vs Shift+Enter newline; clear on successful send.
  Alpine.data('composer', () => ({
    submit(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        this.$el.closest('form').requestSubmit();
      }
    },
    clear() {
      this.$el.reset();
    },
  }));

  // Autoscroll: keep the thread pinned to the bottom unless the Magus scrolled up.
  Alpine.data('autoscroll', () => ({
    pinned: true,
    init() {
      this.scrollToBottom();
      this.$el.addEventListener('scroll', () => {
        const gap = this.$el.scrollHeight - this.$el.scrollTop - this.$el.clientHeight;
        this.pinned = gap < 48;
      });
      // Re-pin as SSE content lands.
      new MutationObserver(() => { if (this.pinned) this.scrollToBottom(); })
        .observe(this.$el, { childList: true, subtree: true });
    },
    scrollToBottom() { this.$el.scrollTop = this.$el.scrollHeight; },
  }));

  // Drawer: open/closed of an inspector or panel (content still loads via hx-get).
  Alpine.data('drawer', () => ({ open: false, toggle() { this.open = !this.open; } }));

  // Omen stack: transient toasts for connection / request faults (no routes).
  Alpine.data('omens', () => ({
    items: [],
    add(text, fault) {
      const id = Date.now() + Math.random();
      this.items.push({ id, text, fault });
      if (!fault) setTimeout(() => this.dismiss(id), 6000);
    },
    dismiss(id) { this.items = this.items.filter((o) => o.id !== id); },
  }));
});

Alpine.start();

/* ── Mermaid — single source of truth: derive theme from the built tokens ── */
const initMermaid = () => {
  const css = getComputedStyle(document.documentElement);
  const t = (name) => css.getPropertyValue(name).trim();
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    theme: 'base',
    themeVariables: {
      background: t('--color-obsidian'),
      primaryColor: t('--color-obsidian-2'),
      primaryTextColor: t('--color-bone'),
      primaryBorderColor: t('--color-rune'),
      lineColor: t('--color-rune-dim'),
      tertiaryColor: t('--color-void'),
      fontFamily: t('--font-glyph'),
    },
  });
};

const renderMermaid = (root) => {
  const nodes = root.querySelectorAll('.mermaid:not([data-processed])');
  if (nodes.length) mermaid.run({ nodes });
};

document.addEventListener('DOMContentLoaded', () => {
  initMermaid();
  renderMermaid(document);
});
document.body.addEventListener('htmx:afterSettle', (e) => renderMermaid(e.detail.elt));

/* ── Omen triggers: surface htmx / SSE faults as toasts (§6.3) ───────── */
const raiseOmen = (text, fault) => {
  window.dispatchEvent(new CustomEvent('altar:omen', { detail: { text, fault } }));
};
document.body.addEventListener('htmx:sendError', () => raiseOmen('The Altar cannot be reached.', true));
document.body.addEventListener('htmx:responseError', () => raiseOmen('The rite was refused by the Altar.', true));
document.body.addEventListener('htmx:sseError', () => raiseOmen('The stream has gone quiet — re-binding…', false));
