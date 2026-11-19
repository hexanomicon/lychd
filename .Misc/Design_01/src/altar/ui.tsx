import React from 'react'

export type Tone = 'ok' | 'warn' | 'bad' | 'neutral'

const pillTone: Record<Tone, string> = {
  ok: 'bg-oksoft text-ok border-transparent',
  warn: 'bg-warnsoft text-warn border-transparent',
  bad: 'bg-badsoft text-bad border-transparent',
  neutral: 'bg-sunk text-ink2 border-line',
}

/** Status is always icon + word: the dot carries the shape, the word the meaning. */
export function Pill({ tone = 'neutral', plain, children }: { tone?: Tone; plain?: boolean; children: React.ReactNode }) {
  return (
    <span className={`inline-flex h-[22px] items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 text-[11.5px] font-medium ${pillTone[tone]}`}>
      {!plain && <span className="size-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}

export function Dot({ tone = 'ok' }: { tone?: 'ok' | 'warn' | 'bad' | 'idle' }) {
  const c = { ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad', idle: 'bg-ink3' }[tone]
  return <span className={`inline-block size-[7px] flex-none rounded-full ${c}`} />
}

export function Btn({
  primary,
  sm,
  children,
  onClick,
}: {
  primary?: boolean
  sm?: boolean
  children: React.ReactNode
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border font-semibold shadow-card transition-[background-color,opacity] duration-150 ${
        sm ? 'h-8 px-3.5 text-[12.5px]' : 'h-9 px-4'
      } ${primary ? 'border-primary bg-primary text-onprimary hover:opacity-90' : 'border-line bg-panel hover:bg-hover'}`}
    >
      {children}
    </button>
  )
}

export function IconBtn({ title, onClick, children }: { title: string; onClick?: () => void; children: React.ReactNode }) {
  return (
    <button
      title={title}
      aria-label={title}
      onClick={onClick}
      className="grid size-7 flex-none place-items-center rounded-[7px] text-ink2 transition-colors duration-150 hover:bg-hover hover:text-ink"
    >
      {children}
    </button>
  )
}

export function Kicker({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`text-[12px] font-medium text-ink3 ${className}`}>{children}</div>
}

export function Mono({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <span className={`font-mono text-[12.5px] ${className}`}>{children}</span>
}

export function Search({ placeholder, value, onChange }: { placeholder: string; value?: string; onChange?: (v: string) => void }) {
  return (
    <label className="my-2.5 flex h-10 items-center gap-2 rounded-xl border border-line2 bg-sunk px-3 text-ink3 focus-within:border-accent">
      <svg viewBox="0 0 24 24" className="size-4 flex-none fill-none stroke-current" strokeWidth="1.6" strokeLinecap="round">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input
        value={value}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        placeholder={placeholder}
        className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-ink3"
      />
    </label>
  )
}

export function Segmented({ options, value, onChange }: { options: string[]; value: string; onChange?: (v: string) => void }) {
  return (
    <div className="grid auto-cols-fr grid-flow-col rounded-xl border border-line bg-sunk p-1">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange?.(o)}
          className={`h-7 whitespace-nowrap rounded-lg px-1.5 text-xs transition-colors duration-150 ${
            o === value ? 'bg-raise font-semibold text-ink shadow-card ring-1 ring-line' : 'text-ink2 hover:text-ink'
          }`}
        >
          {o}
        </button>
      ))}
    </div>
  )
}

/** Context-panel list row. */
export function ListItem({
  on,
  icon,
  title,
  sub,
  mono,
  right,
  onClick,
}: {
  on?: boolean
  icon?: React.ReactNode
  title: string
  sub?: string
  mono?: boolean
  right?: string
  onClick?: () => void
}) {
  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-current={on ? 'true' : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } } : undefined}
      className={`flex cursor-pointer items-start gap-2.5 rounded-xl px-3 py-2 transition-colors duration-150 ${on ? 'bg-sel' : 'hover:bg-hover'}`}
    >
      {icon && <span className={`mt-0.5 ${on ? 'text-accent' : 'text-ink2'}`}>{icon}</span>}
      <div className="min-w-0 flex-1">
        <div className={`truncate font-medium ${mono ? 'font-mono text-[12.5px]' : ''}`}>{title}</div>
        {sub && <div className={`text-xs text-ink3 ${mono ? 'font-mono' : ''}`}>{sub}</div>}
      </div>
      {right && <span className="font-mono text-xs text-ink3">{right}</span>}
    </div>
  )
}

export function PageWrap({ title, lead, children }: { title: string; lead: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="min-h-0 flex-1 overflow-auto px-5 py-7 sm:px-8">
      <h1 className="m-0 mb-1 text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="m-0 mb-6 text-ink2">{lead}</p>
      {children}
    </div>
  )
}

export function Table({ head, children }: { head: string[]; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-panel shadow-card">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr>
            {head.map((h) => (
              <th key={h} className="whitespace-nowrap border-b border-line bg-sidebg px-4 py-2.5 text-[11.5px] font-semibold uppercase tracking-wide text-ink3">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="[&_tr:last-child_td]:border-b-0 [&_tr:hover_td]:bg-hover [&_td]:border-b [&_td]:border-line [&_td]:px-4 [&_td]:py-3 [&_td]:align-middle">
          {children}
        </tbody>
      </table>
    </div>
  )
}

export function SectionHead({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-3 mt-2 flex items-center justify-between gap-3">
      <h2 className="m-0 text-[15px] font-semibold">{title}</h2>
      {children}
    </div>
  )
}

export function Tile({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-panel p-4 shadow-card ${className}`}>{children}</div>
}

export function Kv({ rows, labelWidth = 120 }: { rows: [string, string][]; labelWidth?: number }) {
  return (
    <dl className="m-0 grid gap-x-3 gap-y-1.5 text-[13px]" style={{ gridTemplateColumns: `${labelWidth}px minmax(0,1fr)` }}>
      {rows.map(([k, v]) => (
        <React.Fragment key={k}>
          <dt className="text-ink2">{k}</dt>
          <dd className="m-0 break-all font-mono text-[12.5px]">{v}</dd>
        </React.Fragment>
      ))}
    </dl>
  )
}

export function Spinner({ size = 14 }: { size?: number }) {
  return (
    <span
      className="spin inline-block flex-none rounded-full border-[1.8px] border-line2 border-t-primary"
      style={{ width: size, height: size }}
    />
  )
}
