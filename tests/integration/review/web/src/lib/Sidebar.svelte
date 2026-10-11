<!--
  @component
  Every case: counts, the comparison's settings, search (names, and code from three letters),
  filters, and the list.
-->
<script lang="ts">
  import Squares from './Squares.svelte'
  import { getReview, label, SORTS, STATE_FILTERS } from './review.svelte'

  const review = getReview()

  /** A plain click opens the case here; a modified one (a new tab, a copied link) follows the
   * link, which holds every choice. */
  function follow(event: MouseEvent, name: string) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
    event.preventDefault()
    review.go(name, 'push')
  }

  // the chosen case stays in sight, from a link too
  let list = $state<HTMLOListElement>()
  $effect(() => {
    void [review.selected, review.visible]
    list?.querySelector('.selected')?.scrollIntoView({ block: 'nearest' })
  })

  let metric = $derived(review.settings?.metric ?? '')
  let tolerance = $derived(review.settings?.tolerance ?? 0)

  function saveSettings() {
    if (review.settings && (metric !== review.settings.metric || tolerance !== review.settings.tolerance)) {
      review.saveSettings(metric, tolerance)
    }
  }
</script>

<aside>
  <header>
    <span class="label">cases</span>
    <span class="counts">
      {#each ['working', 'not_matching', 'not_working'] as const as state (state)}
        <span class="count" title={label(state)}>
          <i class="dot {state}"></i>{review.counts.byState.get(state) ?? 0}
        </span>
      {/each}
      {#if (review.counts.byState.get('stale') ?? 0) + (review.counts.byState.get('unrendered') ?? 0) > 0}
        <span class="count" title="stale or unrendered">
          <i class="dot stale"></i>{(review.counts.byState.get('stale') ?? 0) +
            (review.counts.byState.get('unrendered') ?? 0)}
        </span>
      {/if}
    </span>
  </header>

  {#if review.settings}
    <div class="row settings" title="how CE and ManimGX frames are compared">
      <span class="label">metric</span>
      <select class="field" bind:value={metric} onchange={saveSettings}>
        {#each review.settings.metrics as name (name)}
          <option value={name}>{name}</option>
        {/each}
      </select>
      <span class="label">≤</span>
      <input class="field tolerance" type="number" min="0" max="255" step="1" bind:value={tolerance} onchange={saveSettings} />
    </div>
  {/if}

  <div class="row">
    <input
      id="search"
      class="field search"
      type="search"
      placeholder="search names and code  /"
      autocomplete="off"
      spellcheck="false"
      bind:value={review.query}
    />
  </div>

  <div class="row chips">
    {#each STATE_FILTERS as state (state)}
      <button class="button" class:on={review.stateFilter === state} onclick={() => (review.stateFilter = state)}>
        {state === 'all' ? 'all' : label(state)}
      </button>
    {/each}
  </div>

  <div class="row chips">
    <button class="button" class:on={review.failingSource} onclick={() => (review.failingSource = !review.failingSource)}>
      source ✗ {review.counts.source}
    </button>
    <button class="button" class:on={review.failingTypes} onclick={() => (review.failingTypes = !review.failingTypes)}>
      types ✗ {review.counts.types}
    </button>
    <span class="gap"></span>
    <button class="button" class:on={review.onlyReviewed} onclick={() => (review.onlyReviewed = !review.onlyReviewed)}>
      reviewed
    </button>
    <button class="button" class:on={review.onlyNoted} onclick={() => (review.onlyNoted = !review.onlyNoted)}>
      noted
    </button>
  </div>

  <div class="row chips">
    <span class="label">sort</span>
    {#each SORTS as sort (sort)}
      <button class="button" class:on={review.sort === sort} onclick={() => (review.sort = sort)}>{sort}</button>
    {/each}
    <span class="shown">{review.visible.length} shown</span>
  </div>

  <ol bind:this={list}>
    {#each review.visible as item (item.name)}
      <li>
        <a
          href={review.link(item.name)}
          class:selected={review.selected === item.name}
          onclick={(event) => follow(event, item.name)}
        >
          <span class="name">{item.name}</span>
          {#if review.inSource.has(item.name)}<span class="badge" title="found in the code">code</span>{/if}
          {#if item.reviewed}<span class="mark" title="verdict set by review">●</span>{/if}
          {#if item.noted}<span class="mark" title="has a note">✎</span>{/if}
          <Squares {item} />
          <span class="worst">{item.worst === null ? '' : item.worst.toFixed(1)}</span>
        </a>
      </li>
    {:else}
      <li class="none">no case matches</li>
    {/each}
  </ol>
</aside>

<style>
  aside {
    display: flex;
    flex-direction: column;
    min-height: 0;
    border-right: 1px solid var(--line);
    background: var(--panel);
  }

  header,
  .row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
  }

  header {
    justify-content: space-between;
    padding-top: 10px;
  }

  .counts {
    display: flex;
    gap: 10px;
    font-family: var(--mono);
    font-size: 12px;
  }

  .count {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--stale);
  }

  .dot.working {
    background: var(--working);
  }

  .dot.not_matching {
    background: var(--not-matching);
  }

  .dot.not_working {
    background: var(--not-working);
  }

  .settings select {
    flex: 1;
  }

  .tolerance {
    width: 64px;
  }

  .search {
    flex: 1;
  }

  .chips {
    flex-wrap: wrap;
    gap: 4px;
    padding-top: 2px;
    padding-bottom: 2px;
  }

  .chips .button {
    padding: 1px 7px;
    font-size: 12px;
  }

  .gap {
    flex: 1;
  }

  .shown {
    margin-left: auto;
    color: var(--faint);
    font-size: 12px;
  }

  ol {
    flex: 1;
    min-height: 0;
    margin: 6px 0 0;
    padding: 0;
    overflow-y: auto;
    list-style: none;
    border-top: 1px solid var(--line);
  }

  a {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    color: var(--text);
    text-decoration: none;
    border-left: 2px solid transparent;
  }

  a:hover {
    background: var(--raised);
  }

  a.selected {
    border-left-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 10%, var(--panel));
  }

  .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .badge {
    padding: 0 4px;
    border-radius: 3px;
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    font-size: 10px;
  }

  .mark {
    color: var(--dim);
    font-size: 10px;
  }

  .worst {
    width: 38px;
    color: var(--faint);
    font-family: var(--mono);
    font-size: 11px;
    text-align: right;
  }

  .none {
    padding: 12px;
    color: var(--faint);
  }
</style>
