<!--
  @component
  The scene's time, a block per step: green where CE and ManimGX show the same thing (within
  tolerance), red where they differ, and the engine's colour where only one of them has a frame.
-->
<script lang="ts">
  import type { Slot } from './api'

  interface Props {
    slots: Slot[]
    at: number
    metric: string
    tolerance: number
    onselect: (index: number) => void
  }

  let { slots, at, metric, tolerance, onselect }: Props = $props()

  type Kind = 'same' | 'differs' | 'unmeasured' | 'manimgx-only' | 'ce-only'

  const legend: { kind: Kind; text: string }[] = [
    { kind: 'same', text: 'same' },
    { kind: 'differs', text: 'differs' },
    { kind: 'unmeasured', text: 'not compared' },
    { kind: 'manimgx-only', text: 'ManimGX only' },
    { kind: 'ce-only', text: 'ce only' },
  ]

  const kind = (slot: Slot): Kind => {
    if (slot.ce === null) return 'manimgx-only'
    if (slot.manimgx === null) return 'ce-only'
    const error = slot.errors?.[metric]
    if (error === undefined) return 'unmeasured'
    return error <= tolerance ? 'same' : 'differs'
  }

  const kinds = $derived(slots.map(kind))
  const counts = $derived(
    kinds.reduce((found, k) => found.set(k, (found.get(k) ?? 0) + 1), new Map<Kind, number>()),
  )

  function title(slot: Slot, i: number): string {
    const error = slot.errors?.[metric]
    const measured = error === undefined ? '' : ` · ${metric} ${error.toFixed(2)}`
    const held = slot.ce_time !== null && slot.manimgx !== null && slot.ce_time !== slot.time
    const from = held ? ` (ce's from ${slot.ce_time?.toFixed(2)} s)` : ''
    return `${i + 1}/${slots.length} · ${slot.time.toFixed(2)} s${from}${measured}`
  }
</script>

<div class="timeline">
  {#each slots as slot, i (i)}
    <button
      class="block {kinds[i]}"
      class:at={i === at}
      title={title(slot, i)}
      aria-label={title(slot, i)}
      onclick={() => onselect(i)}
    ></button>
  {/each}
</div>

<ul class="legend">
  {#each legend as { kind, text } (kind)}
    <li><i class="block {kind}"></i>{text} {counts.get(kind) ?? 0}</li>
  {/each}
</ul>

<style>
  .timeline {
    display: flex;
    gap: 1px;
    height: 16px;
  }

  .timeline .block {
    flex: 1 1 0;
    min-width: 2px;
    padding: 0;
    border: 0;
    border-radius: 1.5px;
  }

  .block.at {
    outline: 2px solid var(--text);
    outline-offset: 1px;
    z-index: 1;
  }

  .same {
    background: var(--same);
  }

  .differs {
    background: var(--differs);
  }

  .unmeasured {
    background: var(--faint);
  }

  .manimgx-only {
    background: var(--manimgx-only);
  }

  .ce-only {
    background: var(--ce-only);
  }

  .legend {
    display: flex;
    gap: 14px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
    color: var(--dim);
    font-size: 12px;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .legend .block {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
</style>
