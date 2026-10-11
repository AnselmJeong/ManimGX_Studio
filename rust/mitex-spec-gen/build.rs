//! mitex's Typst package, 0.2.7 as Typst Universe publishes it, fetched: the engine serves its
//! manifest and specs, with this crate's own lib.typ in place of mitex's.

fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    let package = fetch::tree(
        "https://packages.typst.org/preview/mitex-0.2.7.tar.gz",
        "03157cb3ea5c005d43db76291badf057503a2478ceec284d3e7de4de8e65b0f6",
    );
    println!("cargo:rustc-env=MITEX_PACKAGE={}", package.display());
}
