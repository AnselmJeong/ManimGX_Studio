<!--
  @component
  One case: its verdict (the comparison's, or a reviewer's), its renders, its source and the
  comparison with CE.
-->
<script lang="ts">
  import type { CaseDetail, Verdict } from './api'
  import Compare from './Compare.svelte'
  import { getReview, label } from './review.svelte'
  import Source from './Source.svelte'

  let { detail }: { detail: CaseDetail } = $props()

  const review = getReview()

  let copied = $state(false)

  // a review's verdict applies only to the renders it was given for
  const verdict = $derived<Verdict | 'auto'>(detail.reviewed && detail.review?.verdict ? detail.review.verdict : 'auto')
  const judged = $derived(detail.state !== 'stale' && detail.state !== 'unrendered')
  const choices = $derived<{ value: Verdict | 'auto'; text: string; key: string }[]>([
    { value: 'auto', text: `auto (${label(detail.auto)})`, key: '0' },
    { value: 'working', text: 'working', key: '1' },
    { value: 'not_matching', text: 'not matching', key: '2' },
    { value: 'not_working', text: 'not working', key: '3' },
  ])
  let note = $derived(detail.review?.note ?? '')

  function choose(value: Verdict | 'auto') {
    if (judged && value !== verdict) review.setVerdict(value, note)
  }

  const saveNote = () => {
    if (note !== (detail.review?.note ?? '')) review.setVerdict(verdict, note)
  }

  function onkeydown(event: KeyboardEvent) {
    const typing = event.target instanceof HTMLElement && event.target.closest('input, textarea, select')
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return
    const choice = choices.find((c) => c.key === event.key)
    if (choice) {
      event.preventDefault()
      choose(choice.value)
    }
  }

  async function copy() {
    await navigator.clipboard.writeText(detail.name)
    copied = true
    setTimeout(() => (copied = false), 1200)
  }

  const seconds = (value: number | null) => (value === null ? '—' : `${value.toFixed(2)} s`)
</script>

<svelte:window {onkeydown} />

<header>
  <div class="line">
    <h1>{detail.name}</h1>
    <button class="button icon" title="copy the case's name" onclick={copy}>{copied ? '✓' : '⧉'}</button>
    <span class="state {detail.state}">{label(detail.state)}</span>

    <div class="verdicts" role="group" aria-label="verdict">
      {#each choices as choice (choice.value)}
        <button
          class="button verdict {choice.value}"
          class:on={verdict === choice.value}
          disabled={!judged}
          title="{choice.text} (key {choice.key})"
          onclick={() => choose(choice.value)}
        >
          <kbd>{choice.key}</kbd>{choice.text}
        </button>
      {/each}
    </div>

    <span class="actions">
      {#if review.busy}<span class="busy">{review.busy}…</span>{/if}
      <button class="button" disabled={review.busy !== null} onclick={() => review.render('manimgx')}>↻ ManimGX</button>
      <button class="button" disabled={review.busy !== null} onclick={() => review.render('ce')}>↻ ce</button>
      <button class="button" disabled={review.busy !== null} onclick={() => review.render('both')}>↻ both</button>
    </span>
  </div>

  <div class="line facts">
    <span>ManimGX {detail.manimgx.frames.length} frames · {seconds(detail.manimgx.duration)}</span>
    <span>ce {detail.ce.version} {detail.ce.frames.length} frames · {seconds(detail.ce.duration)}</span>
    {#if detail.reasons.length}
      <span class="reasons">differs: {detail.reasons.join(', ')}</span>
    {/if}
    {#each [detail.manimgx, detail.ce] as render, i (i)}
      {#if render.error}<span class="failed">{i === 0 ? 'ManimGX' : 'ce'}: {render.error}</span>{/if}
    {/each}
  </div>

  <div class="line">
    <input
      class="field note"
      placeholder="a note for this case (saved on enter or leaving the field)"
      bind:value={note}
      onchange={saveNote}
    />
    {#if detail.stale_review}
      <span class="stale-review" title="its verdict no longer applies">review was for other renders</span>
    {/if}
  </div>
</header>

<div class="panes" class:wide={!review.showSource}>
  {#if review.showSource}
    <section class="source">
      <div class="bar">
        <button class="button icon" title="hide the source" onclick={() => (review.showSource = false)}>‹</button>
        <span class="label">source</span>
      </div>
      <Source source={detail.source} problems={detail.problems} />
    </section>
  {/if}
  <section class="compare">
    <div class="bar">
      {#if !review.showSource}
        <button class="button icon" title="show the source" onclick={() => (review.showSource = true)}>›</button>
      {/if}
      <span class="label">compare</span>
    </div>
    {#key detail.name}
      <Compare {detail} />
    {/key}
  </section>
</div>

<style>
  header {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
  }

  .line {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
  }

  h1 {
    margin: 0;
    font: 600 15px var(--mono);
  }

  .icon {
    padding: 0 6px;
    line-height: 20px;
  }

  .state {
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--bg);
    background: var(--stale);
  }

  .state.working {
    background: var(--working);
  }

  .state.not_matching {
    background: var(--not-matching);
  }

  .state.not_working {
    background: var(--not-working);
  }

  .verdicts {
    display: flex;
    gap: 4px;
  }

  .verdict {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .verdict kbd {
    padding: 0 4px;
    border: 1px solid var(--line);
    border-radius: 3px;
    color: var(--faint);
    font: 11px var(--mono);
  }

  /* the chosen verdict, in its colour */
  .verdict.on {
    --tone: var(--accent);
    border-color: var(--tone);
    color: var(--tone);
    background: color-mix(in srgb, var(--tone) 14%, var(--raised));
  }

  .verdict.on.working {
    --tone: var(--working);
  }

  .verdict.on.not_matching {
    --tone: var(--not-matching);
  }

  .verdict.on.not_working {
    --tone: var(--not-working);
  }

  .verdict.on kbd {
    border-color: var(--tone);
    color: var(--tone);
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }

  .busy {
    color: var(--accent);
    font-size: 12px;
  }

  .facts {
    flex-wrap: wrap;
    gap: 14px;
    color: var(--dim);
    font-family: var(--mono);
    font-size: 12px;
  }

  .reasons {
    color: var(--not-matching);
  }

  .failed {
    color: var(--not-working);
  }

  .note {
    flex: 1;
  }

  .stale-review {
    color: var(--not-matching);
    font-size: 12px;
  }

  .panes {
    flex: 1;
    display: grid;
    grid-template-columns: minmax(280px, 2fr) 3fr;
    min-height: 0;
  }

  .panes.wide {
    grid-template-columns: 1fr;
  }

  section {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }

  .source {
    border-right: 1px solid var(--line);
  }

  .bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-bottom: 1px solid var(--line);
  }
</style>
