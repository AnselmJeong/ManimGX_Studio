// Missing evidence must stay visibly distinct from measured equality.
import { afterAll, afterEach, expect, test } from 'bun:test'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compile } from 'svelte/compiler'
import { render } from 'svelte/server'
import { differences } from '../src/lib/differences.ts'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const source = join(root, 'src/lib/Timeline.svelte')
const compiled = compile(readFileSync(source, 'utf8'), { filename: source, generate: 'server' })
const directory = mkdtempSync(join(root, 'node_modules/.timeline-test-'))
const module = join(directory, 'Timeline.mjs')
writeFileSync(module, compiled.js.code)
const { default: Timeline } = await import(module)
afterAll(() => rmSync(directory, { recursive: true }))

for (const errors of [null, {}, { mae: 0 }]) {
  test(`unmeasured timeline slots are not labelled equal: ${JSON.stringify(errors)}`, () => {
    const { body } = render(Timeline, {
      props: {
        slots: [{ time: 0, ce: 0, ce_time: 0, manimgx: 0, errors }],
        at: 0,
        metric: 'max',
        tolerance: 0,
        onselect() {},
      },
    })
    expect(body).toMatch(/<button class="block unmeasured /)
    expect(body).not.toMatch(/<button class="block same /)
  })
}

test('a measured zero remains an equality', () => {
  const { body } = render(Timeline, {
    props: {
      slots: [{ time: 0, ce: 0, ce_time: 0, manimgx: 0, errors: { max: 0 } }],
      at: 0,
      metric: 'max',
      tolerance: 0,
      onselect() {},
    },
  })
  expect(body).toMatch(/<button class="block same /)
})

const image = globalThis.Image
afterEach(() => {
  globalThis.Image = image
})

for (const detached of [false, true]) {
  test(`missing diff images report an error only to a live view: detached=${detached}`, async () => {
    const pending = Promise.withResolvers()
    globalThis.Image = class {
      decode() {
        return pending.promise
      }
    }
    const errors = []
    const dispose = differences('missing.png', 'other.png', (error) => errors.push(error))({})
    if (detached) dispose()
    pending.reject(new Error('reference image unavailable'))
    // Image.decode, load, Promise.all, and its attached catch all settle before this task.
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(errors).toEqual(detached ? [] : ['reference image unavailable'])
  })
}
