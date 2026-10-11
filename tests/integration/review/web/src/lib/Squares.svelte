<!--
  @component
  A case's checks at a glance: its source (both references rendered from this exact scene.py),
  its types (strict ty, no escapes, nothing ManimGX leaves Any), and its comparison with CE.
-->
<script lang="ts">
  import type { CaseSummary } from './api'
  import { label } from './review.svelte'

  let { item }: { item: CaseSummary } = $props()

  const checks = $derived([
    {
      name: 'source',
      tone: item.checks.source ? 'pass' : 'fail',
      says: item.checks.source ? 'renders are of this source' : 'renders are stale',
    },
    {
      name: 'types',
      tone: item.checks.types ? 'pass' : 'fail',
      says: item.checks.types ? 'type safe' : 'type problems',
    },
    { name: 'ce', tone: item.state, says: label(item.state) },
  ])
</script>

<span class="squares">
  {#each checks as check (check.name)}
    <span class="square {check.tone}" title="{check.name}: {check.says}"></span>
  {/each}
</span>

<style>
  .squares {
    display: inline-flex;
    gap: 2px;
  }

  .square {
    width: 7px;
    height: 7px;
    border-radius: 1.5px;
    background: var(--stale);
  }

  .pass,
  .working {
    background: var(--working);
  }

  .fail,
  .not_working {
    background: var(--not-working);
  }

  .not_matching {
    background: var(--not-matching);
  }
</style>
