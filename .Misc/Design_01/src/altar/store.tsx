import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DEFAULT_PINNED, type Section } from './data'

export type Theme = 'system' | 'light' | 'dark'
export type Layout = { rail: boolean; ctx: boolean; side: boolean; w: { rail: number; ctx: number; side: number } }

const DEFAULT_LAYOUT: Layout = { rail: true, ctx: true, side: true, w: { rail: 232, ctx: 256, side: 340 } }

/** Browser storage is a per-viewer convenience: it may be missing or throw, and the UI must work without it. */
function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(`altar.${key}`)
    return raw ? { ...fallback, ...JSON.parse(raw) } : fallback
  } catch {
    return fallback
  }
}
function loadList(key: string, fallback: string[]): string[] {
  try {
    const raw = localStorage.getItem(`altar.${key}`)
    const v = raw ? JSON.parse(raw) : null
    return Array.isArray(v) ? v.filter((x) => typeof x === 'string') : fallback
  } catch {
    return fallback
  }
}
function save(key: string, value: unknown) {
  try {
    localStorage.setItem(`altar.${key}`, JSON.stringify(value))
  } catch {
    /* storage unavailable: keep in-memory state only */
  }
}

function usePrefersDark() {
  const query = '(prefers-color-scheme: dark)'
  const [dark, setDark] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const on = () => setDark(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return dark
}

type AltarState = {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (t: Theme) => void
  layout: Layout
  setLayout: (f: (l: Layout) => Layout) => void
  pinned: string[]
  togglePin: (id: string) => void
  go: (s: Section) => void
  /** Right-sidebar panes offered by the current page, in title-bar order. */
  sideTabs: SideTab[]
  setSideTabs: (t: SideTab[]) => void
  sideTab: SideTab
  /** Title-bar toggle: opens the sidebar on that pane, or closes it if that pane is already showing. */
  toggleSideTab: (t: SideTab) => void
}

export type SideTab = 'circle' | 'files' | 'terminal' | 'browser' | 'inspector' | 'chat'

const Ctx = createContext<AltarState | null>(null)

export function AltarProvider({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const [theme, setThemeState] = useState<Theme>(() => {
    const t = load<{ v: Theme }>('theme', { v: 'light' }).v
    return t === 'system' || t === 'dark' ? t : 'light'
  })
  const [layout, setLayoutState] = useState<Layout>(() => {
    const l = load<Layout>('layout', DEFAULT_LAYOUT)
    return { ...DEFAULT_LAYOUT, ...l, w: { ...DEFAULT_LAYOUT.w, ...l.w } }
  })
  const [pinned, setPinned] = useState<string[]>(() => loadList('pinned', DEFAULT_PINNED))
  const prefersDark = usePrefersDark()
  const resolvedTheme = theme === 'system' ? (prefersDark ? 'dark' : 'light') : theme

  const setTheme = useCallback((t: Theme) => { setThemeState(t); save('theme', { v: t }) }, [])
  const setLayout = useCallback((f: (l: Layout) => Layout) => {
    setLayoutState((old) => { const next = f(old); save('layout', next); return next })
  }, [])
  const togglePin = useCallback((id: string) => {
    setPinned((p) => { const next = p.includes(id) ? p.filter((x) => x !== id) : [...p, id]; save('pinned', next); return next })
  }, [])
  const go = useCallback((s: Section) => navigate(`/${s}`), [navigate])

  const [sideTabs, setSideTabsState] = useState<SideTab[]>([])
  const [sideTabRaw, setSideTabRaw] = useState<SideTab>('circle')
  const sideTab = sideTabs.includes(sideTabRaw) ? sideTabRaw : (sideTabs[0] ?? sideTabRaw)
  const setSideTabs = useCallback((t: SideTab[]) => {
    setSideTabsState((old) => (old.length === t.length && old.every((x, i) => x === t[i]) ? old : t))
  }, [])
  const toggleSideTab = useCallback((t: SideTab) => {
    setLayout((l) => {
      const showing = l.side && sideTab === t
      return { ...l, side: !showing }
    })
    setSideTabRaw(t)
  }, [setLayout, sideTab])

  // The page background behind the app follows the resolved appearance.
  useEffect(() => { document.documentElement.style.colorScheme = resolvedTheme }, [resolvedTheme])

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme, layout, setLayout, pinned, togglePin, go, sideTabs, setSideTabs, sideTab, toggleSideTab }),
    [theme, resolvedTheme, setTheme, layout, setLayout, pinned, togglePin, go, sideTabs, setSideTabs, sideTab, toggleSideTab],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAltar(): AltarState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAltar must be used inside <AltarProvider>')
  return v
}

/** Sets the browser tab title for the current page. */
export function usePageTitle(title: string) {
  useEffect(() => { document.title = `${title} · LychD Altar` }, [title])
}
