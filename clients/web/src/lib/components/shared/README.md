# Shared Altar components

Reusable presentation atoms for every Altar instrument (Bridge, Atlas, Loom, Nexus, Orb, and
applications). Use these components; do not restyle a local copy. Each file's header comment
describes its contract, and `shared-components.test.ts` holds the accessibility contract for each.

| Need | Component | Notes |
|---|---|---|
| Page title block | `PageHeader` | Kicker, title, description, `actions` snippet |
| Section title with a count | `SectionHeading` | `meta` for the muted count; `focusable` for focus targets |
| Small uppercase label | `Eyebrow` | `as="h2"` only when it names the section |
| Status or badge | `StatusPill` | `tone`: neutral, attention, info, success, fault, muted. Run and capability states that animate keep the global `.chip[data-state]` |
| Facts (term → value) | `KeyValueList` | `items`, or `children` with `<dt>`/`<dd>`; `dd.glyph` for identifiers; `--kv-term-width` or `termWidth` for the term column |
| Side inspector | `InspectorPanel` + `InspectorSection` + `InspectorLinks` | `label` for a stable landmark name, `framed={false}` inside a page column, `titleFocusable` + `titleId` for focus moves |
| Mutually exclusive toggles | `SegmentedControl` | Labelled group of `aria-pressed` buttons; `separator`, `hint` |
| Expand in place or popover | `Disclosure` | `variant="popover"` closes on Escape and outside click (`dismissibleDetails`) |
| Button or button-styled link | `Button` | `variant` primary, secondary or ghost; `size` sm or md; `busy`; `href` renders `<a>` |
| Failure, optional retry | `FaultNotice` | `severity` alert (blocking) or status (soft); `title`, guidance `children`, `retryDisabled` |
| Waiting | `LoadingState` | Always labelled; the mist bars are hidden from assistive technology |
| Nothing to show yet | `EmptyState` | Heading title, body copy, one `action` |

Conversation pieces shared by the shell sidebar and the docked Bridge live in
`lib/components/conversation/` (`ConversationList`, `ConversationHeading`, `TurnHeader`). They
read only the `BridgeHistory` interface in `lib/navigation/instruments.ts`: BridgeView owns the
data and registers it, and the shell renders it.

Styling uses native CSS and the existing tokens only (ADR 15). Variants are props mapped to
`data-*` attributes. To adjust spacing around a component inside a page, wrap it or target its
root class through `:global(.kv-list)` and similar from the page; never fork the component's internals.
