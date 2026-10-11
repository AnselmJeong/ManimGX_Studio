# Bundled components

ManimGX Studio uses GPUI Kit 0.7.1 (Apache-2.0) and its GPUI dependencies.
Their source and license metadata are fixed in Cargo.lock; source is available at
https://github.com/longbridge/gpui-kit and https://crates.io/crates/gpui-pre.

The local macOS bundle includes CPython 3.14.4 from python-build-standalone,
ManimGX 0.1.1, its font packages, and PyAV 18.1.0. Python package license
files and distribution metadata are preserved in Resources/python. ManimGX's
third-party notice is also copied to Resources/MANIMGX-LICENSE-THIRD-PARTY.
The exact Python dependency graph is in runtime/uv.lock.

The animation examples in this app were written for ManimGX Studio. Preview
stills are rendered from those same editable examples.

This script produces a locally signed development deliverable. Before public
redistribution, include the applicable licenses and corresponding source for
all compiled dependencies (including ManimGX's GPL-licensed encoder), and
use Developer ID signing and notarization.
