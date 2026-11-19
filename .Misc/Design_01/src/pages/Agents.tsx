import { Users } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { SidePanes } from '../altar/SidePanes'
import { ListItem, PageWrap, Pill, Table } from '../altar/ui'

const AGENTS = [
  ['Scout', 'Public-page acquisition', 'qwen3:14b · local', 'warn', 'Waiting for consent', 'run_c41b07e2'],
  ['Repository explorer', 'Code evidence', 'qwen3:14b · local', 'ok', 'Running', 'run_41c2e0'],
  ['Scribe', 'Docs drafting', 'claude · CLI', 'neutral', 'Idle', 'run_8a1f02'],
  ['Herald', 'Discord replies', 'qwen3:14b · local', 'neutral', 'Idle', 'run_77b9d1'],
] as const

export default function Agents() {
  return (
    <Shell
      section="agents"
      crumb="Agents"
      title="Roster"
      ctxTitle="Roster"
      ctx={
        <>
          <ListItem on icon={<Users className="size-4" strokeWidth={1.6} />} title="All agents" sub="6" />
          <ListItem icon={<Users className="size-4" strokeWidth={1.6} />} title="Running now" sub="2" />
        </>
      }
      side={<SidePanes mode="page" />}
    >
      <PageWrap title="Agents" lead="Who can do work, on which model, and what they are doing now.">
        <Table head={['Agent', 'Role', 'Model', 'State', 'Last run']}>
          {AGENTS.map(([n, r, m, t, s, run]) => (
            <tr key={n}>
              <td className="whitespace-nowrap font-semibold">{n}</td>
              <td>{r}</td>
              <td className="whitespace-nowrap font-mono text-[12.5px]">{m}</td>
              <td><Pill tone={t}>{s}</Pill></td>
              <td className="font-mono text-[12.5px]">{run}</td>
            </tr>
          ))}
        </Table>
      </PageWrap>
    </Shell>
  )
}
