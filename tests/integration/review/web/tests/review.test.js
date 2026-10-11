// The shipped Svelte state module, with controlled HTTP completion order.
import { afterAll, afterEach, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compileModule } from 'svelte/compiler'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const source = join(root, 'src/lib/review.svelte.ts')
const code = new Bun.Transpiler({ loader: 'ts' }).transformSync(readFileSync(source, 'utf8'))
const compiled = compileModule(code, { filename: source, generate: 'client' }).js.code
const directory = mkdtempSync(join(root, 'node_modules/.review-test-'))
const module = join(directory, 'review.mjs')
writeFileSync(
  module,
  compiled.replace(/(['"])\.\/api\1/, JSON.stringify(join(root, 'src/lib/api.ts'))),
)
const { Review } = await import(module)
afterAll(() => rmSync(directory, { recursive: true }))
const fetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = fetch
})

function detail(name, revision = name) {
  return {
    name,
    revision,
    slots: [],
    source: '',
    problems: [],
    reasons: [],
    review: null,
    stale_review: false,
    state: 'working',
    auto: 'working',
    reviewed: false,
    noted: false,
    checks: { source: true, types: true },
    worst: 0,
    manimgx: { frames: [], duration: 0, error: null, version: '' },
    ce: { frames: [], duration: 0, error: null, version: '' },
  }
}

function showing(name) {
  const review = new Review()
  review.selected = name
  review.detail = detail(name)
  return review
}

test('navigation cannot save a verdict for a view that has not arrived', async () => {
  const pending = Promise.withResolvers()
  const requests = []
  globalThis.fetch = (url, options) => {
    requests.push({ url, body: options?.body })
    return url.endsWith('/review')
      ? Promise.resolve(Response.json(detail('next')))
      : pending.promise
  }
  const review = showing('old')
  const opening = review.open('next')
  expect(review.detail).toBeNull()
  await review.setVerdict('working', 'saw old')
  expect(requests).toHaveLength(1)
  pending.resolve(Response.json(detail('next', 'observed facts')))
  await opening
  await review.setVerdict('working', 'saw next')
  expect(requests[1]).toEqual({
    url: '/api/cases/next/review',
    body: JSON.stringify({ revision: 'observed facts', verdict: 'working', note: 'saw next' }),
  })
})

test('returning to a case cannot revive an older request for that same name', async () => {
  const requests = []
  globalThis.fetch = () => {
    const pending = Promise.withResolvers()
    requests.push(pending)
    return pending.promise
  }
  const review = new Review()
  const first = review.open('a')
  const other = review.open('b')
  const latest = review.open('a')
  requests[2].resolve(Response.json(detail('a', 'latest')))
  await latest
  requests[0].resolve(Response.json(detail('a', 'obsolete')))
  requests[1].reject(new Error('obsolete navigation failed'))
  await Promise.all([first, other])
  expect(review.detail.revision).toBe('latest')
  expect(review.error).toBeNull()
})

test('settings refresh cannot replace a case selected while it was loading', async () => {
  const pending = Promise.withResolvers()
  const requested = Promise.withResolvers()
  globalThis.fetch = (url) => {
    if (url === '/api/settings')
      return Promise.resolve(Response.json({ metric: 'max', tolerance: 0, metrics: ['max'] }))
    if (url === '/api/cases') return Promise.resolve(Response.json([]))
    if (url === '/api/cases/first') {
      requested.resolve()
      return pending.promise
    }
    return Promise.resolve(Response.json(detail('next')))
  }
  const review = showing('first')
  const saving = review.saveSettings('max', 0)
  await requested.promise
  await review.open('next')
  pending.resolve(Response.json(detail('first')))
  await saving
  expect(review.selected).toBe('next')
  expect(review.detail.name).toBe('next')
})

test('a completed action belongs to its original view lifetime', async () => {
  const pending = Promise.withResolvers()
  globalThis.fetch = (url) =>
    url.endsWith('/review')
      ? pending.promise
      : Promise.resolve(
          Response.json(detail(url.endsWith('/next') ? 'next' : 'first', 'new visit')),
        )
  const review = showing('first')
  const saving = review.setVerdict('working', 'old visit')
  await review.open('next')
  await review.open('first')
  pending.resolve(Response.json(detail('first', 'old visit')))
  await saving
  expect(review.detail.revision).toBe('new visit')
})
