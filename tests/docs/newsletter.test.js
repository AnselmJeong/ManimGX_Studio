import { expect, test } from "bun:test"
import { readFileSync } from "node:fs"
import { runInNewContext } from "node:vm"

const script = readFileSync(new URL("../../docs/content/javascripts/manimgx.js", import.meta.url), "utf8")

// Run the shipped script with a deferred HTTP request. No address leaves the test.
function signup() {
  const listeners = new Map(), requests = [], classes = new Set()
  const answer = {
    textContent: "",
    classList: { add: name => classes.add(name), remove: name => classes.delete(name) },
    before: form => { form.attached = true },
  }
  class Form {
    action = "https://academa.ai/api/newsletter"
    elements = { email: { value: "reader@example.com" } }
    button = { disabled: false }
    attached = true
    parentElement = { querySelector: () => answer }
    matches() { return true }
    querySelector() { return this.button }
    remove() { this.attached = false }
  }
  runInNewContext(script, {
    window: {}, URL,
    location: { origin: "https://manimgx.academa.ai" },
    matchMedia: () => ({ matches: false }),
    IntersectionObserver: class {},
    HTMLFormElement: Form,
    HTMLInputElement: class {},
    document: { addEventListener: (name, listener) => listeners.set(name, listener) },
    document$: { subscribe() {} },
    fetch: (url, options) => new Promise((resolve, reject) => {
      requests.push({ url, options, resolve, reject })
    }),
  })
  const form = new Form()
  const pending = listeners.get("submit")({ target: form, preventDefault() {} })
  return { form, answer, classes, requests, pending }
}

test("signup appears before the server responds and survives acceptance", async () => {
  const { form, answer, classes, requests, pending } = signup()
  expect(form.attached).toBe(false)
  expect(answer.textContent).toBe("You are on the list.")
  expect(classes.has("mx-footer__answer--joined")).toBe(true)
  expect(requests).toHaveLength(1)
  const request = requests[0]
  expect(request.url).toBe("https://academa.ai/api/newsletter")
  expect(request.options.method).toBe("POST")
  expect(request.options.credentials).toBe("omit")
  expect(JSON.parse(request.options.body)).toEqual({ email: "reader@example.com" })
  request.resolve({ ok: true, json: async () => ({ success: true }) })
  await pending
  expect(form.attached).toBe(false)
  expect(answer.textContent).toBe("You are on the list.")
})

test.each(["refused", "http-error", "network-error", "invalid-json"])(
  "%s restores the entered address and lets the reader retry",
  async failure => {
    const { form, answer, classes, requests, pending } = signup()
    const request = requests[0]
    if (failure === "network-error") request.reject(new TypeError("Network error"))
    else request.resolve({
      ok: failure !== "http-error",
      json: async () => {
        if (failure === "invalid-json") throw new SyntaxError("Invalid JSON")
        return failure === "refused"
          ? { success: false, error: "Please use another email address." }
          : { success: true }
      },
    })
    await pending
    expect(form.attached).toBe(true)
    expect(form.elements.email.value).toBe("reader@example.com")
    expect(form.button.disabled).toBe(false)
    expect(classes.has("mx-footer__answer--joined")).toBe(false)
    expect(answer.textContent).toBe(failure === "refused"
      ? "Please use another email address."
      : "Something went wrong. Please try again.")
  },
)
