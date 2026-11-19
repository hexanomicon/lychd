import { Layers, Plus } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { SidePanes } from '../altar/SidePanes'
import { Btn, Kicker, ListItem, PageWrap, Pill, Search, SectionHead, Table, Tile } from '../altar/ui'

const CONCERNS = [
  ['Light and dark appearances accepted in ADR 15', 'warn', 'Insufficient', 'Today', 'adr/15'],
  ['Left rail replaces masthead navigation', 'neutral', 'Unassessed', 'Today', 'adr/15'],
  ['Terminal, Files and Browser contracts', 'bad', 'Disputed', 'Yesterday', 'run_41c2e0'],
  ['Turn strip at half height', 'ok', 'Sufficient', 'Today', 'séance · File navigation'],
] as const

export default function Atlas() {
  const icon = <Layers className="size-4" strokeWidth={1.6} />
  return (
    <Shell
      section="atlas"
      crumb="Atlas"
      title="Altar redesign"
      status={{ tone: 'ok', label: 'Active' }}
      ctxTitle="Projects"
      ctx={
        <>
          <Search placeholder="Search projects" />
          <ListItem on icon={icon} title="Altar redesign" sub="Active · 6 concerns" />
          <ListItem icon={icon} title="Desktop Tether" sub="Active · 3 concerns" />
          <ListItem icon={icon} title="Founding trial" sub="Paused" />
        </>
      }
      side={<SidePanes mode="page" />}
    >
      <PageWrap title="Altar redesign" lead="One shell for every section, light and dark, with portable Bridge.">
        <div className="mb-6 grid gap-3.5 [grid-template-columns:repeat(auto-fill,minmax(220px,1fr))]">
          {[
            ['Concerns', '6', '2 insufficient · 1 disputed · 3 unassessed'],
            ['Decisions', '5', 'Last: tab management, 19 Nov'],
            ['References', '12', '8 séances · 4 runs'],
          ].map(([k, n, s]) => (
            <Tile key={k}>
              <Kicker>{k}</Kicker>
              <div className="mb-0.5 mt-1.5 text-[26px] font-semibold tracking-tight">{n}</div>
              <span className="text-ink2">{s}</span>
            </Tile>
          ))}
        </div>
        <SectionHead title="Concerns">
          <Btn sm><Plus className="size-4" strokeWidth={1.6} />Add concern</Btn>
        </SectionHead>
        <Table head={['Concern', 'Assessment', 'Updated', 'References']}>
          {CONCERNS.map(([c, t, a, u, r]) => (
            <tr key={c}>
              <td>{c}</td>
              <td><Pill tone={t}>{a}</Pill></td>
              <td className="whitespace-nowrap text-ink2">{u}</td>
              <td className="font-mono text-[12.5px]">{r}</td>
            </tr>
          ))}
        </Table>
      </PageWrap>
    </Shell>
  )
}
