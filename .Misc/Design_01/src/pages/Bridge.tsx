import React, { useEffect, useRef, useState } from 'react'
import { MessageSquare, Pin, Folder, ChevronDown, Plus, Globe, Mic, ArrowUp, Layers, Settings, Bookmark, Sparkle } from 'lucide-react'

import { Shell } from '../altar/Shell'
import { useAltar } from '../altar/store'
import { SidePanes } from '../altar/SidePanes'
import { Btn, Dot, IconBtn, Kicker, Kv, ListItem, Search, Segmented } from '../altar/ui'

export default function Bridge() {
  const { go } = useAltar()
  const [decided, setDecided] = useState<null | 'consecrated' | 'refused'>(null)
  const status = decided
  const awaiting = status === null
  const [draft, setDraft] = useState('')
  const [sent, setSent] = useState<{ id: number; text: string; time: string; reply?: string }[]>([])
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' }) }, [sent])

  const send = () => {
    const text = draft.trim()
    if (!text) return
    const id = Date.now()
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    setSent((s) => [...s, { id, text, time }])
    setDraft('')
    // Prototype only: a placeholder acknowledgement stands in for the real Run.
    window.setTimeout(() => {
      setSent((s) => s.map((m) => (m.id === id ? { ...m, reply: 'Offered as a new turn. A Run will appear in the Circle once the Vessel admits it.' } : m)))
    }, 700)
  }

  return (
    <Shell
      section="bridge"
      crumb="Bridge"
      title="Observatory hours and public notes"
      status={awaiting ? { tone: 'warn', label: '1 awaiting consent' } : status === 'consecrated' ? { tone: 'ok', label: 'Consecrated' } : { tone: 'bad', label: 'Refused' }}
      headerActions={
        <>
          <button className="inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-xl border border-line bg-panel px-3 font-medium text-ink shadow-card transition-colors duration-150 hover:bg-hover"><Layers className="size-4" strokeWidth={1.6} />Browse séances</button>
          <button className="inline-flex h-9 items-center gap-2 whitespace-nowrap rounded-xl border border-line bg-panel px-3 font-medium text-ink shadow-card transition-colors duration-150 hover:bg-hover"><Settings className="size-4" strokeWidth={1.6} />Tools</button>
        </>
      }
      ctxTitle="Séances"
      ctx={<SeanceList />}
      side={<SidePanes mode="bridge" onGoto={(s) => go(s)} />}
    >
      <div className="flex min-h-0 flex-1 flex-col">
        <div className="relative flex min-h-0 flex-1">
          <TurnStrip />
          <div className="min-w-0 flex-1 overflow-auto pb-6 pt-7">
            <div className="mx-auto max-w-[760px] pl-12 pr-5 lg:pr-8">
              <div className="mb-6 rounded-2xl border border-line bg-panel p-4 shadow-card sm:p-5">
                <Who time="14:21" />
                <p className="m-0 ml-9 mt-1 text-[14.5px]">The test observatory closes at 21:00 UTC.</p>
                <p className="m-0 ml-9 mt-1 text-[14.5px] text-ink2">This comes from one promoted public note. Recall selected 1 of 1 eligible notes and omitted nothing.</p>
                <div className="ml-9 mt-3 flex flex-wrap items-center gap-x-3.5 gap-y-1 border-t border-line pt-2.5 text-[12.5px] text-ink2">
                  <span className="flex items-center gap-2"><Dot />Circle</span>
                  <span>Retained reply</span>
                  <span className="flex-1" />
                  <button onClick={() => go('orb')} className="font-medium text-accent hover:underline">Look into the Orb ↗</button>
                </div>
              </div>

              <div className="mb-6 flex flex-col items-end">
                <span className="mb-1 text-xs text-ink3">You · 14:24</span>
                <div className="max-w-[520px] rounded-2xl rounded-tr-md bg-accentsoft px-4 py-3 text-ink">
                  <span className="mb-1 block break-all font-mono text-[12.5px]">/read-public https://hexanomicon.dev/divination/altar/nexus/</span>
                  What does Nexus change when I only view the board?
                </div>
              </div>

              <div className="mb-6 rounded-2xl border border-line bg-panel p-4 shadow-card sm:p-5">
                <Who time="14:26" />
                <p className="m-0 ml-9 mt-1 text-[14.5px]">
                  {status === 'consecrated'
                    ? 'Page fetched. Nexus changes nothing when you only view the board: observations are read-only and changes go through typed requests.'
                    : status === 'refused'
                      ? 'Understood. I will answer from the retained note only and will not fetch the page.'
                      : 'I need to fetch one public page before I can answer. Review the request below.'}
                </p>
                <div className="ml-9 mt-3 flex flex-wrap items-center gap-x-3.5 gap-y-1.5 border-t border-line pt-2.5 text-[12.5px] text-ink2">
                  <span className="flex items-center gap-2"><Dot tone={awaiting ? 'warn' : status === 'refused' ? 'bad' : 'ok'} />Circle</span>
                  {awaiting && <span className="font-semibold text-warn">awaiting consent</span>}
                  <span className="font-mono text-ink3">acquire page</span>
                  <span className="flex-1" />
                  <button onClick={() => go('orb')} className="font-medium text-accent hover:underline">Look into the Orb ↗</button>
                  {awaiting && <Btn sm>Cancel Run</Btn>}
                </div>
                {awaiting && (
                  <div className="mt-4 overflow-hidden rounded-xl border border-line2 bg-panel sm:ml-9">
                    <div className="flex items-center gap-2 border-b border-line bg-warnsoft px-4 py-3 text-[13px] font-semibold text-warn">
                      Consent sought <span className="ml-auto font-mono text-[12.5px] font-normal text-ink2">acquire_public_page</span>
                    </div>
                    <div className="px-4 py-3.5">
                      <h4 className="m-0 mb-2.5 text-[14.5px] font-semibold">Vision: Acquire one public page with Scout</h4>
                      <Kv rows={[
                        ['exact_url', 'https://hexanomicon.dev/divination/altar/nexus/'],
                        ['resolver', 'System DNS sees the hostname'],
                        ['limits', '1 page · 512 KB · 10 s · no redirects'],
                        ['answered_by', 'llamacpp:qwen3:14b-q5_k_m'],
                      ]} />
                      <div className="mt-3.5 flex flex-wrap items-center gap-2">
                        <Btn primary onClick={() => setDecided('consecrated')}>Consecrate</Btn>
                        <Btn onClick={() => setDecided('refused')}>Refuse</Btn>
                        <small className="ml-auto text-[11.5px] text-ink3">The Vessel decides; this card only asks.</small>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {sent.map((m) => (
                <React.Fragment key={m.id}>
                  <div className="mb-6 flex flex-col items-end">
                    <span className="mb-1 text-xs text-ink3">You · {m.time}</span>
                    <div className="max-w-[520px] whitespace-pre-wrap rounded-2xl rounded-tr-md bg-accentsoft px-4 py-3 text-ink">{m.text}</div>
                  </div>
                  <div className="mb-6 rounded-2xl border border-line bg-panel p-4 shadow-card sm:p-5">
                    <Who time={m.time} />
                    <p className={`m-0 ml-9 mt-1 text-[14.5px] ${m.reply ? '' : 'text-ink3'}`}>{m.reply ?? 'Thinking…'}</p>
                  </div>
                </React.Fragment>
              ))}
              <div ref={endRef} />
            </div>
          </div>
        </div>
        <div className="flex-none pb-[18px]">
          <div className="mx-auto max-w-[760px] pl-12 pr-5 lg:pr-8">
            <div className="rounded-2xl border border-line bg-panel p-3 pl-4 shadow-card focus-within:border-accent">
              <textarea
                aria-label="Message LychD"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send() } }}
                placeholder="What would you like to explore?"
                rows={2}
                className="block h-14 w-full resize-none bg-transparent text-[15px] text-ink outline-none placeholder:text-ink3"
              />
              <div className="mt-2 flex items-center gap-1.5">
                <ChipBtn title="Attach"><Plus className="size-4" strokeWidth={1.6} /></ChipBtn>
                <ChipBtn title="Web"><Globe className="size-4" strokeWidth={1.6} /></ChipBtn>
                <ChipBtn title="Voice"><Mic className="size-4" strokeWidth={1.6} /></ChipBtn>
                <button className="ml-1 inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full bg-accentsoft px-3 text-[13px] font-medium text-accent">Conversation <ChevronDown className="size-3.5" strokeWidth={1.8} /></button>
                <span className="flex-1" />
                <span className="mr-2.5 hidden whitespace-nowrap font-mono text-[12.5px] text-ink3 2xl:inline">bridge_chat · local</span>
                <button
                  title="Send"
                  aria-label="Send"
                  onClick={send}
                  disabled={!draft.trim()}
                  className="grid size-9 flex-none place-items-center rounded-full bg-primary text-onprimary transition-opacity duration-150 hover:opacity-90 disabled:opacity-40"
                >
                  <ArrowUp className="size-4" strokeWidth={1.6} />
                </button>
              </div>
            </div>
            <div className="mt-2 text-[11.5px] text-ink3">Enter to send · Shift + Enter for a new line</div>
          </div>
        </div>
      </div>
    </Shell>
  )
}

function Who({ time }: { time: string }) {
  return (
    <div className="mb-1.5 flex items-center gap-2.5">
      <div className="grid size-[26px] place-items-center rounded-full bg-primary text-onprimary"><Sparkle className="size-3.5 fill-current" strokeWidth={1.4} /></div>
      <b className="font-semibold">LychD</b>
      <time className="text-xs text-ink3">{time}</time>
    </div>
  )
}

function ChipBtn({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <button title={title} aria-label={title} className="grid size-8 place-items-center rounded-full border border-line text-ink2 transition-colors duration-150 hover:bg-hover hover:text-ink">
      {children}
    </button>
  )
}

function TurnStrip() {
  const [hover, setHover] = useState<number | null>(null)
  return (
    <div className="absolute left-[18px] top-1/2 z-[3] hidden h-1/2 w-4 -translate-y-1/2 flex-col items-center sm:flex" onMouseLeave={() => setHover(null)} aria-label="Turn strip">
      <span className="text-[10px] leading-3.5 text-ink3">⌃</span>
      <div className="flex w-2.5 flex-1 flex-col items-center gap-3 overflow-auto rounded-md border border-line bg-sunk py-2.5 [scrollbar-width:none]">
        {Array.from({ length: 14 }, (_, i) => i + 1).map((n) => (
          <div key={n} onMouseEnter={() => setHover(n)} className={`w-1.5 flex-none cursor-pointer rounded-sm ${n === 3 ? 'h-[9px] bg-primary' : 'h-[3px] bg-line2 hover:bg-ink2'}`} />
        ))}
      </div>
      <span className="text-[10px] leading-3.5 text-ink3">⌄</span>
      {hover !== null && (
        <div className="absolute left-7 top-1/3 w-[300px] rounded-xl border border-line bg-raise px-3.5 py-3 shadow-pop">
          <div className="mb-1.5 flex items-center justify-between"><Kicker>Turn {hover}</Kicker><IconBtn title="Bookmark turn"><Bookmark className="size-4" strokeWidth={1.6} /></IconBtn></div>
          <p className="my-0.5 text-[12.5px] text-ink2"><b className="font-semibold text-ink">You</b> · What does Nexus change when I only view the board?</p>
          <p className="my-0.5 text-[12.5px] text-ink2"><b className="font-semibold text-ink">LychD</b> · I need to fetch one public page before I can answer…</p>
          <span className="mt-1.5 inline-block text-xs font-semibold text-ink">Jump to turn ↵</span>
        </div>
      )}
    </div>
  )
}

const FOLDERS: [string, string[][]][] = [
  ['Design', [['Workspace layout', 'Today 14:26'], ['File navigation', 'Today 13:47'], ['Session notes', 'Today 11:32']]],
  ['Development', [['Why did run 41c2e0 fail?', 'Yesterday 17:08'], ['Warm qwen3 on forge-3090', 'Yesterday 10:21']]],
]
const RECENT = [['Broadcast candidate review', 'Mon 09:14'], ['Release notes for 0.4', 'Sun 18:40']]
const ARCHIVED = [['Founding trial retro', 'Nov 02'], ['Discord intake pilot', 'Oct 28']]
const PINNED = 'Observatory hours and public notes'

function SeanceList() {
  const [tab, setTab] = useState('Active')
  const [sel, setSel] = useState(PINNED)
  const [q, setQ] = useState('')
  const match = (t: string) => t.toLowerCase().includes(q.toLowerCase())
  const chat = <MessageSquare className="size-4" strokeWidth={1.6} />
  const row = ([t, s]: string[]) => <ListItem key={t} on={sel === t} onClick={() => setSel(t)} icon={chat} title={t} sub={s} />
  const folders = FOLDERS.map(([n, items]) => [n, items.filter(([t]) => match(t))] as const).filter(([, items]) => items.length)
  const recent = RECENT.filter(([t]) => match(t))
  return (
    <>
      <Segmented options={['Active', 'Archive']} value={tab} onChange={setTab} />
      <Search placeholder="Search séances" value={q} onChange={setQ} />
      {tab === 'Archive' ? (
        <>
          <Kicker className="mx-1.5 mb-1.5 mt-3.5">Archived</Kicker>
          {ARCHIVED.filter(([t]) => match(t)).map(row)}
        </>
      ) : (
        <>
          {match(PINNED) && (
            <>
              <Kicker className="mx-1.5 mb-1.5 mt-3.5">Pinned</Kicker>
              <ListItem on={sel === PINNED} onClick={() => setSel(PINNED)} icon={<Pin className="size-4" strokeWidth={1.6} />} title={PINNED} sub="Today 14:26 · 1 awaiting consent" />
            </>
          )}
          {folders.length > 0 && <Kicker className="mx-1.5 mb-1.5 mt-4">Folders</Kicker>}
          {folders.map(([n, items]) => <FolderGroup key={n} name={n}>{items.map(row)}</FolderGroup>)}
          {recent.length > 0 && <Kicker className="mx-1.5 mb-1.5 mt-4">Recent</Kicker>}
          {recent.map(row)}
        </>
      )}
    </>
  )
}

function FolderGroup({ name, children }: { name: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true)
  return (
    <>
      <button aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex h-[30px] w-full items-center gap-2 rounded-md px-1.5 font-medium text-ink2 hover:bg-hover">
        <ChevronDown className={`size-4 transition-transform duration-150 ${open ? '' : '-rotate-90'}`} strokeWidth={1.6} />
        <Folder className="size-4" strokeWidth={1.6} />
        {name}
      </button>
      {open && <div className="ml-[15px] border-l border-line pl-2.5">{children}</div>}
    </>
  )
}
