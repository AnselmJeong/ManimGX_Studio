//! The committed spec is the one mitex's package makes, and the package the engine serves is
//! mitex's (but for lib.typ, this crate's). mitex's build makes the spec with `typst query` over the package's
//! `specs/mod.typ` for `<mitex-packages>`; this test does the same with Typst as a library, over
//! `PACKAGE`, the files the engine serves. After upgrading mitex, write the new spec with
//! `MITEX_SPEC=write cargo test -p mitex-spec-gen` (in `rust/`).

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use mitex_spec_gen::{PACKAGE, VERSION};
use typst::diag::{FileError, FileResult};
use typst::foundations::{Bytes, Datetime, Duration, Label};
use typst::introspection::{Introspector, MetadataElem};
use typst::syntax::{FileId, RootedPath, Source, VirtualPath, VirtualRoot};
use typst::text::{Font, FontBook};
use typst::utils::{LazyHash, PicoStr};
use typst::{Library, LibraryExt, World};
use typst_kit::fonts::{FontStore, embedded};
use typst_layout::PagedDocument;

/// The package's files, its `specs/mod.typ` the main one.
struct Package {
    library: LazyHash<Library>,
    fonts: FontStore,
    main: FileId,
}

impl World for Package {
    fn library(&self) -> &LazyHash<Library> {
        &self.library
    }
    fn book(&self) -> &LazyHash<FontBook> {
        self.fonts.book()
    }
    fn main(&self) -> FileId {
        self.main
    }
    fn source(&self, id: FileId) -> FileResult<Source> {
        let text = String::from_utf8(self.file(id)?.to_vec()).map_err(|_| FileError::InvalidUtf8)?;
        Ok(Source::new(id, text))
    }
    fn file(&self, id: FileId) -> FileResult<Bytes> {
        let path = id.get().vpath().get_without_slash();
        let file = PACKAGE.iter().find(|(p, _)| *p == path);
        file.map(|(_, bytes)| Bytes::new(*bytes)).ok_or_else(|| FileError::NotFound(path.into()))
    }
    fn font(&self, index: usize) -> Option<Font> {
        self.fonts.font(index)
    }
    fn today(&self, _: Option<Duration>) -> Option<Datetime> {
        None
    }
}

/// The spec the package makes: every package's commands in one spec, as mitex's build merges them.
fn make() -> mitex_spec::CommandSpec {
    let mut fonts = FontStore::new();
    fonts.extend(embedded());
    let main = RootedPath::new(VirtualRoot::Project, VirtualPath::new("specs/mod.typ").unwrap()).intern();
    let world = Package { library: LazyHash::new(Library::default()), fonts, main };
    let document = typst::compile::<PagedDocument>(&world).output.expect("the specs compile");
    let label = Label::new(PicoStr::intern("mitex-packages")).unwrap();
    let content = document.introspector().query_label(label).expect("one <mitex-packages>");
    let value = &content.to_packed::<MetadataElem>().expect("metadata").value;
    let packages: mitex_spec::query::PackagesVec =
        serde_json::from_value(serde_json::to_value(value).unwrap()).expect("mitex's package specs");
    let mut spec = mitex_spec::JsonCommandSpec::default();
    for package in packages.0 {
        spec.commands.extend(package.spec.commands);
    }
    spec.into()
}

/// A spec's commands, in order, for comparing.
fn commands(spec: &mitex_spec::CommandSpec) -> BTreeMap<String, serde_json::Value> {
    spec.items().map(|(name, item)| (name.to_owned(), serde_json::to_value(item).unwrap())).collect()
}

#[test]
fn the_committed_spec_is_the_packages() {
    let made = make();
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("spec.rkyv");
    if std::env::var("MITEX_SPEC").as_deref() == Ok("write") {
        std::fs::write(&path, made.to_bytes()).unwrap();
    }
    let committed = mitex_spec::CommandSpec::from_bytes(&std::fs::read(&path).unwrap());
    let (made, committed) = (commands(&made), commands(&committed));
    assert!(made.len() > 900, "{} commands: the package's specs were not all read", made.len());
    assert!(made == committed, "spec.rkyv is not what mitex's package makes: MITEX_SPEC=write");
}

#[test]
fn the_package_served_is_mitexs() {
    // every Typst file of mitex's package but its WASM plugin's (mitex.typ), whose place lib.typ
    // takes, and these files as mitex publishes them
    let package = Path::new(env!("MITEX_PACKAGE"));
    let mut typst = BTreeSet::new();
    let mut stack = vec![package.to_path_buf()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(dir).unwrap().map(Result::unwrap) {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "typ") || path.ends_with("typst.toml") {
                typst.insert(path.strip_prefix(package).unwrap().to_str().unwrap().replace('\\', "/"));
            }
        }
    }
    typst.remove("mitex.typ");
    let served: BTreeSet<String> = PACKAGE.iter().map(|(path, _)| (*path).to_owned()).collect();
    assert_eq!(served, typst, "PACKAGE is not every Typst file of mitex's package");
    for (path, bytes) in PACKAGE.iter().filter(|(path, _)| *path != "lib.typ") {
        assert_eq!(*bytes, &std::fs::read(package.join(path)).unwrap()[..], "{path} is not mitex's");
    }
    let manifest = std::str::from_utf8(PACKAGE[0].1).unwrap();
    assert!(manifest.contains(&format!("version = \"{VERSION}\"")), "typst.toml is not mitex {VERSION}");
}
