<!--
  @component
  CE's frame and ManimGX's at the same scene time — side by side, one over the other, or their
  difference — and the timeline to walk. ←/→ step, space plays, in a loop.
-->
<script lang="ts">
  import { frameUrl, type CaseDetail, type Engine } from './api'
  import { differences } from './differences'
  import { getReview, MODES } from './review.svelte'
  import Timeline from './Timeline.svelte'

  let { detail }: { detail: CaseDetail } = $props()

  const review = getReview()

  const metric = $derived(review.settings?.metric ?? 'local_max')
  const tolerance = $derived(review.settings?.tolerance ?? 0)
  const slot = $derived(detail.slots[review.at])
  const error = $derived(slot?.errors?.[metric])

  function url(engine: Engine, index: number | null | undefined): string | null {
    const hash = index === null || index === undefined ? undefined : detail[engine].frames[index]
    return hash === undefined ? null : frameUrl(detail.name, engine, hash)
  }

  const ce = $derived(url('ce', slot?.ce))
  const manimgx = $derived(url('manimgx', slot?.manimgx))

  function step(by: number) {
    review.playing = false
    review.at = Math.min(Math.max(review.at + by, 0), detail.slots.length - 1)
  }

  // how long the last step stays, in seconds, before the scene plays again: it is the scene's
  // end, with no time of its own to last
  const HOLD = 1

  // playing, in a loop: each step lasts as long as the scene time until the next, the last one
  // HOLD (and it waits while the next case loads: that one plays from its own start)
  $effect(() => {
    if (!review.playing || review.selected !== detail.name) return
    const now = detail.slots[review.at]
    if (!now || detail.slots.length < 2) return // nothing to play
    const next = detail.slots[review.at + 1]
    const lasts = next ? next.time - now.time : HOLD
    const timer = setTimeout(() => (review.at = next ? review.at + 1 : 0), Math.max(16, lasts * 1000))
    return () => clearTimeout(timer)
  })

  function onkeydown(event: KeyboardEvent) {
    if (event.target instanceof HTMLElement && event.target.closest('input, textarea, select')) return
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault()
      step(event.key === 'ArrowLeft' ? -1 : 1)
    } else if (event.key === ' ') {
      event.preventDefault()
      play()
    }
  }

  // played from its last step, the scene starts over at once; paused there, it stays
  function play() {
    if (!review.playing && review.at >= detail.slots.length - 1) review.at = 0
    review.playing = !review.playing
  }
</script>

<svelte:window {onkeydown} />

<div class="compare">
  <div class="toolbar">
    {#each MODES as choice (choice)}
      <button class="button" class:on={review.mode === choice} onclick={() => (review.mode = choice)}>{choice}</button>
    {/each}
    <span class="readout">
      {#if slot}
        {slot.time.toFixed(2)} s
        {#if slot.ce_time !== null && slot.manimgx !== null && slot.ce_time !== slot.time}
          (ce's frame is from {slot.ce_time.toFixed(2)} s)
        {/if}
        · {review.at + 1}/{detail.slots.length}
        {#if error !== undefined}
          · <span class:exceeds={error > tolerance}>{metric} {error.toFixed(2)}</span>
        {/if}
      {/if}
    </span>
  </div>

  {#snippet frame(engine: Engine, src: string | null)}
    <figure>
      <figcaption>{engine === 'ce' ? 'manim ce' : 'ManimGX'}</figcaption>
      {#if src}
        <img {src} alt="{engine === 'manimgx' ? 'ManimGX' : engine} at {slot?.time.toFixed(2)} s" />
      {:else}
        <div class="missing">no {engine === 'manimgx' ? 'ManimGX' : engine} frame at this time</div>
      {/if}
    </figure>
  {/snippet}

  <div class="view">
    {#if detail.slots.length === 0}
      <p class="missing">nothing rendered</p>
    {:else if review.mode === 'parallel'}
      <div class="parallel">
        {@render frame('ce', ce)}
        {@render frame('manimgx', manimgx)}
      </div>
    {:else if review.mode === 'superimposed'}
      <figure>
        <figcaption>
          <span>manim ce</span>
          <input type="range" min="0" max="1" step="0.01" bind:value={review.mix} aria-label="blend" />
          <span>ManimGX</span>
        </figcaption>
        <div class="stack">
          {#if ce}<img src={ce} alt="ce" />{/if}
          {#if manimgx}<img class="over" src={manimgx} alt="ManimGX" style:opacity={ce ? review.mix : 1} />{/if}
        </div>
      </figure>
    {:else if ce && manimgx}
      <figure>
        <figcaption>where they differ: black, then red → yellow → white as the difference grows</figcaption>
        {#key `${ce} ${manimgx}`}
          <canvas {@attach differences(ce, manimgx, (message) => {
            review.error = `Cannot compare frames: ${message}`
          })}></canvas>
        {/key}
      </figure>
    {:else}
      <p class="missing">only one engine shows this time</p>
    {/if}
  </div>

  <div class="transport">
    <button class="button" onclick={() => step(-1)} title="previous (←)">◀</button>
    <button class="button" title="play (space)" onclick={play}>{review.playing ? '❚❚' : '▶'}</button>
    <button class="button" onclick={() => step(1)} title="next (→)">▶︎|</button>
    <div class="line">
      <Timeline
        slots={detail.slots}
        at={review.at}
        {metric}
        {tolerance}
        onselect={(i) => ((review.playing = false), (review.at = i))}
      />
    </div>
  </div>
</div>

<style>
  .compare {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
  }

  .readout {
    margin-left: auto;
    color: var(--dim);
    font-family: var(--mono);
    font-size: 12px;
  }

  .exceeds {
    color: var(--differs);
  }

  .view {
    flex: 1;
    min-height: 0;
    overflow: auto;
    padding: 4px 12px;
  }

  .parallel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }

  figure {
    margin: 0;
  }

  figcaption {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    color: var(--dim);
    font-size: 12px;
  }

  figcaption input {
    width: 140px;
  }

  img,
  canvas {
    display: block;
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
    border: 1px solid var(--line);
    background: #000;
  }

  .stack {
    position: relative;
  }

  .stack .over {
    position: absolute;
    inset: 0;
  }

  .missing {
    display: grid;
    place-items: center;
    aspect-ratio: 16 / 9;
    margin: 0;
    border: 1px dashed var(--line);
    color: var(--faint);
  }

  .transport {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    padding: 10px 12px 12px;
    border-top: 1px solid var(--line);
  }

  .transport .button {
    min-width: 32px;
  }

  .line {
    flex: 1;
    min-width: 0;
    padding-top: 3px;
  }
</style>
