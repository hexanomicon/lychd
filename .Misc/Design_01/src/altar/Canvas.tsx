import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Minus, Plus, Maximize } from 'lucide-react'

const ORIGIN = { x: 24, y: 64 }
const MIN_FIT = 0.75
const clamp = (s: number) => Math.min(2, Math.max(0.4, s))

/**
 * A pannable, zoomable dotted canvas. Drag (or scroll) to pan, Ctrl/⌘ + scroll or the buttons to zoom.
 * `contentWidth` lets the canvas fit its content to the available width on first show and on resize.
 */
export function Canvas({
  children,
  overlay,
  contentWidth,
  zoomPosition = 'top-right',
}: {
  children: React.ReactNode
  overlay?: React.ReactNode
  contentWidth?: number
  zoomPosition?: 'top-right' | 'bottom-right'
}) {
  const [v, setV] = useState({ ...ORIGIN, s: 1 })
  const ref = useRef<HTMLDivElement>(null)
  const drag = useRef<[number, number] | null>(null)
  const touched = useRef(false)

  const fit = useCallback(() => {
    const el = ref.current
    if (!el || !contentWidth) return setV({ ...ORIGIN, s: 1 })
    // Never shrink below a readable scale; wider content stays reachable by panning.
    const s = clamp(Math.max(MIN_FIT, Math.min(1, (el.clientWidth - 2 * ORIGIN.x) / contentWidth)))
    setV({ ...ORIGIN, s })
  }, [contentWidth])

  // Fit on first show and whenever the canvas is resized, until the user pans or zooms.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    fit()
    const ro = new ResizeObserver(() => { if (!touched.current) fit() })
    ro.observe(el)
    return () => ro.disconnect()
  }, [fit])

  const zoom = (d: number) => {
    if (d === 0) { touched.current = false; return fit() }
    touched.current = true
    setV((o) => ({ ...o, s: clamp(o.s + d * 0.1) }))
  }

  // Wheel needs a non-passive listener to stop the page from scrolling.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      touched.current = true
      if (e.ctrlKey || e.metaKey) setV((o) => ({ ...o, s: clamp(o.s - e.deltaY * 0.002) }))
      else setV((o) => ({ ...o, x: o.x - e.deltaX, y: o.y - e.deltaY }))
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [])

  const pos = zoomPosition === 'top-right' ? 'right-4 top-4' : 'right-4 bottom-4'
  return (
    <div
      ref={ref}
      className="dotgrid relative min-h-0 flex-1 cursor-grab touch-none overflow-hidden bg-bg active:cursor-grabbing"
      style={{ backgroundPosition: `${v.x}px ${v.y}px`, backgroundSize: `${22 * v.s}px ${22 * v.s}px` }}
      onPointerDown={(e) => {
        if ((e.target as HTMLElement).closest('[data-nodrag]')) return
        drag.current = [e.clientX - v.x, e.clientY - v.y]
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (!drag.current) return
        touched.current = true
        const [ox, oy] = drag.current
        setV((o) => ({ ...o, x: e.clientX - ox, y: e.clientY - oy }))
      }}
      onPointerUp={() => (drag.current = null)}
    >
      <div className="absolute left-0 top-0 origin-top-left" style={{ transform: `translate(${v.x}px,${v.y}px) scale(${v.s})` }}>
        {children}
      </div>
      <div data-nodrag className={`absolute z-[5] flex items-center gap-0.5 rounded-xl border border-line bg-raise p-1 shadow-card ${pos}`}>
        <ZBtn label="Zoom out" onClick={() => zoom(-1)}><Minus className="size-4" strokeWidth={1.6} /></ZBtn>
        <span className="min-w-[52px] text-center text-[12.5px] text-ink2" aria-live="polite">{Math.round(v.s * 100)}%</span>
        <ZBtn label="Zoom in" onClick={() => zoom(1)}><Plus className="size-4" strokeWidth={1.6} /></ZBtn>
        <ZBtn label="Fit to view" onClick={() => zoom(0)}><Maximize className="size-4" strokeWidth={1.6} /></ZBtn>
      </div>
      {overlay}
    </div>
  )
}

function ZBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button title={label} aria-label={label} onClick={onClick} className="grid h-7 place-items-center rounded-[7px] px-2.5 text-ink2 transition-colors duration-150 hover:bg-hover hover:text-ink">
      {children}
    </button>
  )
}
