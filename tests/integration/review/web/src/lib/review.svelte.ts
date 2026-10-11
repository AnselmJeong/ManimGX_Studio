// The panel's state: the corpus, the case being reviewed, and every choice a reviewer makes
// (the sidebar's filters, how the case is shown). One instance, shared through context. The
// choices are the page's address (`search`, `apply`): a reload keeps them, a link shares them.

import { createContext } from 'svelte'
import {
  api,
  type CaseDetail,
  type CaseSummary,
  type Engine,
  type Settings,
  type State,
  type Verdict,
} from './api'

export type StateFilter = 'all' | State
export type Sort = 'name' | 'error'
/** How the compare pane shows the two frames. */
export type Mode = 'parallel' | 'superimposed' | 'diff'

export const STATE_FILTERS: readonly StateFilter[] = ['all', 'working', 'not_matching', 'not_working']
export const SORTS: readonly Sort[] = ['name', 'error']
export const MODES: readonly Mode[] = ['parallel', 'superimposed', 'diff']

export const STATES: readonly State[] = [
  'working',
  'not_matching',
  'not_working',
  'stale',
  'unrendered',
]

/** How a state reads. */
export function label(state: State): string {
  return state.replace('_', ' ')
}

function summary(detail: CaseDetail): CaseSummary {
  const { name, state, auto, reviewed, noted, checks, worst } = detail
  return { name, state, auto, reviewed, noted, checks, worst }
}

export class Review {
  #view = 0
  cases = $state.raw<CaseSummary[]>([])
  sources = $state.raw<Record<string, string>>({})
  settings = $state.raw<Settings | null>(null)
  detail = $state.raw<CaseDetail | null>(null)
  selected = $state<string | null>(null)
  /** What is running, if anything ("rendering ce", …). */
  busy = $state<string | null>(null)
  error = $state<string | null>(null)

  query = $state('')
  stateFilter = $state<StateFilter>('all')
  failingSource = $state(false)
  failingTypes = $state(false)
  onlyReviewed = $state(false)
  onlyNoted = $state(false)
  sort = $state<Sort>('name')

  mode = $state<Mode>('parallel')
  /** The superimposed frames' blend: 0 shows CE, 1 ManimGX. */
  mix = $state(0.5)
  /** The timeline step shown, from 0. */
  at = $state(0)
  /** Whether the timeline plays, in a loop: a reload or a link plays on from its step. */
  playing = $state(false)
  showSource = $state(true)

  /** Every choice, as the page's query: only what differs from a fresh panel, whose address
   * stays bare. */
  search = $derived.by(() => this.#search(this.selected, this.at))

  /** Lower-cased sources, for search. */
  #haystacks = $derived(
    new Map(Object.entries(this.sources).map(([name, source]) => [name, source.toLowerCase()])),
  )

  /** Every term of the query must be in the name — or, from three letters, in the source. */
  #matches = $derived.by(() => {
    const terms = this.query.toLowerCase().split(/\s+/).filter(Boolean)
    const found = new Map<string, 'name' | 'source'>()
    for (const c of this.cases) {
      const name = c.name.toLowerCase()
      let where: 'name' | 'source' | null = 'name'
      for (const term of terms) {
        if (name.includes(term)) continue
        if (term.length >= 3 && this.#haystacks.get(c.name)?.includes(term)) where = 'source'
        else {
          where = null
          break
        }
      }
      if (where) found.set(c.name, where)
    }
    return found
  })

  visible = $derived.by(() => {
    const shown = this.cases.filter(
      (c) =>
        this.#matches.has(c.name) &&
        (this.stateFilter === 'all' || c.state === this.stateFilter) &&
        (!this.failingSource || !c.checks.source) &&
        (!this.failingTypes || !c.checks.types) &&
        (!this.onlyReviewed || c.reviewed) &&
        (!this.onlyNoted || c.noted),
    )
    if (this.sort === 'error') {
      shown.sort((a, b) => (b.worst ?? -1) - (a.worst ?? -1))
    }
    return shown
  })

  /** Cases found only in their source, not their name. */
  inSource = $derived(
    new Set([...this.#matches].filter(([, where]) => where === 'source').map(([name]) => name)),
  )

  counts = $derived.by(() => {
    const byState = new Map<State, number>(STATES.map((s) => [s, 0]))
    let source = 0
    let types = 0
    for (const c of this.cases) {
      byState.set(c.state, (byState.get(c.state) ?? 0) + 1)
      if (!c.checks.source) source += 1
      if (!c.checks.types) types += 1
    }
    return { byState, source, types }
  })

  #search(name: string | null, at: number): string {
    const params = new URLSearchParams()
    const listed = (...items: (string | false)[]) => items.filter(Boolean).join(',')
    if (name !== null) params.set('case', name)
    if (at > 0) params.set('step', String(at + 1)) // as the readout counts
    if (this.playing) params.set('play', '1')
    if (this.mode !== 'parallel') params.set('compare', this.mode)
    if (this.mix !== 0.5) params.set('mix', String(this.mix))
    if (!this.showSource) params.set('source', 'hidden')
    if (this.query) params.set('q', this.query)
    if (this.stateFilter !== 'all') params.set('state', this.stateFilter)
    const fails = listed(this.failingSource && 'source', this.failingTypes && 'types')
    if (fails) params.set('fails', fails)
    const only = listed(this.onlyReviewed && 'reviewed', this.onlyNoted && 'noted')
    if (only) params.set('only', only)
    if (this.sort !== 'name') params.set('sort', this.sort)
    const query = params.toString().replaceAll('%2C', ',') // commas need no escaping
    return query ? `?${query}` : ''
  }

  /** A case's address, from its first step, with every other choice as it is. */
  link(name: string): string {
    return this.#search(name, 0)
  }

  /** Take every choice from a query; what it leaves out or gets wrong is a fresh panel's. */
  apply(params: URLSearchParams): void {
    const pick = <T extends string>(key: string, from: readonly T[], fallback: T): T =>
      from.find((value) => value === params.get(key)) ?? fallback
    const listed = (key: string) => new Set(params.get(key)?.split(','))
    this.selected = params.get('case') || null
    const step = Number(params.get('step') ?? 1)
    this.at = Number.isInteger(step) && step > 0 ? step - 1 : 0
    this.playing = params.get('play') === '1'
    this.mode = pick('compare', MODES, 'parallel')
    const mix = Number.parseFloat(params.get('mix') ?? '')
    this.mix = mix >= 0 && mix <= 1 ? mix : 0.5
    this.showSource = params.get('source') !== 'hidden'
    this.query = params.get('q') ?? ''
    this.stateFilter = pick('state', STATE_FILTERS, 'all')
    const fails = listed('fails')
    this.failingSource = fails.has('source')
    this.failingTypes = fails.has('types')
    const only = listed('only')
    this.onlyReviewed = only.has('reviewed')
    this.onlyNoted = only.has('noted')
    this.sort = pick('sort', SORTS, 'name')
  }

  async load(): Promise<void> {
    await this.#attempt(async () => {
      ;[this.cases, this.settings] = await Promise.all([api.cases(), api.settings()])
      this.sources = await api.sources()
    })
  }

  /** Show a case at the step chosen (the address's, on a reload or back and forward). */
  async open(name: string | null, refresh = false): Promise<void> {
    const view = ++this.#view
    this.selected = name
    if (name === null) {
      this.detail = null
      return
    }
    if (!refresh && name === this.detail?.name) {
      this.#show(this.detail) // only the step may have moved
      return
    }
    this.detail = null
    await this.#attempt(async () => {
      const detail = await api.detail(name)
      if (this.#view === view) this.#show(detail)
    }, view)
  }

  /** Go to a case, from its first step: as a new history entry (`push`: back returns to the
   * panel as it was), or in place of the current one. */
  go(name: string, how: 'push' | 'replace'): void {
    if (name === this.selected) return
    if (how === 'push') {
      history.replaceState(history.state, '', this.search || location.pathname)
      history.pushState(null, '', this.link(name))
    }
    this.at = 0
    void this.open(name)
  }

  /** The next or previous case in the list. */
  neighbour(offset: number): string | null {
    const list = this.visible
    if (list.length === 0) return null
    const at = list.findIndex((c) => c.name === this.selected)
    const next = at === -1 ? 0 : Math.min(Math.max(at + offset, 0), list.length - 1)
    return list[next]?.name ?? null
  }

  async setVerdict(verdict: Verdict | 'auto', note: string): Promise<void> {
    const detail = this.detail
    if (!detail || detail.name !== this.selected || detail.revision === null) return
    const { name, revision } = detail
    const view = this.#view
    await this.#attempt(
      async () => this.#update(await api.review(name, revision, verdict, note), view),
      view,
    )
  }

  async render(engine: Engine | 'both'): Promise<void> {
    const name = this.selected
    if (name === null) return
    const view = this.#view
    this.busy = `rendering ${engine === 'both' ? 'both engines' : engine}`
    try {
      await this.#attempt(async () => this.#update(await api.render(name, engine), view), view)
    } finally {
      this.busy = null
    }
  }

  async saveSettings(metric: string, tolerance: number): Promise<void> {
    await this.#attempt(async () => {
      this.settings = await api.saveSettings(metric, tolerance)
      this.cases = await api.cases() // every verdict may have moved
      if (this.selected !== null) await this.open(this.selected, true)
    })
  }

  #show(detail: CaseDetail): void {
    this.at = Math.max(Math.min(this.at, detail.slots.length - 1), 0)
    this.detail = detail
  }

  #update(detail: CaseDetail, view: number): void {
    if (this.#view === view && this.selected === detail.name) this.#show(detail)
    this.cases = this.cases.map((c) => (c.name === detail.name ? summary(detail) : c))
  }

  async #attempt(work: () => Promise<void>, view = this.#view): Promise<void> {
    this.error = null
    try {
      await work()
    } catch (error) {
      if (this.#view === view) this.error = error instanceof Error ? error.message : String(error)
    }
  }
}

export const [getReview, setReview] = createContext<Review>()
