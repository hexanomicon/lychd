import React, { useEffect, useState } from 'react'
import {
  Target, File as FileIcon, Terminal, Globe, PanelRight, MessageSquare, ChevronDown, ChevronRight, Folder, Search,
  Plus, ArrowUp, Check, X, type LucideIcon,
} from 'lucide-react'
import { useAltar, type SideTab } from './store'
import { Dot, IconBtn, Kicker, Kv, Pill, Spinner, Tile } from './ui'

type TabId = SideTab

/** Pane names and icons; the window title bar shows these as the sidebar toggles. */
export const SIDE_TABS: Record<TabId, { label: string; Icon: LucideIcon }> = {
  circle: { label: 'Circle', Icon: Target },
  files: { label: 'Files', Icon: FileIcon },
  terminal: { label: 'Terminal', Icon: Terminal },
  browser: { label: 'Browser', Icon: Globe },
  inspector: { label: 'Inspector', Icon: PanelRight },
  chat: { label: 'Bridge', Icon: MessageSquare },
}

const MODES: Record<'bridge' | 'canvas' | 'page', TabId[]> = {
  bridge: ['circle', 'files', 'terminal', 'browser'],
  canvas: ['inspector', 'chat'],
  page: ['chat'],
}

export function SidePanes({
  mode,
  inspectorTitle = 'Repository explorer',
  onGoto,
}: {
  mode: 'bridge' | 'canvas' | 'page'
  inspectorTitle?: string
  onGoto?: (s: 'loom' | 'orb') => void
}) {
  const { sideTab: tab, setSideTabs, setLayout } = useAltar()
  useEffect(() => { setSideTabs(MODES[mode]) }, [mode, setSideTabs])
  const { label, Icon } = SIDE_TABS[tab]
  return (
    <>
      <div className="flex h-12 flex-none items-center gap-2 border-b border-line pl-4 pr-2.5">
        <Icon className="size-4 text-ink2" strokeWidth={1.6} />
        <h2 className="m-0 text-[13.5px] font-semibold">{label}</h2>
        <span className="flex-1" />
        <IconBtn title="Close panel" onClick={() => setLayout((l) => ({ ...l, side: false }))}><X className="size-4" strokeWidth={1.6} /></IconBtn>
      </div>
      {tab === 'circle' && <Circle onGoto={onGoto} />}
      {tab === 'files' && <Files />}
      {tab === 'terminal' && <Term />}
      {tab === 'browser' && <Browser />}
      {tab === 'inspector' && <Inspector title={inspectorTitle} />}
      {tab === 'chat' && <MiniChat />}
    </>
  )
}

function Circle({ onGoto }: { onGoto?: (s: 'loom' | 'orb') => void }) {
  const stations = [
    { n: 'admit', d: 'Intent admitted, invocation opened', t: 'ok' as const },
    { n: 'gate', d: 'Graph Stasis · holds no lease', t: 'warn' as const },
    { n: 'settle', d: 'Not started', t: 'idle' as const },
  ]
  return (
    <div className="min-h-0 flex-1 overflow-auto px-5 py-[18px]">
      <div className="flex items-center gap-2 font-semibold text-warn"><Dot tone="warn" />Waiting for consent</div>
      <div className="mb-4 mt-1 font-mono text-[12.5px] text-ink2">Run · run_c41b07e2</div>
      <div className="border-y border-line py-3.5">
        <Kv labelWidth={110} rows={[['Pattern', 'bridge_chat@4'], ['Capability', 'llamacpp:qwen3:14b'], ['Sigil', 'Local · Magus'], ['Capture', 'process-local']]} />
      </div>
      <Kicker className="mt-[18px]">Stations</Kicker>
      <ul className="m-0 mt-3 list-none p-0">
        {stations.map((s, i) => (
          <li key={s.n} className="relative pb-[18px] pl-[22px]">
            <span className={`absolute left-1 top-[7px] size-2 rounded-full ${s.t === 'ok' ? 'bg-ok' : s.t === 'warn' ? 'bg-warn' : 'bg-line2'}`} />
            {i < stations.length - 1 && <span className="absolute bottom-0.5 left-[7.5px] top-[18px] w-px bg-line" />}
            <b className="font-mono text-[13px]">{s.n}</b>
            <span className="block text-[12.5px] text-ink2">{s.d}</span>
          </li>
        ))}
      </ul>
      {([['Open score in Loom', () => onGoto?.('loom')], ['Inspect Run in Orb', () => onGoto?.('orb')], ['Link this conversation to…', undefined]] as const).map(([l, f]) => (
        <button key={l} onClick={f} className="flex h-[38px] w-full items-center justify-between border-t border-line text-left transition-colors duration-150 hover:text-ink2">
          {l} <span>↗</span>
        </button>
      ))}
    </div>
  )
}

function Switcher({ icon: Icon, label, items, onPick, right, addLabel }: {
  icon: LucideIcon; label: string; items: { id: string; right?: string }[]; onPick: (id: string) => void; right?: React.ReactNode; addLabel?: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative flex h-12 flex-none items-center gap-2 border-b border-line px-4">
      <button onClick={() => setOpen((o) => !o)} className="-ml-2 flex items-center gap-2 rounded-[7px] px-2 py-1 font-semibold transition-colors duration-150 hover:bg-hover">
        <Icon className="size-4" strokeWidth={1.6} />
        <span>{label}</span>
        <ChevronDown className="size-4" strokeWidth={1.6} />
      </button>
      <span className="flex-1" />
      {right}
      {open && (
        <div className="absolute left-2.5 top-11 z-10 w-[270px] rounded-[10px] border border-line2 bg-raise p-1.5 shadow-pop">
          {items.map((it) => (
            <button
              key={it.id}
              onClick={() => { onPick(it.id); setOpen(false) }}
              className={`flex h-8 w-full items-center gap-2.5 rounded-[7px] px-2.5 text-[13px] hover:bg-hover ${it.id === label ? 'bg-sel font-semibold' : ''}`}
            >
              {it.id}
              <span className="ml-auto text-[11.5px] font-normal text-ink3">{it.right}</span>
            </button>
          ))}
          {addLabel && <div className="flex h-8 items-center px-2.5 text-[13px] text-ink2">+ {addLabel}</div>}
        </div>
      )}
    </div>
  )
}

function Files() {
  const [file, setFile] = useState('brief.md')
  const [tree, setTree] = useState(true)
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Switcher
        icon={FileIcon}
        label={file}
        items={[{ id: 'brief.md', right: '×' }, { id: 'notes.md', right: '×' }]}
        onPick={setFile}
        addLabel="Open file…"
        right={<Pill plain>Preview</Pill>}
      />
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-auto p-5">
          <h3 className="m-0 mb-2.5 text-xl font-semibold">{file === 'brief.md' ? 'Project brief' : 'Working notes'}</h3>
          <p className="text-ink2">
            {file === 'brief.md'
              ? 'A short project brief for the next iteration of the workspace. It outlines the goal, scope and deliverables to guide the work.'
              : 'Running notes from the last three séances: open questions on consent scope and the turn strip.'}
          </p>
          <p className="text-ink2">Preview · Edit · Diff</p>
        </div>
        {tree ? (
          <div className="w-[190px] flex-none overflow-auto border-l border-line bg-sidebg px-2.5 py-3">
            <div className="mb-2 flex items-center justify-between font-semibold">
              File tree
              <IconBtn title="Collapse tree" onClick={() => setTree(false)}><ChevronRight className="size-4" strokeWidth={1.6} /></IconBtn>
            </div>
            <label className="mb-2 flex h-[34px] items-center gap-2 rounded-lg border border-line bg-panel px-2.5 text-ink3">
              <Search className="size-4 flex-none" strokeWidth={1.6} />
              <input placeholder="Filter files" className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-ink3" />
            </label>
            <TreeRow depth={0} open folder name="lychd" />
            <TreeRow depth={1} open folder name="docs" />
            {['brief.md', 'notes.md'].map((f) => (
              <TreeRow key={f} depth={2} name={f} mono on={file === f} onClick={() => setFile(f)} />
            ))}
            <TreeRow depth={1} folder name="src" />
            <TreeRow depth={1} folder name="tests" />
          </div>
        ) : (
          <button onClick={() => setTree(true)} title="Show file tree" className="w-6 flex-none border-l border-line bg-sidebg text-ink2">
            <ChevronDown className="mx-auto size-4 rotate-90" strokeWidth={1.6} />
          </button>
        )}
      </div>
    </div>
  )
}

function TreeRow({ depth, name, folder, open, mono, on, onClick }: {
  depth: number; name: string; folder?: boolean; open?: boolean; mono?: boolean; on?: boolean; onClick?: () => void
}) {
  return (
    <div
      onClick={onClick}
      style={{ paddingLeft: depth * 14 + 6 }}
      className={`flex h-7 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md pr-1.5 text-[13px] hover:bg-hover ${mono ? 'font-mono' : ''} ${on ? 'bg-sel font-semibold' : ''}`}
    >
      {folder ? (
        <>
          {open ? <ChevronDown className="size-4" strokeWidth={1.6} /> : <ChevronRight className="size-4" strokeWidth={1.6} />}
          <Folder className="size-4" strokeWidth={1.6} />
        </>
      ) : (
        <FileIcon className="size-4" strokeWidth={1.6} />
      )}
      {name}
    </div>
  )
}

function Term() {
  const [shell, setShell] = useState('Shell 2 · tests')
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Switcher
        icon={Terminal}
        label={shell}
        items={[{ id: 'Shell 1 · lychd', right: 'idle' }, { id: 'Shell 2 · tests', right: 'running' }, { id: 'Shell 3 · docs', right: 'running' }]}
        onPick={setShell}
        addLabel="New shell"
        right={<Pill tone="ok">2 running</Pill>}
      />
      <div className="m-4 flex-1 overflow-auto rounded-xl border border-line bg-sunk p-3.5 font-mono text-[12.5px] leading-[1.9]">
        <div>$ uv run pytest tests/test_ci.py -q</div>
        <div className="text-ink2">........................ 24 passed in 3.1s</div>
        <div>$ git status --short</div>
        <div className="whitespace-pre text-ink2"> M src/lychd/web/contracts.py</div>
        <div>$ ▍</div>
      </div>
    </div>
  )
}

function Browser() {
  const [page, setPage] = useState('Nexus — Hexanomicon')
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <Switcher
        icon={Globe}
        label={page}
        items={[{ id: 'Nexus — Hexanomicon', right: 'run_c41b07e2' }, { id: 'State of Work' }]}
        onPick={setPage}
        addLabel="New page"
      />
      <div className="mx-4 mt-3 flex h-8 items-center gap-2 rounded-lg border border-line bg-sunk px-2.5 text-ink2">
        <span>‹ › ⟳</span>
        <span className="truncate font-mono text-[12.5px]">hexanomicon.dev/divination/altar/nexus/</span>
      </div>
      <div className="m-4 mt-3 grid flex-1 place-items-center rounded-[10px] border border-line bg-sidebg p-4 text-center text-ink3">
        Page preview · opened by run_c41b07e2 · read-only
      </div>
    </div>
  )
}

function Inspector({ title }: { title: string }) {
  const [t, setT] = useState('Overview')
  return (
    <div className="min-h-0 flex-1 overflow-auto px-5 py-[18px]">
      <Kicker>Exploration agent</Kicker>
      <h3 className="mb-1 mt-1.5 text-[19px] font-semibold">{title}</h3>
      <div className="flex items-center gap-2.5 text-[12.5px]">
        <Pill tone="ok">Running</Pill>
        <span className="font-mono text-ink3">agent_004 · started 42s ago</span>
      </div>
      <div className="my-3.5 flex gap-[18px] border-b border-line">
        {['Overview', 'Inputs', 'Outputs', 'Logs'].map((x) => (
          <button key={x} onClick={() => setT(x)} className={`pb-2 text-[13px] ${t === x ? 'font-semibold text-accent shadow-[inset_0_-2px_0_var(--accent)]' : 'text-ink2'}`}>{x}</button>
        ))}
      </div>
      <Kv labelWidth={110} rows={[['Model', 'qwen3:14b · local'], ['Orchestrator', 'Exploration lead']]} />
      <p className="mb-0 mt-3 text-ink2">Find the source of stale search results and return a code-grounded evidence packet.</p>
      <div className="my-3.5 rounded-[10px] border border-line bg-sunk px-3.5 py-3">
        <div className="flex items-center gap-2 font-semibold">
          <Spinner />Tracing query invalidation
          <span className="ml-auto text-xs font-normal text-ink3">3 / 8 probes</span>
        </div>
        <div className="relative mt-2.5 h-1 rounded-sm bg-line"><i className="absolute inset-y-0 left-0 w-[38%] rounded-sm bg-primary" /></div>
      </div>
      <div className="mb-3 mt-2 flex items-center justify-between"><h2 className="m-0 text-sm font-semibold">Activity</h2><span className="text-xs text-ink3">View full trace ↗</span></div>
      <ul className="m-0 list-none p-0">
        {[['Opened repository', 'acme/platform · main', '42s', 'idle'], ['Located filter lifecycle', 'src/hooks/useSearch.ts', '31s', 'idle'], ['Inspecting query cache', 'src/lib/queryClient.ts', 'now', 'ok']].map(([a, b, c, d]) => (
          <li key={a} className="flex gap-2.5 border-b border-line py-2 text-[13px]">
            <span className="mt-1.5"><Dot tone={d as 'idle' | 'ok'} /></span>
            <div>{a}<span className="block font-mono text-[11.5px] text-ink3">{b}</span></div>
            <time className="ml-auto whitespace-nowrap text-[11.5px] text-ink3">{c}</time>
          </li>
        ))}
      </ul>
      <div className="mb-3 mt-[18px] flex items-center justify-between"><h2 className="m-0 text-sm font-semibold">Evidence collected</h2><span className="text-xs text-ink3">1 packet</span></div>
      <Tile className="px-3.5 py-3">
        <div className="flex gap-2.5">
          <FileIcon className="mt-0.5 size-4 flex-none" strokeWidth={1.6} />
          <div><b className="font-semibold">Filter reset leaves cached query</b><div className="font-mono text-[12.5px] text-ink3">src/hooks/useSearch.ts : 84–102</div></div>
        </div>
        <div className="mt-2 text-right text-xs font-semibold">Open packet ↗</div>
      </Tile>
    </div>
  )
}

function MiniChat() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-12 flex-none items-center gap-2 border-b border-line px-4 font-semibold">
        <MessageSquare className="size-4" strokeWidth={1.6} />Investigate flaky CI<ChevronDown className="size-4" strokeWidth={1.6} />
      </div>
      <div className="flex min-h-0 flex-1 flex-col overflow-auto px-5 py-[18px] text-[13px]">
        <Msg me>What is this Run waiting on?</Msg>
        <Msg>Search and Inspect are still running; Summarize starts when both report. No consent is pending for this Run.</Msg>
        <Msg me>Open the failing test.</Msg>
        <Msg>Opened <span className="font-mono text-[12.5px]">tests/test_ci.py</span> in Bridge → Files.</Msg>
      </div>
      <div className="m-4 mt-0 flex items-center gap-2 rounded-xl border border-line2 px-3 py-2.5 text-ink3">
        <Plus className="size-4" strokeWidth={1.6} />Ask about this view…
        <button className="ml-auto grid size-7 place-items-center rounded-full bg-primary text-onprimary" aria-label="Send"><ArrowUp className="size-4" strokeWidth={1.6} /></button>
      </div>
    </div>
  )
}

function Msg({ me, children }: { me?: boolean; children: React.ReactNode }) {
  return me ? (
    <div className="mb-3.5 max-w-[85%] self-end rounded-xl border border-line bg-sunk px-3 py-2">{children}</div>
  ) : (
    <div className="mb-3.5"><b className="mb-0.5 block text-[12.5px] font-semibold">LychD</b>{children}</div>
  )
}

export { Check }
