import { expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { runInNewContext } from "node:vm"

const script = readFileSync(new URL("../../docs/content/javascripts/manimgx.js", import.meta.url), "utf8")
const config = readFileSync(new URL("../../docs/zensical.toml", import.meta.url), "utf8")
const CDN = "https://cdn.jsdelivr.net/npm/katex@0.18.9/dist/"
const flush = () => new Promise(resolve => setImmediate(resolve))
const math = () => ({ isConnected: true })

// Run the shipped script with controlled asset downloads and Zensical navigation. The
// body persists, but each navigation discards the old page's nodes and head additions.
function page(initial = []) {
  let roots = initial, boot
  const assets = [], rendered = [], head = []
  const body = {
    getAttribute: () => "default",
    appendChild(asset) { asset.parent = body; assets.push(asset) },
  }
  const context = {
    window: {}, URL,
    location: { origin: "https://manimgx.academa.ai" },
    matchMedia: () => ({ matches: false }),
    IntersectionObserver: class { disconnect() {} observe() {} },
    MutationObserver: class { disconnect() {} observe() {} },
    document: {
      body,
      head: { appendChild: asset => head.push(asset) },
      addEventListener() {},
      querySelectorAll: selector => selector === ".arithmatex" ? roots : [],
      createElement: tag => ({ tag, remove() { this.removed = true } }),
    },
    document$: { subscribe(callback) { boot = callback; callback() } },
  }
  runInNewContext(script, context)
  return {
    assets, rendered, head, body,
    navigate(next) {
      for (const root of roots) root.isConnected = false
      for (const root of next) root.isConnected = true
      roots = next
      head.length = 0
      boot()
    },
    async load(path) {
      const asset = assets.findLast(asset => (asset.src ?? asset.href) === CDN + path)
      expect(asset).toBeDefined()
      if (path === "contrib/auto-render.min.js") {
        context.renderMathInElement = (root, options) => rendered.push({ root, options })
      }
      asset.onload()
      await flush()
    },
    async fail(path) {
      const asset = assets.findLast(asset => (asset.src ?? asset.href) === CDN + path)
      asset.onerror()
      await flush()
      return asset
    },
    reloadScript() { runInNewContext(script, context) },
  }
}

test("pages without math request no KaTeX, including through global site configuration", () => {
  const doc = page()
  doc.navigate([])
  doc.reloadScript()
  expect(doc.assets).toHaveLength(0)
  expect(doc.rendered).toHaveLength(0)
  expect(config).not.toMatch(/https:\/\/[^"\s]*katex/)
})

test("a first math page waits for the stylesheet and loads the renderer after KaTeX", async () => {
  const root = math(), doc = page([root])
  expect(doc.assets.map(asset => asset.href ?? asset.src)).toEqual([
    CDN + "katex.min.css", CDN + "katex.min.js",
  ])
  expect(doc.assets[0].rel).toBe("stylesheet")
  expect(doc.rendered).toHaveLength(0)
  await doc.load("katex.min.js")
  expect(doc.assets[2].src).toBe(CDN + "contrib/auto-render.min.js")
  await doc.load("contrib/auto-render.min.js")
  expect(doc.rendered).toHaveLength(0)
  await doc.load("katex.min.css")
  expect(doc.rendered).toEqual([{
    root,
    options: { delimiters: [
      { left: "\\(", right: "\\)", display: false },
      { left: "\\[", right: "\\]", display: true },
    ] },
  }])
})

test("instant navigation shares downloads, skips departed math, and styles later pages", async () => {
  const departed = math(), current = math(), later = math(), doc = page()
  doc.navigate([departed])
  doc.navigate([current])
  expect(doc.assets).toHaveLength(2)
  await doc.load("katex.min.css")
  await doc.load("katex.min.js")
  await doc.load("contrib/auto-render.min.js")
  expect(doc.rendered.map(call => call.root)).toEqual([current])
  doc.navigate([])
  doc.navigate([later])
  doc.reloadScript()
  await flush()
  expect(doc.rendered.map(call => call.root)).toEqual([current, later])
  expect(doc.assets).toHaveLength(3)
  expect(doc.assets.every(asset => asset.parent === doc.body && !asset.removed)).toBe(true)
  expect(doc.head).toHaveLength(0)
})

test.each(["katex.min.css", "katex.min.js", "contrib/auto-render.min.js"])(
  "a failed %s download leaves source readable and retries on the next math page",
  async path => {
    const first = math(), next = math(), doc = page([first])
    if (path !== "katex.min.css") await doc.load("katex.min.css")
    if (path !== "katex.min.js") {
      await doc.load("katex.min.js")
      if (path !== "contrib/auto-render.min.js") await doc.load("contrib/auto-render.min.js")
    }
    const failed = await doc.fail(path)
    expect(failed.removed).toBe(true)
    expect(doc.rendered).toHaveLength(0)
    doc.navigate([next])
    await flush()
    await doc.load(path)
    if (path === "katex.min.js") await doc.load("contrib/auto-render.min.js")
    expect(doc.rendered.map(call => call.root)).toEqual([next])
    expect(doc.assets).toHaveLength(4)
  },
)
