// The review server's API (tests/integration/review/app.py), typed as it answers.

export type Verdict = 'working' | 'not_matching' | 'not_working'
/** Where a case stands: a verdict, or no current renders to judge. */
export type State = Verdict | 'stale' | 'unrendered'
export type Engine = 'manimgx' | 'ce'

export interface Settings {
  metric: string
  tolerance: number
  metrics: string[]
}

export interface Checks {
  /** Both references were rendered from this exact scene.py. */
  source: boolean
  /** Strict ty, no escapes, no Any/Unknown from ManimGX. */
  types: boolean
}

export interface CaseSummary {
  name: string
  /** What counts: a current review's verdict, else the comparison's. */
  state: State
  /** What the comparison alone says. */
  auto: State
  reviewed: boolean
  noted: boolean
  checks: Checks
  /** The largest error of any same-time pair, in the current metric. */
  worst: number | null
}

export interface Render {
  /** The engine's version; for ManimGX, empty. */
  version: string
  /** Each frame's hash, in order (a held frame repeats its hash). */
  frames: string[]
  duration: number | null
  error: string | null
}

/** One step of the timeline: a scene time, and the frame each engine has on screen then. */
export interface Slot {
  time: number
  ce: number | null
  /** The scene time CE's frame shows: up to a frame earlier, when CE's frames fall off
   * ManimGX's (CE rounds each play to whole frames). */
  ce_time: number | null
  manimgx: number | null
  /** Per metric, when both engines show this time. */
  errors: Record<string, number> | null
}

export interface Review {
  /** null: a note alone, and the comparison's verdict stands. */
  verdict: Verdict | null
  note: string
  at: string
}

export interface CaseDetail extends CaseSummary {
  /** The exact facts shown; a save fails if they changed while being reviewed. */
  revision: string | null
  source: string
  /** The type report's findings, one per line. */
  problems: string[]
  manimgx: Render
  ce: Render
  slots: Slot[]
  /** Why the comparison differs under the current settings. */
  reasons: string[]
  review: Review | null
  /** A review exists, but for other renders than these. */
  stale_review: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'content-type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const body = await response.text()
    throw new Error(`${response.status} ${path}: ${body}`)
  }
  return (await response.json()) as T
}

export const api = {
  cases: () => request<CaseSummary[]>('/api/cases'),
  sources: () => request<Record<string, string>>('/api/sources'),
  detail: (name: string) => request<CaseDetail>(`/api/cases/${encodeURIComponent(name)}`),
  settings: () => request<Settings>('/api/settings'),
  saveSettings: (metric: string, tolerance: number) =>
    request<Settings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify({ metric, tolerance }),
    }),
  review: (name: string, revision: string, verdict: Verdict | 'auto', note: string) =>
    request<CaseDetail>(`/api/cases/${encodeURIComponent(name)}/review`, {
      method: 'PUT',
      body: JSON.stringify({ revision, verdict, note }),
    }),
  render: (name: string, engine: Engine | 'both') =>
    request<CaseDetail>(`/api/cases/${encodeURIComponent(name)}/render`, {
      method: 'POST',
      body: JSON.stringify({ engine }),
    }),
}

export function frameUrl(name: string, engine: Engine, hash: string): string {
  return `/api/cases/${encodeURIComponent(name)}/frames/${engine}/${hash}.png`
}
