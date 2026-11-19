import React, { useState } from 'react'
import { Check, Target, Globe, File as FileIcon, ChevronDown, SkipBack, Play, SkipForward, type LucideIcon } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { SidePanes } from '../altar/SidePanes'
import { Canvas } from '../altar/Canvas'
import { Dot, Kicker, ListItem, Pill, Search, Segmented, Spinner } from '../altar/ui'

type Station = { name: string; x: number; y: number; kind: 'done' | 'run' | 'wait' | 'queued' }

const STATIONS: Station[] = [
  { name: 'Intent', x: 40, y: 100, kind: 'done' },
  { name: 'Router', x: 200, y: 100, kind: 'done' },
  { name: 'Find docs', x: 360, y: 100, kind: 'done' },
  { name: 'Draft', x: 520, y: 100, kind: 'done' },
  { name: 'Review', x: 680, y: 100, kind: 'wait' },
  { name: 'Intent', x: 40, y: 310, kind: 'done' },
  { name: 'Router', x: 190, y: 310, kind: 'done' },
  { name: 'Search', x: 352, y: 272, kind: 'run' },
  { name: 'Inspect', x: 352, y: 348, kind: 'run' },
  { name: 'Summarize', x: 510, y: 310, kind: 'queued' },
]

const WORD = { done: 'complete', run: 'running', wait: 'waiting for you', queued: 'queued' }

export default function Orb() {
  const [sel, setSel] = useState('Search')
  const [filter, setFilter] = useState('All')

  return (
    <Shell
      section="orb"
      crumb="Orb"
      title="Run field"
      status={{ tone: 'ok', label: '2 running' }}
      ctxTitle="Runs"
      ctx={
        <>
          <Search placeholder="Filter runs" />
          <div className="mb-3"><Segmented options={['All', 'Running', 'Waiting', 'Failed']} value={filter} onChange={setFilter} /></div>
          <ListItem icon={<span className="mt-1.5 block"><Dot tone="warn" /></span>} title="Update docs" sub="run_8a1f02 · waiting for you" mono />
          <ListItem on icon={<span className="mt-1.5 block"><Dot /></span>} title="Investigate flaky CI" sub="run_41c2e0 · running 42s" mono />
          <ListItem icon={<span className="mt-1.5 block"><Dot tone="idle" /></span>} title="Release notes 0.4" sub="run_77b9d1 · settled" mono />
          <ListItem icon={<span className="mt-1.5 block"><Dot tone="bad" /></span>} title="Crawl sources" sub="run_0c93aa · gate refused" mono />
        </>
      }
      side={<SidePanes mode="canvas" inspectorTitle={sel} />}
    >
      <Canvas
        contentWidth={1110}
        overlay={
          <>
            <div data-nodrag className="absolute left-4 top-4 z-[5] flex items-center gap-0.5 rounded-xl border border-line bg-raise p-1 shadow-card">
              {['Runs', 'View', 'Runtime', 'Evidence'].map((l) => (
                <button key={l} className="flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[12.5px] text-ink2 transition-colors duration-150 hover:bg-hover hover:text-ink">
                  {l} <ChevronDown className="size-4" strokeWidth={1.6} />
                </button>
              ))}
            </div>
            <div data-nodrag className="absolute bottom-4 left-4 right-4 z-[5] flex h-11 items-center gap-3 rounded-xl border border-line bg-raise px-3 shadow-card sm:right-[200px]">
              <b className="whitespace-nowrap text-[13px] font-semibold">Tab history</b>
              {[SkipBack, Play, SkipForward].map((I, i) => (
                <button key={i} aria-label={['Previous', 'Play', 'Next'][i]} className="grid size-7 place-items-center rounded-[7px] text-ink2 hover:bg-hover"><I className="size-4" strokeWidth={1.6} /></button>
              ))}
              <Pill plain>1×</Pill>
              <div className="relative h-1 flex-1 rounded-sm bg-sunk"><i className="absolute inset-y-0 left-0 w-[78%] rounded-sm bg-line2" /></div>
              <span className="flex h-6 items-center gap-1.5 rounded-full bg-primary px-2.5 text-[11px] font-bold tracking-wide text-onprimary"><span className="size-1.5 rounded-full bg-ok" />LIVE</span>
            </div>
            <div className="absolute bottom-4 right-4 z-[5] hidden h-[104px] w-[168px] rounded-xl border border-line bg-raise p-2 shadow-card sm:block">
              <i className="absolute left-2.5 top-3 h-4 w-[90px] rounded-[3px] bg-sunk" />
              <i className="absolute left-2.5 top-9 h-7 w-[72px] rounded-[3px] bg-sunk" />
              <i className="absolute left-[110px] top-9 h-[30px] w-10 rounded-[3px] bg-sunk" />
              <i className="absolute left-[84px] top-[72px] h-[22px] w-[60px] rounded-[3px] bg-sunk" />
              <b className="absolute left-1.5 top-2 h-16 w-[110px] rounded border-[1.5px] border-primary" />
            </div>
          </>
        }
      >
        <svg className="pointer-events-none absolute left-0 top-0 z-[1] overflow-visible fill-none stroke-line2" strokeWidth="1.5" width="1400" height="900">
          <path d="M168 128 H200" /><path d="M328 128 H360" /><path d="M488 128 H520" /><path d="M648 128 H680" />
          <path d="M168 338 H190" />
          <g strokeDasharray="4 4">
            <path d="M480 300 C496 300 494 338 510 338" /><path d="M480 376 C496 376 494 338 510 338" />
            <path d="M416 272 C416 220 760 230 840 300" /><path d="M736 156 C760 260 860 520 880 560" /><path d="M416 404 C420 520 560 560 610 580" />
          </g>
          <path d="M318 338 C340 338 330 300 352 300" /><path d="M318 338 C340 338 330 376 352 376" />
          <g className="fill-ink3 stroke-none text-[11px]"><text x="540" y="222">dispatch</text><text x="808" y="420">edit</text><text x="470" y="520">read</text></g>
        </svg>

        <Territory x={24} y={60} w={800} h={120} name="Update docs" id="run_8a1f02" pill={<Pill tone="warn">Waiting for you</Pill>} />
        <Territory x={24} y={220} w={640} h={220} name="Investigate flaky CI" id="run_41c2e0" pill={<Pill tone="ok">Running</Pill>} />

        {STATIONS.map((s, i) => (
          <button
            key={i}
            data-nodrag
            onClick={() => setSel(s.name)}
            style={{ left: s.x, top: s.y }}
            className={`absolute z-[2] flex h-14 w-32 flex-col justify-center rounded-xl border bg-panel px-2.5 py-2 text-left shadow-card transition-colors duration-150 ${
              s.kind === 'run' ? 'border-primary ring-1 ring-primary' : s.kind === 'wait' ? 'border-warn' : s.kind === 'queued' ? 'border-dashed border-line2' : 'border-line2'
            } ${sel === s.name && s.kind === 'run' ? 'outline-2 outline-offset-2 outline-primary' : ''}`}
          >
            <b className="flex items-center gap-1.5 text-[12.5px] font-semibold">
              {s.kind === 'done' && <Check className="size-3.5 text-ok" strokeWidth={1.6} />}
              {s.kind === 'run' && <Spinner />}
              {s.kind === 'wait' && <Target className="size-3.5" strokeWidth={1.6} />}
              {s.name}
            </b>
            <span className={`text-[11px] ${s.kind === 'wait' ? 'text-warn' : 'text-ink3'}`}>{WORD[s.kind]}</span>
          </button>
        ))}

        <Group x={840} y={250} w={230} title="Animators" rows={[[Target, 'qwen3:14b', 'local'], [Target, 'claude', 'CLI']]} />
        <Group x={600} y={540} w={230} title="Reach" rows={[[Globe, 'GitHub', 'read'], [Globe, 'Discord', 'post']]} />
        <Group x={860} y={520} w={240} title="Files" rows={[[FileIcon, 'docs/guide.md', 'edit'], [FileIcon, 'tests/test_ci.py', 'read']]} />
      </Canvas>
    </Shell>
  )
}

function Territory({ x, y, w, h, name, id, pill }: { x: number; y: number; w: number; h: number; name: string; id: string; pill: React.ReactNode }) {
  return (
    <div style={{ left: x, top: y, width: w, height: h }} className="absolute z-0 rounded-2xl border border-line bg-panel/70 shadow-card">
      <header className="flex items-center gap-2.5 px-4 py-3">
        <b className="font-semibold">{name}</b>
        <span className="font-mono text-[12.5px] text-ink3">{id}</span>
        <span className="flex-1" />
        {pill}
      </header>
    </div>
  )
}

function Group({ x, y, w, title, rows }: { x: number; y: number; w: number; title: string; rows: [LucideIcon, string, string][] }) {
  return (
    <div style={{ left: x, top: y, width: w }} className="absolute z-[2] rounded-2xl border border-dashed border-line2 p-2.5">
      <Kicker>{title}</Kicker>
      {rows.map(([I, n, m]) => (
        <div key={n} className="mt-2 flex h-[34px] items-center gap-2 rounded-lg border border-line bg-panel px-2.5 text-[12.5px] font-medium">
          <I className="size-4" strokeWidth={1.6} />
          {n}
          <span className="ml-auto font-mono text-[11px] text-ink3">{m}</span>
        </div>
      ))}
    </div>
  )
}
