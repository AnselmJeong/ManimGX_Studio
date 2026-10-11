//! NASM for a build script, with nothing installed: NASM is compiled into the build script that
//! depends on this crate, which runs it as a process of itself. Call [`serve`] first in that
//! script's `main`; [`command`] is then NASM.

use std::ffi::{CString, c_char, c_int};
use std::process::Command;

unsafe extern "C" {
    fn nasm_main(argc: c_int, argv: *const *const c_char) -> c_int;
}

/// Set in the environment of the build script started as NASM.
const AS_NASM: &str = "MANIMGX_BUILD_SCRIPT_AS_NASM";

/// Be NASM, if [`command`] started this process: it then exits with NASM's status.
pub fn serve() {
    if std::env::var_os(AS_NASM).is_none() {
        return;
    }
    let args: Vec<CString> = std::env::args_os().skip(1).map(|a| CString::new(a.into_encoded_bytes()).unwrap()).collect();
    let mut argv: Vec<*const c_char> = std::iter::once(c"nasm".as_ptr()).chain(args.iter().map(|a| a.as_ptr())).collect();
    argv.push(std::ptr::null());
    std::process::exit(unsafe { nasm_main(argv.len() as c_int - 1, argv.as_ptr()) });
}

/// NASM, as a command to give arguments to: this build script, started as NASM.
pub fn command() -> Command {
    let mut command = Command::new(std::env::current_exe().expect("the build script's path"));
    command.env(AS_NASM, "1");
    command
}
