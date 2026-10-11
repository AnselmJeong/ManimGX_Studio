# Natural-language film authoring

The desktop app owns projects, conversation, scene plans, previews and revisions.
A separate Python worker speaks the installed Codex App Server protocol (tested CLI
0.160.0), using stdlib only. It first plans, then generates a complete ManimGX scene,
then renders and decodes an MP4. At most two render-error repair attempts are allowed.
A successful result is applied atomically; failure/cancel retains the original project.

The provider uses its own private `codex/` home and empty scratch directory in the
Studio data directory, ChatGPT OAuth, an environment allowlist, ephemeral threads,
no agent tools, no paid API fallback, live model discovery and quota preflight before
each turn. Included usage must be explicitly allowed. Account default is persisted
as an empty model string. Each job owns its process and cancellation; jobs serialize.
Generated Python is checked before executing and rendered under a macOS sandbox.

UI: New film (Command-N), AI creation conversation, scene plan in the preview pane,
create/revise (Command-Return), cancellation, restore previous version, project save,
Codex connect/cancel/disconnect/refresh and account model selection. Python remains
an advanced tab. Prompt drafts, conversation, plans and successful revisions persist.

Delivery: source, tests, a local app bundle and installed-app validation. Source is
tracked in Git for the requested ManimGX_Studio repository. No release publication,
automatic CLI installation or credential copying.
Validation includes fake protocol failures, quota decisions, process cancellation,
project compatibility, real GPUI interactions, real sandboxed rendering and, when
Studio OAuth is available, a live creation plus conversational revision.

## Validation evidence (2026-10-11)

- 14 Rust tests: project migration/revisions, render lifecycle, real GPUI input,
  selection, themes, new-film composer and Command-Return submission.
- 24 Python tests: fake App Server stream ordering, final deduplication, failures,
  credentials/environment isolation, quota denial before thread creation, missing
  models, unexpected tool requests, startup/quiet-turn cancellation, repair limits,
  previous-source preservation and macOS sandbox read/write/network boundaries.
- Real bundled Python rendered and decoded two MP4s through the complete worker
  pipeline with a deterministic fake provider; the second conversational edit
  changed the source and preserved the first version.
- Real packaged GUI: entered a new request, generated a video, revised its color,
  restored its previous version and verified the persisted session state.
- Ruff, rustfmt, Clippy, root ty and browser TypeScript/Prettier checks passed.
- The supplied source archive initially had no `.git` metadata. After initializing
  Git for the requested repository publication, `just check` passed every hook,
  including REUSE and workflow security. `git diff --cached --check` also passed.
- Studio's private ChatGPT login was completed and verified with Codex CLI 0.160.0.
  Live account-default model `gpt-6.1-sol` created an 8-second blue square-to-circle
  film, then changed the shapes to yellow and extended the ending by two seconds.
  A further revision included the actual preview JPEG, removed the bottom caption
  and added a subtitle while preserving the color and duration.
- All three live runs used the installed app's bundled Python and workers with
  PATH=/usr/bin:/bin, normal Studio authentication and the macOS render sandbox.
  No fake provider or API key was used. All succeeded without a repair attempt.
  The 1280×720 H.264 files decoded completely (152 variable-duration frames each;
  durations 8.033, 10.033 and 10.033 seconds). Sampled output frames were inspected.
  The final project retained six conversation messages and two previous versions,
  with the prior source and render paths unchanged. Evidence and projects are in
  `qa-output/ai-live/`; `created.mp4`, `revised.mp4` and `preview-revised.mp4` are
  copies of the actual outputs, and `evidence.json` records their decode results.
- Bundle is locally signed (ad hoc), not notarized. Previous installed app is kept
  in a timestamped backup in /Applications. Existing user projects are preserved.

Installed 0.2.0 was launched with PATH=/usr/bin:/bin. Its executable and worker
hashes match the verified bundle, signature verification passed and launcher stderr
was empty. The UI automation inventory could not resolve the newly replaced installed
bundle path; GUI create/revise/restore evidence above is from the packaged build.
Live inference was verified through the installed workers, not by automating the
installed window. No credentials were copied, and the user's live session was not
replaced by the verification projects.
