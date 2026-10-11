<!--
  @component
  The scene's source — the one file both engines run — with the lines the type report flags.
-->
<script lang="ts">
  let { source, problems }: { source: string; problems: string[] } = $props()

  const lines = $derived(source.replace(/\n$/, '').split('\n'))
  const flagged = $derived(new Set(problems.map((p) => /line (\d+):/.exec(p)?.[1]).filter(Boolean).map(Number)))
</script>

<div class="source">
  <pre>{#each lines as text, i (i)}<span class="line" class:flag={flagged.has(i + 1)}>{text}</span>{/each}</pre>
  {#if problems.length}
    <ul>
      {#each problems as problem, i (i)}
        <li class:heading={!problem.startsWith(' ')}>{problem.trim()}</li>
      {/each}
    </ul>
  {:else}
    <p class="clean">type safe: strict ty, no escapes, nothing ManimGX leaves Any</p>
  {/if}
</div>

<style>
  .source {
    flex: 1;
    min-height: 0;
    overflow: auto;
  }

  pre {
    margin: 0;
    padding: 8px 0;
    font: 12px/1.55 var(--mono);
    counter-reset: line;
    tab-size: 4;
  }

  .line {
    display: block;
    padding-right: 12px;
    white-space: pre;
  }

  .line::before {
    counter-increment: line;
    content: counter(line);
    display: inline-block;
    width: 3.2em;
    margin-right: 1em;
    padding-right: 0.6em;
    color: var(--faint);
    text-align: right;
    user-select: none;
  }

  .line.flag {
    background: color-mix(in srgb, var(--not-working) 14%, transparent);
  }

  .line.flag::before {
    color: var(--not-working);
  }

  ul {
    margin: 0;
    padding: 8px 14px 14px;
    border-top: 1px solid var(--line);
    list-style: none;
    font: 12px/1.5 var(--mono);
    color: var(--dim);
  }

  li {
    padding-left: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }

  li.heading {
    padding-left: 0;
    margin-top: 6px;
    color: var(--not-working);
  }

  .clean {
    margin: 0;
    padding: 8px 14px;
    border-top: 1px solid var(--line);
    color: var(--working);
    font-size: 12px;
  }
</style>
