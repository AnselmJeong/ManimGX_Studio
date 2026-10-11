// The docs' scripts, in a scope of their own: a classic script's top-level names are shared
// with every other script of the page, and instant navigation may evaluate this file again,
// which then does nothing (its first evaluation serves every page)
;(() => {
  if (window.mxDocs) return
  window.mxDocs = true

  // A film plays while it is on screen, unless the reader prefers less motion.
  const motion = matchMedia("(prefers-reduced-motion: no-preference)")
  const films = new IntersectionObserver(entries => {
    for (const { target, isIntersecting } of entries) {
      if (isIntersecting && motion.matches) target.play().catch(() => {})
      else target.pause()
    }
  }, { threshold: 0.5 })

  // The README's pictures follow the site's selected palette. Zensical resolves system
  // preference into this same body attribute. Keep the original media in the DOM so a
  // cached page restored by instant navigation still knows which source is light or dark.
  let palette
  function pictures() {
    const scheme = document.body.getAttribute("data-md-color-scheme")
    for (const source of document.querySelectorAll("picture > source[media]")) {
      const original = source.getAttribute("data-mx-color-media") ?? source.media
      const match = /^\(prefers-color-scheme:\s*(light|dark)\)$/.exec(original)
      if (!match) continue
      source.setAttribute("data-mx-color-media", original)
      const selected = scheme === "slate" ? "dark" : scheme === "default" ? "light" : null
      const media = selected === null ? original : selected === match[1] ? "all" : "not all"
      if (source.media !== media) source.media = media
    }
  }

  const pictureCache = new Map()
  function preloadPictures() {
    for (const source of document.querySelectorAll(".mx-benchmark source[srcset], .mx-benchmark-quality source[srcset]")) {
      const url = new URL(source.getAttribute("srcset"), document.baseURI).href
      if (pictureCache.has(url)) continue
      const image = new Image()
      image.decoding = "async"
      image.fetchPriority = "low"
      image.src = url
      pictureCache.set(url, image)
      image.decode().catch(() => pictureCache.delete(url))
    }
  }

  // Most pages need no math renderer. Load it once on the first page with math, with its
  // stylesheet beside the scripts in the persistent body: instant navigation replaces
  // the head and page container, but keeps these assets. A failed download can be retried
  // on the next navigation, while successfully loaded dependencies remain available.
  const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.18.9/dist/"
  const mathAssets = new Map()
  function mathAsset(path) {
    if (!mathAssets.has(path)) {
      const style = path.endsWith(".css")
      const asset = document.createElement(style ? "link" : "script")
      if (style) {
        asset.rel = "stylesheet"
        asset.href = KATEX + path
      } else asset.src = KATEX + path
      mathAssets.set(path, new Promise((resolve, reject) => {
        asset.onload = resolve
        asset.onerror = () => {
          asset.remove()
          mathAssets.delete(path)
          reject(new Error(`Could not load ${path}`))
        }
        document.body.appendChild(asset)
      }))
    }
    return mathAssets.get(path)
  }

  function mathematics() {
    const roots = document.querySelectorAll(".arithmatex")
    if (!roots.length) return
    Promise.all([
      mathAsset("katex.min.css"),
      mathAsset("katex.min.js").then(() => mathAsset("contrib/auto-render.min.js")),
    ]).then(() => {
      for (const math of roots) {
        if (!math.isConnected) continue // the reader navigated away while assets loaded
        renderMathInElement(math, {
          delimiters: [
            { left: "\\(", right: "\\)", display: false },
            { left: "\\[", right: "\\]", display: true },
          ],
        })
      }
    }).catch(() => {
      // Keep the readable source if the CDN is unavailable; a later page can retry.
    })
  }

  // A rate function explorer, <div class="mx-rates" data-rates="smooth linear …">: a button for
  // each function named, its curve with a dot that rides it as time passes, and under it a
  // square that the function moves, beside a faint one that keeps one speed. It plays while it
  // is on screen, unless the reader prefers less motion; its slider, or a drag across it, scrubs
  // the time. The curves are scripts/docs/rates.py's, beside this file.
  const RATES = new URL("rate-functions.json", document.currentScript?.src ?? location.origin + "/javascripts/")
  const REST = 0.6, MOTION = 1.5 // seconds: still at each end, and moving
  const SIDE = 16 // the squares', in pixels
  const ICONS = { Play: "M5 3v10l8-5z", Pause: "M4 3h3v10H4zM9 3h3v10H9z" }
  const explorers = new IntersectionObserver(entries => {
    for (const { target, isIntersecting } of entries) target.mxSeen(isIntersecting)
  })
  let curves // fetched by the first page that has an explorer

  const set = (element, attributes) => {
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value)
  }

  function explore(root, data) {
    const names = root.dataset.rates.split(/\s+/).filter(name => Object.hasOwn(data, name))
    if (!names.length) return
    // the progress shown: 0 to 1, and beyond, as far as a function goes
    const all = names.flatMap(name => data[name])
    const low = Math.min(0, ...all), high = Math.max(1, ...all)
    const square = `width="${SIDE}" height="${SIDE}" rx="3"`
    root.innerHTML = `
      <div class="mx-rates__names" role="group" aria-label="Rate function">
        ${names.map(name => `<button type="button">${name}</button>`).join("")}
      </div>
      <svg class="mx-rates__plot" aria-hidden="true">
        <path class="mx-rates__grid"/>
        <text text-anchor="end" dy="0.35em">1</text>
        <text text-anchor="end" dy="0.35em">0</text>
        <text text-anchor="end" dy="0.35em">progress</text>
        <text dy="0.35em">time</text>
        <line class="mx-rates__now"/>
        <path class="mx-rates__curve"/>
        <circle class="mx-rates__dot" r="5"/>
        <rect class="mx-rates__ghost" ${square}/>
        <rect class="mx-rates__square" ${square}/>
      </svg>
      <div class="mx-rates__controls">
        <button type="button" class="mx-rates__play"><svg viewBox="0 0 16 16"><path/></svg></button>
        <input type="range" min="0" max="100" step="any" aria-label="Time">
      </div>`
    const plot = root.querySelector(".mx-rates__plot")
    const [grid, curve] = plot.querySelectorAll("path"), labels = plot.querySelectorAll("text")
    const [now, dot, ghost, mobject] = plot.querySelectorAll("line, circle, rect")
    const buttons = root.querySelectorAll(".mx-rates__names button")
    const play = root.querySelector(".mx-rates__play"), range = root.querySelector("input")

    let name = names[0], playing = motion.matches, seen = false, frame = 0, last = null
    let t = playing ? 0 : 0.3, clock = REST + t * MOTION // the time shown, and the loop's
    let x = time => time, y = progress => progress // the layout's, in pixels

    // the function's progress at a time, between its samples
    function progress(time) {
      const values = data[name], at = time * (values.length - 1)
      const i = Math.min(Math.floor(at), values.length - 2)
      return values[i] + (values[i + 1] - values[i]) * (at - i)
    }

    // The layout for a width, in pixels: the plot's unit square in the middle, with room on
    // either side for its labels and for the square where it goes beyond the start or the end.
    // Progress is as wide on the track as time is on the plot: the faint square is under the dot
    function layout(width) {
      const unit = Math.min(width - 128, (width - SIDE - 4) / (1 + 2 * Math.max(-low, high - 1)))
      const left = (width - unit) / 2, scale = Math.min(Math.max(0.3 * width, 90), 130)
      x = time => left + time * unit
      y = progress => 8 + (high - progress) * scale
      const track = y(low) + 36, bottom = track + SIDE / 2
      plot.setAttribute("viewBox", `0 0 ${width} ${bottom + 2}`)
      grid.setAttribute("d", `M${x(0)} ${y(1)}H${x(1)}M${x(0)} ${y(0)}H${x(1)}` +
        `M${x(0)} 8V${bottom}M${x(1)} 8V${bottom}M2 ${track}H${width - 2}`)
      const places = [[x(0) - 8, y(1)], [x(0) - 8, y(0)], [x(0) - 8, y(0.5)], [x(1) + 8, y(0)]]
      labels.forEach((label, i) => set(label, { x: places[i][0], y: places[i][1] }))
      set(now, { y1: 8, y2: bottom })
      for (const square of [ghost, mobject]) square.setAttribute("y", track - SIDE / 2)
      root.style.setProperty("--mx-left", `${left}px`)
      root.style.setProperty("--mx-unit", `${unit}px`)
      draw()
    }

    // the function chosen: its button pressed, and its curve
    function draw() {
      for (const button of buttons) button.setAttribute("aria-pressed", button.textContent === name)
      const values = data[name], end = values.length - 1
      curve.setAttribute("d", "M" + values.map((value, i) => `${x(i / end)} ${y(value)}`).join("L"))
      show()
    }

    // the moment t: the dot on the curve, and the squares on the track
    function show() {
      const value = progress(t)
      set(now, { x1: x(t), x2: x(t) })
      set(dot, { cx: x(t), cy: y(value) })
      ghost.setAttribute("x", x(t) - SIDE / 2)
      mobject.setAttribute("x", x(value) - SIDE / 2)
      range.value = 100 * t
    }

    function tick(time) {
      if (!root.isConnected) return // its page is gone
      if (last !== null) clock = (clock + (time - last) / 1000) % (2 * REST + MOTION)
      last = time
      t = Math.min(Math.max((clock - REST) / MOTION, 0), 1)
      show()
      frame = requestAnimationFrame(tick)
    }

    // play while the reader wants it and the page shows it
    function run() {
      cancelAnimationFrame(frame)
      last = null
      if (playing && seen) frame = requestAnimationFrame(tick)
      const action = playing ? "Pause" : "Play"
      play.setAttribute("aria-label", action)
      play.querySelector("path").setAttribute("d", ICONS[action])
    }

    // the reader takes the time in hand
    function scrub(time) {
      playing = false
      t = Math.min(Math.max(time, 0), 1)
      clock = REST + t * MOTION
      run()
      show()
    }

    for (const button of buttons) {
      button.addEventListener("click", () => {
        name = button.textContent
        if (playing) t = clock = 0 // the loop starts again
        draw()
      })
    }
    play.addEventListener("click", () => {
      playing = !playing
      if (playing && t === 1) clock = 0
      run()
    })
    range.addEventListener("input", () => scrub(range.value / 100))
    const drag = event => {
      const from = event.clientX - plot.getBoundingClientRect().left
      scrub((from - x(0)) / (x(1) - x(0)))
    }
    plot.addEventListener("pointerdown", event => {
      plot.setPointerCapture(event.pointerId)
      drag(event)
    })
    plot.addEventListener("pointermove", event => {
      if (plot.hasPointerCapture(event.pointerId)) drag(event)
    })
    root.mxSeen = shown => {
      seen = shown
      run()
    }
    new ResizeObserver(([{ contentRect }]) => {
      if (contentRect.width) layout(contentRect.width)
    }).observe(plot)
    explorers.observe(root)
    run()
  }

  // The footer's newsletter field (overrides/partials/academa.html). Its address goes to
  // academa.ai's door as JSON. A signup is shown immediately; a refusal or network failure
  // restores the same field, with its address intact. Every page has a footer of its own,
  // so the field's form is found when it is submitted
  document.addEventListener("submit", async event => {
    const form = event.target
    if (!(form instanceof HTMLFormElement) || !form.matches(".mx-footer__subscribe")) return
    event.preventDefault()
    const answer = form.parentElement.querySelector(".mx-footer__answer")
    const button = form.querySelector("button")
    button.disabled = true
    form.remove()
    answer.classList.add("mx-footer__answer--joined")
    answer.textContent = "You are on the list."
    let reply = null
    let accepted = false
    try {
      const response = await fetch(form.action, {
        method: "POST",
        credentials: "omit", // the door reads no session
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: form.elements.email.value }),
      })
      reply = await response.json()
      accepted = response.ok && reply?.success === true
    } catch {
      // the door unreachable, or an answer this page may not read
    }
    if (!accepted) {
      answer.classList.remove("mx-footer__answer--joined")
      answer.textContent =
        typeof reply?.error === "string" ? reply.error : "Something went wrong. Please try again."
      button.disabled = false
      answer.before(form)
    }
  })
  // a refusal is about what was typed: typing again clears it
  document.addEventListener("input", event => {
    const field = event.target
    if (field instanceof HTMLInputElement && field.closest(".mx-footer__subscribe")) {
      field.form.parentElement.querySelector(".mx-footer__answer").textContent = ""
    }
  })

  // Every page, including those reached by instant navigation: its films, its math and its
  // rate function explorers and theme-aware pictures
  document$.subscribe(() => {
    palette ??= new MutationObserver(pictures)
    palette.disconnect()
    palette.observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] })
    pictures()
    preloadPictures()
    films.disconnect()
    for (const film of document.querySelectorAll("video.mx-film")) films.observe(film)
    mathematics()
    explorers.disconnect()
    const roots = document.querySelectorAll(".mx-rates")
    if (!roots.length) return
    curves ??= fetch(RATES).then(response => {
      if (!response.ok) throw new Error(`Could not load rate functions: ${response.status}`)
      return response.json()
    }).catch(error => {
      curves = undefined // a later page can retry a failed download
      throw error
    })
    curves.then(data => {
      for (const root of roots) {
        if (root.isConnected) root.mxSeen ? explorers.observe(root) : explore(root, data)
      }
    }).catch(() => {
      // The rate functions' reference remains readable if its interactive data is unavailable.
    })
  })
})()
