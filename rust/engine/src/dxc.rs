//! The DXC staged by the engine's build and included beside the extension by maturin. Its
//! absolute path makes the compiler independent of the working directory and process PATH.

use std::path::PathBuf;

pub(super) fn compiler() -> Result<wgpu::Dx12Compiler, String> {
    // Cargo runs its test executable from target's deps directory; maturin instead installs
    // the extension and its resources together. Both load this build's exact staged compiler.
    #[cfg(test)]
    let path = PathBuf::from(env!("OUT_DIR")).join("dxcompiler.dll");
    #[cfg(not(test))]
    let path = module_path()?.with_file_name("dxcompiler.dll");
    if !path.is_file() { return Err(format!("the engine's shader compiler is missing: {}", path.display())); }
    Ok(wgpu::Dx12Compiler::DynamicDxc { dxc_path: path.to_str().ok_or("the shader compiler's path is not Unicode")?.to_owned() })
}

#[cfg(not(test))]
fn module_path() -> Result<PathBuf, String> {
    use std::ffi::OsString;
    use std::os::windows::ffi::OsStringExt;
    use windows_sys::Win32::System::LibraryLoader::{GetModuleFileNameW, GetModuleHandleExW, GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT};
    unsafe {
        let mut module = std::ptr::null_mut();
        let flags = GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT;
        if GetModuleHandleExW(flags, compiler as *const u16, &mut module) == 0 {
            return Err(format!("the engine cannot find its own module: {}", std::io::Error::last_os_error()));
        }
        // Windows' maximum extended path length, in UTF-16 code units.
        let mut path = vec![0; 32768];
        let length = GetModuleFileNameW(module, path.as_mut_ptr(), path.len() as u32) as usize;
        if length == 0 || length == path.len() {
            return Err(format!("the engine cannot find its own file: {}", std::io::Error::last_os_error()));
        }
        Ok(PathBuf::from(OsString::from_wide(&path[..length])))
    }
}
