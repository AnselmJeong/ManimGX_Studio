import { expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { runInNewContext } from "node:vm"

const script = readFileSync(new URL("../../docs/content/javascripts/manimgx.js", import.meta.url), "utf8")
const flush = () => new Promise(resolve => setImmediate(resolve))
const explorer = () => ({ isConnected: true, mxSeen() {} })

// Cached pages retain their initialized explorers. Exercise the shipped script's download
// and navigation boundary without replacing fetch with an already-resolved promise.
function page(initial = []) {
  let roots = initial, boot
  const requests = [], observed = []
  const context = {
    window: {}, URL,
    location: { origin: "https://manimgx.academa.ai" },
    matchMedia: () => ({ matches: false }),
    IntersectionObserver: class {
      disconnect() { observed.length = 0 }
      observe(root) { observed.push(root) }
    },
    MutationObserver: class { disconnect() {} observe() {} },
    fetch(url) {
      return new Promise((resolve, reject) => requests.push({ url: String(url), resolve, reject }))
    },
    document: {
      body: { getAttribute: () => "default" },
      addEventListener() {},
      querySelectorAll: selector => selector === ".mx-rates" ? roots : [],
    },
    document$: { subscribe(callback) { boot = callback; callback() } },
  }
  runInNewContext(script, context)
  return {
    requests, observed,
    navigate(next) {
      for (const root of roots) root.isConnected = false
      for (const root of next) root.isConnected = true
      roots = next
      boot()
    },
    async load() {
      requests.at(-1).resolve({ ok: true, json: async () => ({ linear: [0, 1] }) })
      await flush()
    },
  }
}

test("rate data is lazy, shared across pages, and never attaches departed explorers", async () => {
  const first = explorer(), current = explorer(), later = explorer(), doc = page()
  expect(doc.requests).toHaveLength(0)
  doc.navigate([first])
  doc.navigate([current])
  expect(doc.requests).toHaveLength(1)
  expect(doc.requests[0].url).toBe("https://manimgx.academa.ai/javascripts/rate-functions.json")
  await doc.load()
  expect(doc.observed).toEqual([current])
  doc.navigate([later])
  await flush()
  expect(doc.observed).toEqual([later])
  expect(doc.requests).toHaveLength(1)
})

test.each(["network", "http", "json"])(
  "a %s failure is contained and the next explorer page retries",
  async failure => {
    const first = explorer(), next = explorer(), doc = page([first])
    const request = doc.requests[0]
    if (failure === "network") request.reject(new Error("offline"))
    else request.resolve({
      ok: failure !== "http", status: 503,
      json: async () => {
        if (failure === "json") throw new SyntaxError("invalid JSON")
        return {}
      },
    })
    await flush()
    expect(doc.observed).toHaveLength(0)
    doc.navigate([next])
    expect(doc.requests).toHaveLength(2)
    await doc.load()
    expect(doc.observed).toEqual([next])
  },
)
