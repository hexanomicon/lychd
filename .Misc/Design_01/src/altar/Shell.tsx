import React, { useEffect, useState } from 'react'
import {
  MessageSquare, Users, Layers, GitBranch, Network, Globe, LayoutGrid, SquarePen, Search, PanelLeft,
  ChevronRight, ChevronDown, Settings, Sun, Moon, Monitor, PenTool, Presentation, Radio, AudioLines, Captions, ScanSearch, Sparkle,
  MoreHorizontal, Minus, Square, Copy, X,
  type LucideIcon,
} from 'lucide-react'
import { SIDE_TABS } from './SidePanes'
import { APPS, type Section } from './data'
import { useAltar, usePageTitle, type Theme } from './store'
import { IconBtn, Kicker, Pill, type Tone } from './ui'

export type { Theme }

const NAV: { id: Section; label: string; sub: string; Icon: LucideIcon }[] = [
  { id: 'bridge', label: 'Bridge', sub: 'Talk', Icon: MessageSquare },
  { id: 'atlas', label: 'Atlas', sub: 'Projects', Icon: Layers },
  { id: 'loom', label: 'Loom', sub: 'Scores', Icon: GitBranch },
  { id: 'nexus', label: 'Nexus', sub: 'Iron', Icon: Network },
  { id: 'orb', label: 'Orb', sub: 'Runs', Icon: Globe },
  { id: 'agents', label: 'Agents', sub: 'Crew', Icon: Users },
]

export const APP_ICONS: Record<string, LucideIcon> = {
  search: ScanSearch, pen: PenTool, board: Presentation, radio: Radio, wave: AudioLines, captions: Captions,
}

export type ShellProps = {
  section: Section
  crumb: string
  title: string
  status?: { tone: Tone; label: string } | null
  headerActions?: React.ReactNode
  ctxTitle: string
  ctx: React.ReactNode
  side: React.ReactNode
  children: React.ReactNode
}

export function Shell(p: ShellProps) {
  const { theme, setTheme, resolvedTheme, layout, setLayout, pinned: pinnedIds, go } = useAltar()
  const [flyout, setFlyout] = useState(false)
  usePageTitle(p.title)
  const { rail, ctx, side, w } = layout
  const pinned = APPS.filter((a) => pinnedIds.includes(a.id))
  const others = APPS.filter((a) => !pinnedIds.includes(a.id)).slice(0, 3)

  useEffect(() => {
    if (!flyout) return
    const close = (e: KeyboardEvent) => e.key === 'Escape' && setFlyout(false)
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [flyout])

  const drag = (k: 'rail' | 'ctx' | 'side', min: number, max: number, dir: 1 | -1) => (e: React.PointerEvent) => {
    e.preventDefault()
    const x0 = e.clientX
    const w0 = w[k]
    const mv = (ev: PointerEvent) =>
      setLayout((o) => ({ ...o, w: { ...o.w, [k]: Math.max(min, Math.min(max, w0 + dir * (ev.clientX - x0))) } }))
    const up = () => {
      window.removeEventListener('pointermove', mv)
      window.removeEventListener('pointerup', up)
      document.body.style.cursor = ''
    }
    document.body.style.cursor = 'col-resize'
    window.addEventListener('pointermove', mv)
    window.addEventListener('pointerup', up)
  }
  const set = (patch: Partial<Layout>) => setLayout((o) => ({ ...o, ...patch }))

  return (
    <div data-theme={resolvedTheme} className="altar relative flex h-screen min-h-[560px] w-full flex-col overflow-hidden bg-frame" onClick={() => setFlyout(false)}>
      <TitleBar title={p.title} />
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
      {/* compact section switcher for narrow widths */}
      <nav className="chrome flex flex-none gap-1 overflow-x-auto bg-panel p-2 md:hidden" aria-label="Sections">
        {[...NAV, { id: 'apps' as Section, label: 'Applications', Icon: LayoutGrid }].map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => go(id)}
            aria-current={p.section === id ? 'page' : undefined}
            className={`flex h-8 flex-none items-center gap-2 rounded-lg px-3 text-[13px] ${p.section === id ? 'bg-sel font-semibold text-accent' : 'text-ink2'}`}
          >
            <Icon className="size-4" strokeWidth={1.6} />
            {label}
          </button>
        ))}
      </nav>

      {/* ---------- rail ---------- */}
      {rail && (
        <aside style={{ width: w.rail }} className="chrome relative hidden flex-none flex-col bg-panel px-3 py-4 md:flex" aria-label="Primary navigation">
          <div className="flex items-center gap-2.5 px-1 pb-4">
            <div className="grid size-8 flex-none place-items-center rounded-full bg-primary text-onprimary">
              <Sparkle className="size-4 fill-current" strokeWidth={1.4} />
            </div>
            <b className="text-[16px] font-semibold tracking-tight">LychD</b>
            <span className="text-[16px] text-ink3">Altar</span>
            <span className="flex-1" />
            <IconBtn title="Search (⌘K)"><Search className="size-4" strokeWidth={1.6} /></IconBtn>
            <IconBtn title="Collapse rail" onClick={() => set({ rail: false })}><PanelLeft className="size-4" strokeWidth={1.6} /></IconBtn>
          </div>
          <div className="mb-3 h-px bg-line" />
          <button onClick={() => go('bridge')} className="mb-4 flex h-10 flex-none items-center gap-2.5 whitespace-nowrap rounded-xl border border-line2 bg-sunk px-3 font-medium transition-colors duration-150 hover:bg-hover">
            <SquarePen className="size-4" strokeWidth={1.6} />
            New séance
            <kbd className="ml-auto rounded-md border border-line2 px-1.5 font-sans text-[11px] text-ink3">⌘N</kbd>
          </button>
          <nav className="flex flex-col gap-0.5">
            {NAV.map(({ id, label, sub, Icon }) => (
              <NavItem key={id} on={p.section === id} Icon={Icon} label={label} sub={sub} onClick={() => go(id)} />
            ))}
          </nav>
          <div className="my-3 h-px bg-line" />
          <Kicker className="px-3 pb-1.5">Pinned apps</Kicker>
          {pinned.length === 0 && <div className="px-3 pb-1 text-[12.5px] text-ink3">Pin apps from Applications.</div>}
          {pinned.map((a) => {
            const I = APP_ICONS[a.icon]
            return (
              <button key={a.id} onClick={() => go('apps')} className="flex h-9 w-full items-center gap-3 whitespace-nowrap rounded-xl px-3 text-ink2 transition-colors duration-150 hover:bg-hover hover:text-ink">
                <I className="size-4" strokeWidth={1.6} />
                {a.name}
              </button>
            )
          })}
          <div className="relative mt-0.5">
            <NavItem
              on={p.section === 'apps'}
              Icon={LayoutGrid}
              label="Applications"
              expanded={flyout}
              trailing={<ChevronRight className="ml-auto size-4" strokeWidth={1.6} />}
              onClick={(e) => { e.stopPropagation(); setFlyout((o) => !o) }}
            />
            {flyout && (
              <div role="menu" onClick={(e) => e.stopPropagation()} className="absolute left-full top-[-8px] z-50 ml-3 w-60 rounded-xl border border-line2 bg-raise p-1.5 shadow-pop">
                {others.map((a) => {
                  const I = APP_ICONS[a.icon]
                  return (
                    <button role="menuitem" key={a.id} onClick={() => { setFlyout(false); go('apps') }} className="flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 hover:bg-hover">
                      <I className="size-4 text-ink2" strokeWidth={1.6} />
                      {a.name}
                    </button>
                  )
                })}
                {others.length > 0 && <div className="mx-1 my-1.5 h-px bg-line" />}
                <button role="menuitem" onClick={() => { setFlyout(false); go('apps') }} className="flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 font-medium text-accent hover:bg-hover">
                  <LayoutGrid className="size-4" strokeWidth={1.6} />
                  All applications <span className="ml-auto">→</span>
                </button>
              </div>
            )}
          </div>
          <div className="flex-1" />
          <button onClick={() => go('bridge')} className="mb-3 flex items-center gap-2 whitespace-nowrap rounded-xl bg-warnsoft px-3 py-2.5 text-left text-[12.5px] font-semibold text-warn">
            <span className="size-[7px] flex-none rounded-full border-[1.6px] border-current" />
            1 awaiting consent
          </button>
          <div className="flex items-center gap-2.5 px-1 pb-3">
            <div className="grid size-8 flex-none place-items-center rounded-full border border-line2 bg-sunk text-[12px] font-bold">M</div>
            <b className="font-semibold">Magus</b>
            <span className="flex-1" />
            <IconBtn title="Settings"><Settings className="size-4" strokeWidth={1.6} /></IconBtn>
          </div>
          <div role="radiogroup" aria-label="Appearance" className="grid auto-cols-fr grid-flow-col rounded-xl border border-line bg-sunk p-1">
            {([['system', Monitor], ['light', Sun], ['dark', Moon]] as const).map(([t, I]) => (
              <button
                key={t}
                role="radio"
                aria-checked={theme === t}
                title={t[0].toUpperCase() + t.slice(1)}
                aria-label={t}
                onClick={() => setTheme(t)}
                className={`flex h-7 items-center justify-center rounded-lg transition-colors duration-150 ${theme === t ? 'bg-sel text-accent' : 'text-ink3 hover:text-ink'}`}
              >
                <I className="size-4" strokeWidth={1.6} />
              </button>
            ))}
          </div>
          <Handle label="Resize rail" onDown={drag('rail', 190, 320, 1)} className="absolute inset-y-0 right-0 hidden md:block" />
        </aside>
      )}

      {/* ---------- context panel (follows the appearance; only the rail is always dark) ---------- */}
      {ctx && (
        <section style={{ width: w.ctx }} className="relative hidden flex-none flex-col border-r border-line bg-panel lg:flex" aria-label="Context panel">
          <div className="flex h-[68px] flex-none items-center justify-between pl-[18px] pr-3">
            <h2 className="m-0 text-[15px] font-semibold">{p.ctxTitle}</h2>
            <IconBtn title="Collapse panel" onClick={() => set({ ctx: false })}><PanelLeft className="size-4" strokeWidth={1.6} /></IconBtn>
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-3 pb-4">{p.ctx}</div>
          <Handle label="Resize context panel" onDown={drag('ctx', 220, 400, 1)} className="absolute inset-y-0 right-0" />
        </section>
      )}

      {/* ---------- workspace: an inset surface ---------- */}
      <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden bg-bg md:my-2 md:mr-2 md:rounded-[20px]">
        <main className="relative flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex-none p-3 pb-0">
            <header className="flex h-14 min-w-0 items-center gap-2.5 rounded-2xl border border-line bg-panel pl-3 pr-3 shadow-card">
              {(!rail || !ctx) && (
                <HeadBtn title="Expand panels" onClick={() => set({ rail: true, ctx: true })}>
                  <PanelLeft className="size-4" strokeWidth={1.6} />
                </HeadBtn>
              )}
              <span className="hidden flex-none items-center gap-2 whitespace-nowrap pl-2 text-ink3 sm:flex">{p.crumb} <span>/</span></span>
              <h1 className="m-0 min-w-0 truncate pl-2 text-[15px] font-semibold sm:pl-0" title={p.title}>{p.title}</h1>
              {p.status && <span className="flex-none"><Pill tone={p.status.tone}>{p.status.label}</Pill></span>}
              <span className="min-w-2 flex-1" />
              <div className="hidden flex-none items-center gap-1.5 2xl:flex">{p.headerActions}</div>
            </header>
          </div>
          {p.children}
        </main>

        {side && (
          <>
            <Handle label="Resize right sidebar" onDown={drag('side', 300, 640, -1)} className="relative hidden xl:block" />
            <aside style={{ width: w.side }} className="my-3 mr-3 hidden flex-none flex-col overflow-hidden rounded-2xl border border-line bg-panel shadow-card xl:flex" aria-label="Right sidebar">
              {p.side}
            </aside>
          </>
        )}
      </div>
      </div>
    </div>
  )
}

/**
 * Window title bar, as in a desktop app: current title on the left; on the right the
 * right-sidebar pane toggles for this page, then the window controls.
 */
function TitleBar({ title }: { title: string }) {
  const { sideTabs, sideTab, toggleSideTab, layout } = useAltar()
  const [full, setFull] = useState(false)
  useEffect(() => {
    const on = () => setFull(Boolean(document.fullscreenElement))
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [])
  const toggleFull = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void document.documentElement.requestFullscreen?.().catch(() => {})
  }
  return (
    <div className="flex h-10 flex-none select-none items-center border-b border-line bg-frame text-ink2" role="banner">
      <div className="flex min-w-0 items-center gap-1.5 pl-4 text-[13px] text-ink">
        <span className="truncate font-medium">{title}</span>
        <ChevronDown className="size-3.5 flex-none text-ink3" strokeWidth={1.8} />
      </div>
      <span className="flex-1" />
      <div role="toolbar" aria-label="Panels" className="flex items-center gap-0.5 pr-2">
        {sideTabs.map((t) => {
          const { label, Icon } = SIDE_TABS[t]
          const on = layout.side && sideTab === t
          return (
            <button
              key={t}
              title={label}
              aria-label={label}
              aria-pressed={on}
              onClick={() => toggleSideTab(t)}
              className={`grid h-7 w-8 place-items-center rounded-md transition-colors duration-150 ${on ? 'bg-sel text-ink' : 'hover:bg-hover hover:text-ink'}`}
            >
              <Icon className="size-4" strokeWidth={1.6} />
            </button>
          )
        })}
        <button title="More" aria-label="More" className="grid h-7 w-8 place-items-center rounded-md transition-colors duration-150 hover:bg-hover hover:text-ink">
          <MoreHorizontal className="size-4" strokeWidth={1.6} />
        </button>
      </div>
      <div className="flex h-full items-stretch border-l border-line" aria-label="Window controls">
        <button title="Minimise" aria-label="Minimise" className="grid w-11 place-items-center transition-colors duration-150 hover:bg-hover hover:text-ink">
          <Minus className="size-4" strokeWidth={1.4} />
        </button>
        <button title={full ? 'Restore' : 'Maximise'} aria-label={full ? 'Restore' : 'Maximise'} onClick={toggleFull} className="grid w-11 place-items-center transition-colors duration-150 hover:bg-hover hover:text-ink">
          {full ? <Copy className="size-3.5" strokeWidth={1.4} /> : <Square className="size-3.5" strokeWidth={1.4} />}
        </button>
        <button title="Close" aria-label="Close" className="grid w-11 place-items-center transition-colors duration-150 hover:bg-[#c42b1c] hover:text-white">
          <X className="size-4" strokeWidth={1.4} />
        </button>
      </div>
    </div>
  )
}

type Layout = ReturnType<typeof useAltar>['layout']

function NavItem({ on, Icon, label, sub, trailing, expanded, onClick }: {
  on: boolean; Icon: LucideIcon; label: string; sub?: string; trailing?: React.ReactNode; expanded?: boolean; onClick: (e: React.MouseEvent) => void
}) {
  return (
    <button
      onClick={onClick}
      aria-current={on ? 'page' : undefined}
      aria-expanded={expanded}
      className={`relative flex h-10 w-full items-center gap-3 whitespace-nowrap rounded-xl px-3 transition-colors duration-150 ${
        on ? 'bg-sel font-semibold text-accent' : 'text-ink2 hover:bg-hover hover:text-ink'
      }`}
    >
      {on && <span className="absolute -left-3 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-primary" />}
      <Icon className="size-[18px] flex-none" strokeWidth={1.6} />
      {label}
      {sub && <small className={`ml-auto text-[11px] font-normal ${on ? 'text-accent' : 'text-ink3'}`}>{on ? '→' : sub}</small>}
      {trailing}
    </button>
  )
}

/** Bordered square header button, as the workspace toolbar uses. */
function HeadBtn({ title, onClick, pressed, children }: { title: string; onClick?: () => void; pressed?: boolean; children: React.ReactNode }) {
  return (
    <button
      title={title}
      aria-label={title}
      aria-pressed={pressed}
      onClick={onClick}
      className="grid size-9 flex-none place-items-center rounded-xl border border-line bg-panel text-ink2 shadow-card transition-colors duration-150 hover:bg-hover hover:text-ink"
    >
      {children}
    </button>
  )
}

function Handle({ label, onDown, className }: { label: string; onDown: (e: React.PointerEvent) => void; className: string }) {
  return (
    <div role="separator" aria-orientation="vertical" aria-label={label} onPointerDown={onDown} className={`group z-10 w-1.5 flex-none cursor-col-resize ${className}`}>
      <span className="absolute left-1/2 top-1/2 flex h-7 w-1.5 -translate-x-1/2 -translate-y-1/2 flex-col items-center justify-center gap-[3px] rounded border border-line2 bg-raise opacity-0 transition-opacity duration-150 group-hover:opacity-100">
        <i className="size-0.5 rounded-full bg-ink3" /><i className="size-0.5 rounded-full bg-ink3" /><i className="size-0.5 rounded-full bg-ink3" />
      </span>
    </div>
  )
}
