<script lang="ts">
  import CaseView from './lib/CaseView.svelte'
  import Sidebar from './lib/Sidebar.svelte'
  import { Review, setReview } from './lib/review.svelte'

  const review = setReview(new Review())

  // every choice is in the address (see Review.search): read it now and on back and forward
  function restore() {
    review.apply(new URLSearchParams(location.search))
    review.open(review.selected)
  }
  review.apply(new URLSearchParams(location.search))
  review.selected ??= decodeURIComponent(location.hash.slice(1)) || null // an older #case link
  review.load().then(() => review.open(review.selected))

  // and write it as they change: at most every 0.4 s, since browsers refuse a flood of history
  // writes (holding an arrow key, playing), and always the latest
  let written = 0
  $effect(() => {
    if (review.search === location.search) return
    const timer = setTimeout(
      () => {
        written = performance.now()
        history.replaceState(history.state, '', review.search || location.pathname)
      },
      Math.max(0, written + 400 - performance.now()),
    )
    return () => clearTimeout(timer)
  })

  function onkeydown(event: KeyboardEvent) {
    const typing = event.target instanceof HTMLElement && event.target.closest('input, textarea, select')
    if (typing || event.metaKey || event.ctrlKey || event.altKey) return
    if (event.key === '/') {
      event.preventDefault()
      document.getElementById('search')?.focus()
    } else if (['ArrowDown', 'ArrowUp', 'j', 'k'].includes(event.key)) {
      // up and down walk the list; left and right are the timeline's
      event.preventDefault()
      const down = event.key === 'ArrowDown' || event.key === 'j'
      const next = review.neighbour(down ? 1 : -1)
      if (next) review.go(next, 'replace')
    }
  }
</script>

<svelte:window onpopstate={restore} {onkeydown} />

<div class="panel">
  <Sidebar />
  <main>
    {#if review.error}
      <p class="error">{review.error}</p>
    {/if}
    {#if review.detail}
      <CaseView detail={review.detail} />
    {:else}
      <p class="empty">
        Pick a case. <kbd>/</kbd> searches, <kbd>↑</kbd> <kbd>↓</kbd> walk the list,
        <kbd>←</kbd> <kbd>→</kbd> the frames, <kbd>0</kbd>–<kbd>3</kbd> give the verdict.
      </p>
    {/if}
  </main>
</div>

<style>
  .panel {
    display: grid;
    grid-template-columns: 320px 1fr;
    height: 100vh;
  }

  main {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }

  .error {
    margin: 0;
    padding: 6px 12px;
    color: var(--not-working);
    background: color-mix(in srgb, var(--not-working) 12%, var(--bg));
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
  }

  .empty {
    margin: auto;
    color: var(--faint);
  }

  kbd {
    padding: 0 4px;
    border: 1px solid var(--line);
    border-radius: 3px;
    font-family: var(--mono);
  }
</style>
