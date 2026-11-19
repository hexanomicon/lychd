import { Plus } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { SidePanes } from '../altar/SidePanes'
import { Btn, Dot, ListItem, PageWrap, Pill, Search, SectionHead, Table, Tile, type Tone } from '../altar/ui'

const CAPS: [string, Tone, string, string, string][] = [
  ['Inference', 'ok', 'Ready', '3 targets · default qwen3:14b', 'Observed 12s ago'],
  ['Sandbox', 'ok', 'Ready', 'exec · read · write (after approval)', 'Observed 40s ago'],
  ['Network reach', 'warn', 'Pending', '1 typed request awaiting review', 'Observed 2m ago'],
  ['Storage', 'neutral', 'Unknown', 'no fresh observation', 'Stale · 3h'],
]

const PLAN = [
  ['default', 'Qwen3.5-27B', 'http://127.0.0.1:8000/v1', 'Configured', 'default'],
  ['claude', 'CLI default', 'local CLI', 'Installed', 'strong_reasoning#1, writer#2'],
  ['qwen38', 'Qwen3.6-27B', 'http://127.0.0.1:8000/v1', 'Configured', 'writer#1, general#1'],
]

export default function Nexus() {
  return (
    <Shell
      section="nexus"
      crumb="Nexus"
      title="Capabilities"
      status={{ tone: 'ok', label: 'Ready' }}
      ctxTitle="Capabilities"
      ctx={
        <>
          <Search placeholder="Filter capabilities" />
          <ListItem on icon={<span className="mt-1.5 block"><Dot /></span>} title="Inference" sub="3 targets" />
          <ListItem icon={<span className="mt-1.5 block"><Dot /></span>} title="Sandbox" sub="exec · read · write" />
          <ListItem icon={<span className="mt-1.5 block"><Dot tone="warn" /></span>} title="Network reach" sub="1 pending request" />
        </>
      }
      side={<SidePanes mode="page" />}
    >
      <PageWrap title="Nexus" lead="What this instance can do right now. Observations are read-only; changes go through typed requests.">
        <div className="mb-6 grid gap-3.5 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
          {CAPS.map(([n, t, s, d, o]) => (
            <Tile key={n}>
              <div className="mb-2.5 flex items-center justify-between gap-2"><b className="font-semibold">{n}</b><Pill tone={t}>{s}</Pill></div>
              <div className="font-mono text-[12.5px] text-ink2">{d}</div>
              <div className="mt-2 text-xs text-ink3">{o}</div>
            </Tile>
          ))}
        </div>
        <SectionHead title="Plan preview"><span className="text-ink3">Nonbinding</span></SectionHead>
        <div className="mb-6">
          <Table head={['Target', 'Model', 'Endpoint', 'State', 'Role order']}>
            {PLAN.map(([a, b, c, d, e]) => (
              <tr key={a} className="font-mono text-[12.5px]">
                <td>{a}</td><td className="whitespace-nowrap">{b}</td><td className="whitespace-nowrap">{c}</td>
                <td className="font-sans"><Pill tone="ok">{d}</Pill></td><td>{e}</td>
              </tr>
            ))}
          </Table>
        </div>
        <SectionHead title="Tickets">
          <Btn sm><Plus className="size-4" strokeWidth={1.6} />New request</Btn>
        </SectionHead>
        <Table head={['Ticket', 'Request', 'Status', 'Updated']}>
          <tr><td className="font-mono text-[12.5px]">tk_0193</td><td>Allow outbound fetch to hexanomicon.dev</td><td><Pill tone="warn">Awaiting review</Pill></td><td className="whitespace-nowrap text-ink2">2m ago</td></tr>
          <tr><td className="font-mono text-[12.5px]">tk_0192</td><td>Warm qwen3 on forge-3090</td><td><Pill tone="ok">Done</Pill></td><td className="whitespace-nowrap text-ink2">1h ago</td></tr>
        </Table>
      </PageWrap>
    </Shell>
  )
}
