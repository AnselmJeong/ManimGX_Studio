//! Use the build scripts' verified source store from release tooling. OUT_DIR holds the
//! verified file under its hash; MANIMGX_SOURCES retains the original download for reuse.

fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    let [url, hash] = args.as_slice() else {
        eprintln!("usage: fetch-file URL SHA256 (OUT_DIR and optionally MANIMGX_SOURCES in the environment)");
        std::process::exit(2);
    };
    fetch::file(url, hash);
}
