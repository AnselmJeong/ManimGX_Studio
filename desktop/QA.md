# Verification — 2026-10-11

Validated on Apple Silicon macOS, Rust 1.99.0, GPUI Kit 0.7.1 and ManimGX 0.1.1.

- `cargo test --locked`: 10 tests passed, including two tests operating the production GPUI view with native test input.
- `cargo clippy --locked --all-targets -- -D warnings`: passed.
- `cargo fmt --check`: passed.
- `uv run --frozen python desktop/tests/smoke.py`: all four lessons rendered, every MP4 decoded to its end, and all preview frames existed. The ManimGX sampled layout reports found no problems. Final lesson frames were visually inspected.
- The native window was visually inspected with Korean text, a rendered lesson poster, three panes and the primary render control. Render and cancellation were exercised through the native UI.
- The installed `/Applications/ManimGX Studio.app` was launched through Launch Services with `--smoke-test`. Its production view invoked the regular renderer and completed a 1280×720, 30 fps, 13.73-second MP4 with 135 preview frames, using only its bundled Python and engine. Result: `~/Library/Application Support/ManimGX Studio/native-smoke-result.json`.
- The app bundle passed `codesign --verify --deep --strict`. Its signature is ad hoc, not Developer ID / notarized.
- Source checks passed: Ruff, ty, TypeScript, Prettier, TOML/YAML, whitespace, citation format, workflow security and REUSE.

This workspace was supplied without `.git`, so the initial checks used an isolated Git index and source snapshot. After Git was initialized at the user's request for the ManimGX_Studio repository, a direct `just check` passed every hook against the complete staged source. No Git hooks were installed. The later AI-authoring tests and live Codex verification are recorded in [AI_IMPLEMENTATION.md](AI_IMPLEMENTATION.md).

To repeat the installed-app smoke test, close Studio and run:

```sh
open -n "/Applications/ManimGX Studio.app" --args --smoke-test
```

It creates a separate workspace under `native-smoke/`, renders the bundled derivative lesson, and writes `native-smoke-result.json`. Normal launches do not automatically execute Python. Check the result file's modification time to distinguish a fresh run from an earlier result. The regular workspace is left intact.

The in-app player deliberately samples at most 240 frames at up to 12 fps and is silent. Exported MP4 files retain their original frame rate and audio. Use the system video player for full-rate playback. Rendering is bounded to 30 minutes and can be cancelled. Completed and failed run folders remain available for inspection.
