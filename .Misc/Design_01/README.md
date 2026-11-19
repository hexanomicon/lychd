# LychD Altar — UI design prototype

A runnable prototype of the LychD Altar UI, finalised from a Magic Patterns design.
It uses mock data only and talks to no backend.

## Run

```bash
npm install
npm run dev        # http://localhost:5173 (or the port Vite prints)
npm run typecheck  # tsc --noEmit
npm run build      # production bundle in dist/
```

## Routes

| Path | Screen |
| --- | --- |
| `/bridge` | Conversation: séances, turn strip, consent card, composer; Circle / Files / Terminal / Browser sidebar |
| `/atlas` | Project record: concerns, decisions, references |
| `/loom` | Workflow score canvas with inspector |
| `/nexus` | Capabilities, plan preview, tickets |
| `/orb` | Live run field canvas with tab history |
| `/agents` | Agent roster |
| `/apps` | Applications: search, area filter, pinning |

## Structure

```
src/
  main.tsx          entry: router + styles
  App.tsx           routes inside <AltarProvider>
  styles.css        Tailwind v4 theme tokens; light/dark; dark navigation chrome
  altar/
    store.tsx       shared state: appearance (System/Light/Dark), panel layout, pinned apps
    Shell.tsx       window title bar (title · sidebar pane toggles · window controls),
                    rail, context panel, inset workspace, header, right sidebar
    SidePanes.tsx   right-sidebar tabs (Circle, Files, Terminal, Browser, Inspector, Bridge)
    Canvas.tsx      pan / zoom / fit canvas used by Orb and Loom
    ui.tsx          Pill, Btn, ListItem, Table, Tile, Kv, Segmented, Search, Spinner
    data.ts         applications catalogue
  pages/            one file per route
```

`npm run build:static` builds a copy that works from any static host or file path
(hash URLs such as `#/orb`, relative asset paths).

Appearance, panel widths and collapsed state, and pinned apps are saved in the browser
(`localStorage`, keys `altar.*`) and fall back to defaults when storage is unavailable.

## Relation to the real Altar

The production Altar lives in `clients/web` and is Svelte 5 with native CSS
(ADR 15 forbids Tailwind there). This prototype is the visual and behavioural reference
for that port, not code to copy across directly.
