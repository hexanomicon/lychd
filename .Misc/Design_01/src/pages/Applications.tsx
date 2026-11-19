import { useState } from 'react'
import { ChevronDown, Pin } from 'lucide-react'

import { Shell, APP_ICONS } from '../altar/Shell'
import { useAltar } from '../altar/store'
import { SidePanes } from '../altar/SidePanes'
import { ListItem, PageWrap, Search } from '../altar/ui'
import { APPS } from '../altar/data'

const AREAS = ['All areas', 'Research', 'Media', 'Language', 'Commerce']

export default function Applications() {
  const { pinned, togglePin } = useAltar()
  const [q, setQ] = useState('')
  const [area, setArea] = useState('All areas')
  const [areaOpen, setAreaOpen] = useState(false)
  const list = APPS.filter((a) => a.name.toLowerCase().includes(q.toLowerCase()) && (area === 'All areas' || a.area === area))
  const areas = AREAS

  return (
    <Shell
      section="apps"
      crumb="Applications"
      title="All applications"
      ctxTitle="Areas"
      ctx={areas.map((a) => (
        <ListItem key={a} on={a === area} onClick={() => setArea(a)} title={a} />
      ))}
      side={<SidePanes mode="page" />}
    >
      <PageWrap title="Applications" lead="Admitted applications. Pin the ones you use to keep them in the rail.">
        <div className="mb-[18px] flex flex-wrap items-center gap-2.5">
          <div className="w-full sm:w-[360px]"><Search placeholder="Find an app" value={q} onChange={setQ} /></div>
          <div className="relative">
            <button
              aria-haspopup="listbox"
              aria-expanded={areaOpen}
              onClick={() => setAreaOpen((o) => !o)}
              className="flex h-10 min-w-[170px] items-center justify-between gap-2 rounded-xl border border-line bg-panel px-3 shadow-card transition-colors duration-150 hover:bg-hover"
            >
              {area}<ChevronDown className={`size-4 transition-transform duration-150 ${areaOpen ? 'rotate-180' : ''}`} strokeWidth={1.6} />
            </button>
            {areaOpen && (
              <div role="listbox" className="absolute left-0 top-11 z-20 w-full rounded-xl border border-line2 bg-raise p-1.5 shadow-pop">
                {AREAS.map((a) => (
                  <button
                    key={a}
                    role="option"
                    aria-selected={a === area}
                    onClick={() => { setArea(a); setAreaOpen(false) }}
                    className={`flex h-8 w-full items-center rounded-lg px-2.5 text-left text-[13px] hover:bg-hover ${a === area ? 'bg-sel font-semibold' : ''}`}
                  >
                    {a}
                  </button>
                ))}
              </div>
            )}
          </div>
          <span className="flex-1" />
          <span className="text-ink3">{APPS.length} applications · {APPS.filter((a) => pinned.includes(a.id)).length} pinned</span>
        </div>
        {list.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line2 px-6 py-10 text-center text-ink2">
            No applications match “{q}”{area !== 'All areas' ? ` in ${area}` : ''}.
          </div>
        )}
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(280px,1fr))]">
          {list.map((a) => {
            const I = APP_ICONS[a.icon]
            const on = pinned.includes(a.id)
            return (
              <article key={a.id} className="flex flex-col rounded-2xl border border-line bg-panel p-3.5 shadow-card">
                <div className="relative grid h-[140px] place-items-center rounded-xl bg-sunk text-ink3">
                  <I className="size-14" strokeWidth={1.2} />
                  <button
                    title={on ? 'Unpin' : 'Pin'}
                    aria-pressed={on}
                    aria-label={`${on ? 'Unpin' : 'Pin'} ${a.name}`}
                    onClick={() => togglePin(a.id)}
                    className={`absolute right-2.5 top-2.5 grid size-7 place-items-center rounded-lg border bg-panel transition-colors duration-150 ${on ? 'border-primary bg-accentsoft text-accent' : 'border-line text-ink3'}`}
                  >
                    <Pin className="size-4" strokeWidth={1.6} />
                  </button>
                </div>
                <h3 className="m-0 mb-0.5 mt-3.5 text-[17px] font-semibold">{a.name}</h3>
                <p className="m-0 mb-3.5 text-ink2">{a.blurb}</p>
                <span className="mt-auto font-semibold text-accent">{a.action} →</span>
              </article>
            )
          })}
        </div>
      </PageWrap>
    </Shell>
  )
}
