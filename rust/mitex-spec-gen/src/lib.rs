//! mitex, as ManimGX builds with it: its Typst package (0.2.7, fetched by build.rs), served to
//! Typst by the engine as `@preview/mitex:{VERSION}`, mitex's own but for `lib.typ`, this crate's,
//! which imports only the scope the converted LaTeX calls; and mitex's default command spec, made
//! from that package's `specs/`: which LaTeX commands mitex converts, and how many arguments each
//! takes. mitex's own crate of this name reads the spec from a git submodule or makes it with a
//! `typst` on the PATH; this one holds the spec made from the package served, so the converter
//! and the scope it converts for come from the same files. `tests/spec.rs` makes the spec from
//! `PACKAGE` and checks that the committed one is still what it makes.

use std::sync::LazyLock;

use mitex_spec::CommandSpec;

/// The spec as rkyv bytes.
pub const SPEC: &[u8] = include_bytes!("../spec.rkyv");

/// The default command spec, which mitex converts with when it isn't given one.
pub static DEFAULT_SPEC: LazyLock<CommandSpec> = LazyLock::new(|| CommandSpec::from_bytes(SPEC));

/// The package's version, this crate's: Typst imports it as `@preview/mitex:{VERSION}`.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");

/// The package's files Typst reads, by their paths in it.
pub const PACKAGE: [(&str, &[u8]); 5] = [
    ("typst.toml", include_bytes!(concat!(env!("MITEX_PACKAGE"), "/typst.toml"))),
    ("lib.typ", include_bytes!("../lib.typ")),
    ("specs/mod.typ", include_bytes!(concat!(env!("MITEX_PACKAGE"), "/specs/mod.typ"))),
    ("specs/prelude.typ", include_bytes!(concat!(env!("MITEX_PACKAGE"), "/specs/prelude.typ"))),
    ("specs/latex/standard.typ", include_bytes!(concat!(env!("MITEX_PACKAGE"), "/specs/latex/standard.typ"))),
];
