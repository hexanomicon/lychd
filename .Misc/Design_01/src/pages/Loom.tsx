import { useState } from 'react'
import { Check, MessageSquare, GitBranch } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { SidePanes } from '../altar/SidePanes'
import { Canvas } from '../altar/Canvas'
import { Dot, Kicker, ListItem, Search, Spinner } from '../altar/ui'

type Card = { name: string; sub: string; foot: string; x: number; y: number; done: boolean }

const CARDS: Card[] = [
  { name: 'Target state', sub: 'Complete', foot: 'Expected behaviour · 3 criteria', x: 182, y: 156, done: true },
  { name: 'Current state', sub: 'Complete', foot: 'Repository baseline · 4 findings', x: 622, y: 156, done: true },
  { name: 'Difference', sub: 'Complete', foot: 'Gap & acceptance criteria', x: 402, y: 292, done: true },
  { name: 'Issue history', sub: 'Similar regressions', foot: '2 evidence packets · 18s', x: 132, y: 444, done: true },
  { name: 'Repository explorer', sub: 'Tracing filter → query', foot: 'Exploring · 42s · 3 probes', x: 402, y: 444, done: false },
  { name: 'Test coverage', sub: 'Existing search tests', foot: 'Exploring · 26s · 2 probes', x: 672, y: 444, done: false },
]

export default function Loom() {
  const [sel, setSel] = useState('Repository explorer')
  const flow = <GitBranch className="size-4" strokeWidth={1.6} />

  return (
    <Shell
      section="loom"
      crumb="Loom / Runs"
      title="Resolve GitHub issue #553"
      status={{ tone: 'ok', label: 'Running' }}
      ctxTitle="Patterns"
      ctx={
        <>
          <Search placeholder="Search patterns" />
          <ListItem on icon={flow} title="resolve_issue" mono right="@4" />
          <ListItem icon={flow} title="bridge_chat" mono right="@4" />
          <ListItem icon={flow} title="investigate_ci" mono right="@2" />
          <Kicker className="mx-1.5 mb-1.5 mt-4">Revisions</Kicker>
          <ListItem icon={<span className="mt-1.5 block"><Dot /></span>} title="@4" sub="current · 2 days ago" mono />
          <ListItem icon={<span className="mt-1.5 block"><Dot tone="idle" /></span>} title="@3" sub="superseded" mono />
        </>
      }
      side={<SidePanes mode="canvas" inspectorTitle={sel} />}
    >
      <Canvas
        contentWidth={930}
        zoomPosition="bottom-right"
        overlay={
          <div className="absolute bottom-4 left-4 z-[5] flex items-center gap-4 text-xs text-ink2">
            <span className="flex items-center gap-1.5"><Dot />Complete</span>
            <span className="flex items-center gap-1.5"><Spinner size={11} />Running</span>
            <span className="flex items-center gap-1.5"><Dot tone="idle" />Queued</span>
          </div>
        }
      >
        <svg className="pointer-events-none absolute left-0 top-0 z-[1] overflow-visible fill-none stroke-line2" strokeWidth="1.5" width="1200" height="800">
          <path d="M520 104 V130 M300 156 V130 H740 V156" />
          <path d="M300 248 V270 H740 V248 M520 270 V292" />
          <path d="M520 384 V420 M250 444 V420 H790 V444" />
          <path strokeDasharray="4 4" d="M250 536 V560 H790 V536 M520 560 V584" />
        </svg>
        <Kicker className="absolute left-6 top-[140px] whitespace-nowrap">01 Understand</Kicker>
        <Kicker className="absolute left-6 top-[428px] whitespace-nowrap">02 Explore</Kicker>

        <div data-nodrag className="absolute z-[2] w-[236px] cursor-pointer rounded-2xl border border-line bg-panel shadow-card" style={{ left: 402, top: 40 }}>
          <div className="flex gap-2.5 px-3.5 py-3">
            <MessageSquare className="mt-0.5 size-4 flex-none" strokeWidth={1.6} />
            <div><b className="block text-[13.5px] font-semibold">Resolve issue #553</b><span className="text-xs text-ink3">Intent · GitHub</span></div>
            <Check className="ml-auto size-4 flex-none text-ok" strokeWidth={1.6} />
          </div>
        </div>

        {CARDS.map((c) => (
          <button
            key={c.name}
            data-nodrag
            onClick={() => setSel(c.name)}
            style={{ left: c.x, top: c.y }}
            className={`absolute z-[2] w-[236px] cursor-pointer rounded-2xl border bg-panel text-left shadow-card transition-colors duration-150 ${sel === c.name ? 'border-primary ring-1 ring-primary' : 'border-line'}`}
          >
            <div className="flex gap-2.5 px-3.5 py-3">
              {c.done ? (
                <span className="grid size-6 flex-none place-items-center rounded-[7px] bg-oksoft text-ok"><Check className="size-3.5" strokeWidth={1.6} /></span>
              ) : (
                <span className="m-[5px] flex-none"><Spinner /></span>
              )}
              <div><b className="block text-[13.5px] font-semibold">{c.name}</b><span className="text-xs text-ink3">{c.sub}</span></div>
            </div>
            <div className="border-t border-line px-3.5 py-[9px] text-xs text-ink2">{c.foot}</div>
          </button>
        ))}

        <div className="absolute z-[2] flex h-[46px] items-center justify-center gap-7 whitespace-nowrap rounded-2xl border border-dashed border-line2 bg-sunk text-[13px] text-ink2" style={{ left: 182, top: 584, width: 680 }}>
          03 Crucible &amp; decision <span className="text-ink3">→</span> 04 Implementation <span className="text-ink3">→</span> 05 Verification
        </div>
      </Canvas>
    </Shell>
  )
}
