//! Mesa's lavapipe, Vulkan on the CPU, for a Linux machine with no GPU driver: the Linux wheels
//! bundle it beside the engine (`manimgx/lavapipe/libvulkan_lvp.so`, made by
//! `scripts/release/build_lavapipe.sh`). The engine loads it itself, as Vulkan's loader loads a driver,
//! and gives wgpu an instance of it: neither the system's loader nor the environment is involved.

/// An instance of the bundled lavapipe; None where there is none (not Linux, or an engine built
/// from source); an error saying why, when it is there but cannot be used.
#[cfg(target_os = "linux")]
pub fn instance() -> Result<Option<wgpu::Instance>, String> {
    use std::ffi::{CStr, CString, OsStr};
    use std::os::unix::ffi::{OsStrExt, OsStringExt};

    use ash::vk;
    use wgpu::hal::{api::Vulkan, vulkan};

    unsafe {
        // the engine's folder, then the driver in it
        let mut engine: libc::Dl_info = std::mem::zeroed();
        if libc::dladdr(instance as *const libc::c_void, &mut engine) == 0 || engine.dli_fname.is_null() {
            return Err("the engine cannot find its own file".into());
        }
        let engine = std::path::Path::new(OsStr::from_bytes(CStr::from_ptr(engine.dli_fname).to_bytes()));
        let path = engine.with_file_name("lavapipe").join("libvulkan_lvp.so");
        if !path.exists() {
            return Ok(None);
        }
        let name = CString::new(path.into_os_string().into_vec()).map_err(|e| e.to_string())?;
        let library = libc::dlopen(name.as_ptr(), libc::RTLD_NOW | libc::RTLD_LOCAL);
        if library.is_null() {
            return Err(CStr::from_ptr(libc::dlerror()).to_string_lossy().into_owned());
        }
        // a driver's entry points, as the loader finds them: its interface version agreed first
        let negotiate = libc::dlsym(library, c"vk_icdNegotiateLoaderICDInterfaceVersion".as_ptr());
        let get_instance_proc_addr = libc::dlsym(library, c"vk_icdGetInstanceProcAddr".as_ptr());
        if negotiate.is_null() || get_instance_proc_addr.is_null() {
            return Err(format!("{} is no Vulkan driver", name.to_string_lossy()));
        }
        let negotiate: unsafe extern "system" fn(*mut u32) -> vk::Result = std::mem::transmute(negotiate);
        let mut version = 7;
        let negotiated = negotiate(&mut version);
        if negotiated != vk::Result::SUCCESS {
            return Err(format!("its loader interface: {negotiated}"));
        }
        let get_instance_proc_addr: vk::PFN_vkGetInstanceProcAddr = std::mem::transmute(get_instance_proc_addr);
        let entry = ash::Entry::from_static_fn(ash::StaticFn { get_instance_proc_addr });
        // the instance wgpu-hal would make (Instance::init_with_callback), from this entry
        let api = entry.try_enumerate_instance_version().map_err(|e| e.to_string())?.unwrap_or(vk::API_VERSION_1_0);
        let flags = wgpu::InstanceFlags::default();
        let extensions = vulkan::Instance::desired_extensions(&entry, api, flags).map_err(|e| e.to_string())?;
        let names: Vec<_> = extensions.iter().map(|name| name.as_ptr()).collect();
        let app = vk::ApplicationInfo::default()
            .engine_name(c"wgpu-hal")
            .engine_version(2)
            .api_version(if api < vk::API_VERSION_1_1 { vk::API_VERSION_1_0 } else { vk::API_VERSION_1_3 });
        let create = vk::InstanceCreateInfo::default().application_info(&app).enabled_extension_names(&names);
        let raw = entry.create_instance(&create, None).map_err(|e| format!("vkCreateInstance: {e}"))?;
        let hal = vulkan::Instance::from_raw(entry, raw, api, 0, None, extensions, flags, Default::default(), false, None).map_err(|e| e.to_string())?;
        Ok(Some(wgpu::Instance::from_hal::<Vulkan>(hal)))
    }
}

#[cfg(not(target_os = "linux"))]
pub fn instance() -> Result<Option<wgpu::Instance>, String> {
    Ok(None)
}
