export type Section = 'bridge' | 'agents' | 'atlas' | 'loom' | 'nexus' | 'orb' | 'apps'

export type AppEntry = { id: string; name: string; blurb: string; action: string; icon: string; area: string }

export const APPS: AppEntry[] = [
  { id: 'scavenger', name: 'Scavenger', blurb: 'Compare market listings.', action: 'Open market', icon: 'search', area: 'Commerce' },
  { id: 'atelier', name: 'Atelier', blurb: 'Develop visual assets.', action: 'View design', icon: 'pen', area: 'Media' },
  { id: 'canvas', name: 'Canvas', blurb: 'Draw and organise boards.', action: 'Open Canvas', icon: 'board', area: 'Research' },
  { id: 'broadcast', name: 'Broadcast', blurb: 'Edit publication candidates.', action: 'View design', icon: 'radio', area: 'Media' },
  { id: 'riffmaw', name: 'Riffmaw', blurb: 'Develop music and audio.', action: 'View design', icon: 'wave', area: 'Media' },
  { id: 'language', name: 'Language Edition', blurb: 'Align dialogue and captions.', action: 'View design', icon: 'captions', area: 'Language' },
]

export const DEFAULT_PINNED = ['scavenger', 'atelier']
