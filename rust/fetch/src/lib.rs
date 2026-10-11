//! Others' sources for a build script: the engine's crates hold only ManimGX's code, and fetch
//! what they build from others (x264, NASM, FFmpeg, libopus, mitex's Typst package) at build time,
//! each pinned by the hash of its files. Immutable binary resources are pinned by their bytes.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use sha2::{Digest, Sha256};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

/// The tree of files in the archive at `url` (its one top folder, if it has one), unpacked into
/// the build script's OUT_DIR, in a folder named by `hash`: the SHA-256 of its files, each one's
/// path, length and bytes, by path. It names the files, not the archive, which hosts regenerate:
/// any archive of the same files passes, and a tree once checked is found again by its name.
///
/// The archive is kept in the folder MANIMGX_SOURCES names (an absolute path), if it names one:
/// read from there, and published there only after its files pass verification. A folder that
/// holds the archives builds offline, and a build into an empty one gathers what it is built
/// from, as a release does for its complete source. A build script fetches the same archives on
/// every target (what it compiles of them may differ), so one build gathers what every build reads.
pub fn tree(url: &str, hash: &str) -> PathBuf {
    stored(url, hash, unpack)
}

/// An immutable file, verified against the SHA-256 of its bytes. Like `tree`, this reads and
/// collects the original download in MANIMGX_SOURCES, and publishes only verified content.
pub fn file(url: &str, hash: &str) -> PathBuf {
    stored(url, hash, verified_file)
}

type Prepare = fn(&Path, &Path, &str) -> Result<PathBuf>;

fn stored(url: &str, hash: &str, prepare: Prepare) -> PathBuf {
    println!("cargo:rerun-if-env-changed=MANIMGX_SOURCES");
    let out = PathBuf::from(std::env::var_os("OUT_DIR").expect("a build script's OUT_DIR"));
    let sources = std::env::var_os("MANIMGX_SOURCES").map(PathBuf::from);
    acquire(url, hash, &out, sources.as_deref(), prepare).unwrap_or_else(|error| panic!("{url}: {error}"))
}

fn acquire(url: &str, hash: &str, out: &Path, sources: Option<&Path>, prepare: Prepare) -> Result<PathBuf> {
    let tree = out.join(hash);
    if tree.exists() && sources.is_none() {
        return Ok(tree);
    }
    fs::create_dir_all(out)?;
    let work = tempfile::tempdir_in(out)?;
    let unpacked = work.path().join("files");
    let cached = sources.map(|folder| folder.join(url.rsplit('/').next().unwrap()));
    let verified = cached.as_ref().filter(|archive| archive.is_file()).map(|archive| prepare(archive, &unpacked, hash));
    let root = match verified {
        Some(Ok(root)) => root,
        invalid => {
            if let Some(Err(error)) = invalid {
                eprintln!("{url}: ignoring invalid cached archive: {error}");
            }
            // Each candidate stays private until verified. Staging beside its destination
            // makes publication atomic even when MANIMGX_SOURCES is on another filesystem.
            let folder = sources.unwrap_or(out);
            fs::create_dir_all(folder)?;
            let download = tempfile::tempdir_in(folder)?;
            let archive = download.path().join("archive");
            run(Command::new("curl")
                .args(["-fsSL", "--retry", "3", "--retry-connrefused", "--connect-timeout", "30", "--max-time", "300", "--retry-max-time", "600", "-o"])
                .arg(&archive)
                .arg(url))?;
            let root = prepare(&archive, &unpacked, hash)?;
            if let Some(cached) = cached {
                publish(&archive, &cached, |copy| prepare(copy, &work.path().join("published"), hash).is_ok())?;
            }
            root
        }
    };
    // Concurrent builders publish the same verified content; only one needs to win.
    if let Err(error) = fs::rename(root, &tree)
        && !tree.exists()
    {
        return Err(error.into());
    }
    Ok(tree)
}

/// Publishes the verified `archive` as the source store's copy, `cached`. Concurrent builders
/// publish archives of the same files, and one copy serves them all: on Windows, a copy that
/// another builder is reading can't be replaced (`tar.exe` doesn't share its deletion), and it
/// stays if it `verifies` too.
fn publish(archive: &Path, cached: &Path, verifies: impl FnOnce(&Path) -> bool) -> Result<()> {
    match fs::rename(archive, cached) {
        Err(error) if !verifies(cached) => Err(error.into()),
        _ => Ok(()),
    }
}

fn verified_file(archive: &Path, prepared: &Path, hash: &str) -> Result<PathBuf> {
    let found = Sha256::digest(fs::read(archive)?).iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    if found != hash {
        return Err(format!("{}: its bytes hash to {found}, not {hash}", archive.display()).into());
    }
    fs::copy(archive, prepared)?;
    Ok(prepared.to_owned())
}

fn unpack(archive: &Path, unpacked: &Path, hash: &str) -> Result<PathBuf> {
    if unpacked.exists() {
        fs::remove_dir_all(unpacked)?;
    }
    fs::create_dir(unpacked)?;
    // the archive named from its own folder: GNU tar reads `C:` in a path as a remote host
    run(Command::new("tar").current_dir(archive.parent().unwrap()).arg("-xf").arg(archive.file_name().unwrap()).arg("-C").arg(unpacked))?;
    let entries = fs::read_dir(unpacked)?.map(|entry| entry.map(|entry| entry.path())).collect::<std::io::Result<Vec<_>>>()?;
    let root = match &entries[..] {
        [folder] if folder.is_dir() => folder.clone(),
        _ => unpacked.to_owned(),
    };
    let found = hash_files(&root)?;
    if found != hash {
        return Err(format!("{}: its files hash to {found}, not {hash}", archive.display()).into());
    }
    Ok(root)
}

/// The SHA-256 of a tree's files: each one's path (`/` between its parts), length and bytes, by
/// path.
pub fn files_hash(root: &Path) -> String {
    hash_files(root).unwrap_or_else(|error| panic!("{}: {error}", root.display()))
}

fn hash_files(root: &Path) -> std::io::Result<String> {
    let mut files = Vec::new();
    let mut folders = vec![PathBuf::new()];
    while let Some(folder) = folders.pop() {
        for entry in fs::read_dir(root.join(&folder))? {
            let path = folder.join(entry?.file_name());
            if root.join(&path).is_dir() { folders.push(path) } else { files.push(path) }
        }
    }
    let key = |path: &PathBuf| path.iter().map(|part| part.to_string_lossy()).collect::<Vec<_>>().join("/");
    files.sort_by_cached_key(key);
    let mut sha = Sha256::new();
    for path in &files {
        let bytes = fs::read(root.join(path))?;
        sha.update(key(path).as_bytes());
        sha.update([0]);
        sha.update((bytes.len() as u64).to_le_bytes());
        sha.update(&bytes);
    }
    Ok(sha.finalize().iter().map(|byte| format!("{byte:02x}")).collect())
}

fn run(command: &mut Command) -> Result<()> {
    let output = command.output().map_err(|error| format!("{command:?}: {error}"))?;
    if !output.status.success() {
        return Err(format!("{command:?}: {}\n{}", output.status, String::from_utf8_lossy(&output.stderr)).into());
    }
    Ok(())
}

#[cfg(all(test, windows))]
mod tests {
    use std::fs;
    use std::os::windows::fs::OpenOptionsExt;

    /// How `tar.exe` opens the archive it reads: others may read it too, but not replace it.
    const FILE_SHARE_READ: u32 = 0x1;

    #[test]
    fn a_copy_another_builder_reads_stays_only_if_it_verifies() {
        let folder = tempfile::tempdir().unwrap();
        let (archive, cached) = (folder.path().join("archive"), folder.path().join("cached"));
        fs::write(&archive, "ours").unwrap();
        fs::write(&cached, "theirs").unwrap();
        let reader = fs::OpenOptions::new().read(true).share_mode(FILE_SHARE_READ).open(&cached).unwrap();
        assert!(super::publish(&archive, &cached, |_| false).is_err());
        super::publish(&archive, &cached, |_| true).unwrap();
        assert_eq!(fs::read_to_string(&cached).unwrap(), "theirs");
        drop(reader);
        super::publish(&archive, &cached, |_| false).unwrap();
        assert_eq!(fs::read_to_string(&cached).unwrap(), "ours");
    }
}
