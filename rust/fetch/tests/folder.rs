//! The source store's contract, through separate build-script processes: only verified
//! archives are published, independent builds can share them, and a full store needs no network.

use std::fs;
use std::io::{Read, Write};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};

struct Source {
    work: tempfile::TempDir,
    hash: String,
    url: String,
}

impl Source {
    fn new() -> Self {
        let work = tempfile::tempdir().unwrap();
        let served = work.path().join("served");
        fs::create_dir_all(served.join("tree/sub")).unwrap();
        fs::write(served.join("tree/a.txt"), "a").unwrap();
        fs::write(served.join("tree/sub/b.txt"), "b").unwrap();
        let status = Command::new("tar").current_dir(&served).args(["-czf", "tree.tar.gz", "tree"]).status().unwrap();
        assert!(status.success());
        let hash = fetch::files_hash(&served.join("tree"));
        let path = served.join("tree.tar.gz").display().to_string().replace('\\', "/");
        let url = format!("file:///{}", path.trim_start_matches('/'));
        Self { work, hash, url }
    }

    fn path(&self, name: &str) -> PathBuf {
        self.work.path().join(name)
    }

    fn build(&self, out: &str) -> Command {
        let mut command = Command::new(std::env::current_exe().unwrap());
        command.args(["--exact", "build_script", "--nocapture"]);
        command.env("FETCH_TEST_URL", &self.url).env("FETCH_TEST_HASH", &self.hash);
        command.env("OUT_DIR", self.path(out)).env("MANIMGX_SOURCES", self.path("sources"));
        command.stdout(Stdio::piped()).stderr(Stdio::piped());
        command
    }

    fn check(&self, out: &str) {
        assert_eq!(fetch::files_hash(&self.path(out).join(&self.hash)), self.hash);
        assert_eq!(entries(&self.path("sources")), ["tree.tar.gz"]);
        assert_eq!(entries(&self.path(out)), std::slice::from_ref(&self.hash));
    }
}

fn entries(path: &Path) -> Vec<String> {
    let mut names: Vec<_> = fs::read_dir(path).unwrap().map(|entry| entry.unwrap().file_name().into_string().unwrap()).collect();
    names.sort();
    names
}

fn success(output: Output) {
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}

#[test]
fn build_script() {
    // Children exercise the public API without mutating the test runner's environment.
    if let Ok(url) = std::env::var("FETCH_TEST_URL") {
        let acquire = if std::env::var("FETCH_TEST_KIND").as_deref() == Ok("file") { fetch::file } else { fetch::tree };
        acquire(&url, &std::env::var("FETCH_TEST_HASH").unwrap());
    }
}

#[test]
fn an_empty_folder_gathers_archives_and_a_full_one_builds_offline() {
    let source = Source::new();
    success(source.build("first").output().unwrap());
    source.check("first");
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    success(source.build("second").output().unwrap());
    source.check("second");
}

#[test]
fn release_tooling_collects_and_reuses_the_same_verified_source_store() {
    use sha2::{Digest, Sha256};
    let source = Source::new();
    let bytes = fs::read(source.path("served/tree.tar.gz")).unwrap();
    let hash = Sha256::digest(&bytes).iter().map(|byte| format!("{byte:02x}")).collect::<String>();
    for out in ["first", "offline"] {
        let output = Command::new(env!("CARGO_BIN_EXE_fetch-file"))
            .args([&source.url, &hash])
            .env("OUT_DIR", source.path(out))
            .env("MANIMGX_SOURCES", source.path("sources"))
            .output().unwrap();
        success(output);
        assert_eq!(fs::read(source.path(out).join(&hash)).unwrap(), bytes);
        assert_eq!(fs::read(source.path("sources/tree.tar.gz")).unwrap(), bytes);
        if out == "first" { fs::remove_file(source.path("served/tree.tar.gz")).unwrap(); }
    }
}

#[test]
fn no_archive_is_retained_without_a_source_store_and_the_tree_is_reused_offline() {
    let source = Source::new();
    success(source.build("first").env_remove("MANIMGX_SOURCES").output().unwrap());
    assert_eq!(entries(&source.path("first")), std::slice::from_ref(&source.hash));
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    success(source.build("first").env_remove("MANIMGX_SOURCES").output().unwrap());
}

#[test]
fn a_warm_tree_still_populates_a_new_source_store() {
    let source = Source::new();
    success(source.build("first").env_remove("MANIMGX_SOURCES").output().unwrap());
    success(source.build("first").output().unwrap());
    source.check("first");
}

#[test]
fn invalid_downloads_publish_nothing_and_a_later_attempt_recovers() {
    let source = Source::new();
    let archive = source.path("served/tree.tar.gz");
    let valid = fs::read(&archive).unwrap();
    for invalid in [b"<html>upstream error</html>".as_slice(), &valid[..valid.len() / 2]] {
        fs::write(&archive, invalid).unwrap();
        let output = source.build("first").output().unwrap();
        assert!(!output.status.success());
        assert!(String::from_utf8_lossy(&output.stderr).contains("tar"));
        assert!(entries(&source.path("sources")).is_empty());
        assert!(entries(&source.path("first")).is_empty());
    }
    fs::write(archive, valid).unwrap();
    success(source.build("first").output().unwrap());
    source.check("first");
}

#[test]
fn a_successful_http_response_must_still_be_a_verified_archive() {
    let mut source = Source::new();
    let listener = TcpListener::bind("127.0.0.1:0").unwrap();
    source.url = format!("http://{}/tree.tar.gz", listener.local_addr().unwrap());
    let valid = fs::read(source.path("served/tree.tar.gz")).unwrap();
    let server = std::thread::spawn(move || {
        for body in [b"<html>upstream challenge</html>".to_vec(), valid] {
            let (mut stream, _) = listener.accept().unwrap();
            stream.set_read_timeout(Some(std::time::Duration::from_secs(10))).unwrap();
            let mut request = Vec::new();
            while !request.ends_with(b"\r\n\r\n") {
                let mut byte = [0];
                stream.read_exact(&mut byte).unwrap();
                request.push(byte[0]);
            }
            write!(stream, "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n", body.len()).unwrap();
            stream.write_all(&body).unwrap();
        }
    });
    assert!(!source.build("first").output().unwrap().status.success());
    assert!(entries(&source.path("sources")).is_empty());
    success(source.build("first").output().unwrap());
    source.check("first");
    server.join().unwrap();
}

#[test]
fn a_source_that_temporarily_refuses_connections_recovers() {
    use std::sync::mpsc;
    use std::time::Duration;

    let mut source = Source::new();
    let reserved = TcpListener::bind("127.0.0.1:0").unwrap();
    let address = reserved.local_addr().unwrap();
    drop(reserved); // The first requests see a refused connection, not an HTTP error.
    source.url = format!("http://{address}/tree.tar.gz");
    let archive = fs::read(source.path("served/tree.tar.gz")).unwrap();
    let (finished, stopped) = mpsc::channel();
    let server = std::thread::spawn(move || {
        if stopped.recv_timeout(Duration::from_secs(2)).is_ok() {
            return; // A downloader without retries already failed.
        }
        let listener = TcpListener::bind(address).unwrap();
        listener.set_nonblocking(true).unwrap();
        loop {
            match listener.accept() {
                Ok((mut stream, _)) => {
                    // Winsock inherits the listener's mode; request reads are blocking.
                    stream.set_nonblocking(false).unwrap();
                    stream.set_read_timeout(Some(Duration::from_secs(10))).unwrap();
                    let mut request = Vec::new();
                    while !request.ends_with(b"\r\n\r\n") {
                        let mut byte = [0];
                        stream.read_exact(&mut byte).unwrap();
                        request.push(byte[0]);
                    }
                    write!(stream, "HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n", archive.len()).unwrap();
                    stream.write_all(&archive).unwrap();
                    return;
                }
                Err(error) if error.kind() == std::io::ErrorKind::WouldBlock => {
                    if stopped.recv_timeout(Duration::from_millis(10)).is_ok() {
                        return;
                    }
                }
                Err(error) => panic!("{error}"),
            }
        }
    });
    let result = source.build("first").output().unwrap();
    let _ = finished.send(());
    server.join().unwrap();
    success(result);
    source.check("first");
}

#[test]
fn the_pin_rejects_valid_archives_with_different_files() {
    let source = Source::new();
    let output = source.build("first").env("FETCH_TEST_HASH", "0".repeat(64)).output().unwrap();
    assert!(!output.status.success());
    let error = String::from_utf8_lossy(&output.stderr);
    assert!(error.contains(&source.hash) && error.contains(&"0".repeat(64)), "{error}");
    assert!(entries(&source.path("sources")).is_empty());
    assert!(entries(&source.path("first")).is_empty());
}

#[test]
fn a_corrupted_archive_is_replaced_only_by_verified_content() {
    let source = Source::new();
    success(source.build("first").output().unwrap());
    let archive = source.path("sources/tree.tar.gz");
    fs::write(&archive, "broken cache").unwrap();
    success(source.build("second").output().unwrap());
    assert_eq!(fs::read(archive).unwrap(), fs::read(source.path("served/tree.tar.gz")).unwrap());
    source.check("second");
}

#[test]
fn cached_files_with_the_wrong_hash_are_refetched() {
    let source = Source::new();
    success(source.build("first").output().unwrap());
    let served = source.path("served");
    fs::write(served.join("tree/a.txt"), "tampered").unwrap();
    let status = Command::new("tar").current_dir(&served).args(["-czf", "../sources/tree.tar.gz", "tree"]).status().unwrap();
    assert!(status.success());
    success(source.build("second").output().unwrap());
    source.check("second");
}

#[test]
fn failed_recovery_does_not_replace_cached_data_or_publish_a_tree() {
    let source = Source::new();
    success(source.build("first").output().unwrap());
    let archive = source.path("sources/tree.tar.gz");
    fs::write(&archive, "broken cache").unwrap();
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    let output = source.build("second").output().unwrap();
    assert!(!output.status.success());
    let error = String::from_utf8_lossy(&output.stderr);
    assert!(error.contains("invalid cached archive") && error.contains("curl"), "{error}");
    assert_eq!(fs::read_to_string(archive).unwrap(), "broken cache");
    assert!(entries(&source.path("second")).is_empty());
}

#[test]
fn concurrent_builds_publish_whole_archives_and_trees() {
    let source = Source::new();
    // Share both a source store and some output directories, as independent Cargo invocations do.
    let children: Vec<_> = (0..12).map(|i| source.build(&format!("build-{}", i % 3)).spawn().unwrap()).collect();
    for child in children {
        success(child.wait_with_output().unwrap());
    }
    for i in 0..3 {
        source.check(&format!("build-{i}"));
    }
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    success(source.build("offline").output().unwrap());
    source.check("offline");
}

#[test]
fn archives_without_a_top_folder_are_supported() {
    let source = Source::new();
    let status = Command::new("tar").current_dir(source.path("served/tree")).args(["-czf", "../tree.tar.gz", "a.txt", "sub"]).status().unwrap();
    assert!(status.success());
    success(source.build("first").output().unwrap());
    source.check("first");
}

#[test]
fn output_and_source_paths_may_contain_spaces() {
    let source = Source::new();
    let sources = source.path("source archives");
    success(source.build("build output").env("MANIMGX_SOURCES", &sources).output().unwrap());
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    success(source.build("offline output").env("MANIMGX_SOURCES", sources).output().unwrap());
    assert_eq!(fetch::files_hash(&source.path("offline output").join(&source.hash)), source.hash);
}

#[cfg(unix)]
#[test]
fn an_offline_source_store_can_be_read_only() {
    use std::os::unix::fs::PermissionsExt;
    let source = Source::new();
    success(source.build("first").output().unwrap());
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    fs::set_permissions(source.path("sources"), fs::Permissions::from_mode(0o555)).unwrap();
    let output = source.build("second").output().unwrap();
    fs::set_permissions(source.path("sources"), fs::Permissions::from_mode(0o755)).unwrap();
    success(output);
    source.check("second");
}

#[test]
fn an_immutable_file_is_verified_collected_and_reused_offline() {
    use sha2::{Digest, Sha256};
    let mut source = Source::new();
    let bytes = fs::read(source.path("served/tree.tar.gz")).unwrap();
    source.hash = Sha256::digest(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
    success(source.build("first").env("FETCH_TEST_KIND", "file").env_remove("MANIMGX_SOURCES").output().unwrap());
    success(source.build("first").env("FETCH_TEST_KIND", "file").output().unwrap());
    fs::remove_file(source.path("served/tree.tar.gz")).unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(source.path("sources"), fs::Permissions::from_mode(0o555)).unwrap();
    }
    let offline = source.build("offline").env("FETCH_TEST_KIND", "file").output().unwrap();
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::set_permissions(source.path("sources"), fs::Permissions::from_mode(0o755)).unwrap();
    }
    success(offline);
    assert_eq!(fs::read(source.path("offline").join(&source.hash)).unwrap(), bytes);
    assert_eq!(entries(&source.path("sources")), ["tree.tar.gz"]);
}

#[test]
fn immutable_file_cache_corruption_is_repaired_only_by_verified_bytes() {
    use sha2::{Digest, Sha256};
    let mut source = Source::new();
    let bytes = fs::read(source.path("served/tree.tar.gz")).unwrap();
    source.hash = Sha256::digest(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
    success(source.build("first").env("FETCH_TEST_KIND", "file").output().unwrap());
    fs::write(source.path("sources/tree.tar.gz"), "corrupt cache").unwrap();
    fs::write(source.path("served/tree.tar.gz"), "invalid response").unwrap();
    let output = source.build("second").env("FETCH_TEST_KIND", "file").output().unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("its bytes hash to"));
    assert_eq!(fs::read_to_string(source.path("sources/tree.tar.gz")).unwrap(), "corrupt cache");
    assert!(entries(&source.path("second")).is_empty());
    fs::write(source.path("served/tree.tar.gz"), &bytes).unwrap();
    success(source.build("second").env("FETCH_TEST_KIND", "file").output().unwrap());
    assert_eq!(fs::read(source.path("sources/tree.tar.gz")).unwrap(), bytes);
}

#[test]
fn concurrent_builds_publish_whole_immutable_files() {
    use sha2::{Digest, Sha256};
    let mut source = Source::new();
    let bytes = fs::read(source.path("served/tree.tar.gz")).unwrap();
    source.hash = Sha256::digest(&bytes).iter().map(|byte| format!("{byte:02x}")).collect();
    let children: Vec<_> = (0..12).map(|i| source.build(&format!("build-{}", i % 3)).env("FETCH_TEST_KIND", "file").spawn().unwrap()).collect();
    for child in children { success(child.wait_with_output().unwrap()); }
    for i in 0..3 { assert_eq!(fs::read(source.path(&format!("build-{i}")).join(&source.hash)).unwrap(), bytes); }
}
