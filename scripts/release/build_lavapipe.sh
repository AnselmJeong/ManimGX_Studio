#!/bin/sh
# Mesa's lavapipe, Vulkan on the CPU, for the Linux wheels: the engine draws with it on a machine
# with no GPU driver (rust/engine/src/lavapipe.rs). cibuildwheel runs this in the manylinux
# image before it builds a wheel (`sh scripts/release/build_lavapipe.sh DIRECTORY`, the package's
# manimgx/lavapipe, beside the engine): Mesa from its source (and glslang, which compiles some of
# lavapipe's shaders as Mesa builds), with corrected LLVM built from its source, into
# DIRECTORY/libvulkan_lvp.so. With --sources-only, collect the same checked inputs without
# building. MANIMGX_SOURCES retains them for the release's source archive and offline reuse.
set -eu

mesa=26.2.3
mesa_sha256=1628058a8d2c0615975de5a15ab7bbb9638c50000b5bed9456ff423ea034a81f
glslang=16.6.0
glslang_sha256=9c09b901149c729df745057dafa815278aaa101b84d2b6e14f16a42de52f97f2
llvm=21.1.8
llvm_sha256=4633a23617fa31a3ea51242586ea7fb1da7140e426bd62fc164261fe036aa142

mkdir -p "$1"
out=$(cd "$1" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
export MANIMGX_SOURCES="${MANIMGX_SOURCES:-$root/sources}"
fetch_file() {
  OUT_DIR="$work" cargo run --quiet --locked --manifest-path "$root/rust/Cargo.toml" \
    --package fetch --bin fetch-file -- "$1" "$2"
}
fetch_file "https://github.com/KhronosGroup/glslang/archive/refs/tags/$glslang.tar.gz" "$glslang_sha256"
fetch_file "https://archive.mesa3d.org/mesa-$mesa.tar.xz" "$mesa_sha256"
fetch_file "https://github.com/llvm/llvm-project/releases/download/llvmorg-$llvm/llvm-project-$llvm.src.tar.xz" "$llvm_sha256"
if [ "${2-}" = --sources-only ]; then exit 0; fi
dnf -q -y install dnf-plugins-core
python=/opt/python/cp313-cp313/bin/python
"$python" -m pip -q install --root-user-action=ignore meson ninja mako pyyaml cmake
export PATH="$work/bin:/opt/python/cp313-cp313/bin:$PATH"
cd "$work"

tar -xJf "$llvm_sha256"
patch -d "llvm-project-$llvm.src" -p1 < "$root/scripts/release/llvm/destination-class.patch"
# The JIT needs only the native target. Preserve its register-class constraints when
# rematerializing a split live range; otherwise LLVM can emit unencodable AVX2 registers.
cmake -S "llvm-project-$llvm.src/llvm" -B llvm-build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DLLVM_TARGETS_TO_BUILD=Native -DLLVM_ENABLE_RTTI=ON \
  -DLLVM_ENABLE_ASSERTIONS=OFF -DLLVM_BUILD_LLVM_DYLIB=OFF \
  -DLLVM_LINK_LLVM_DYLIB=OFF -DLLVM_BUILD_TOOLS=OFF \
  -DLLVM_INCLUDE_TESTS=OFF -DLLVM_INCLUDE_BENCHMARKS=OFF -DLLVM_INCLUDE_EXAMPLES=OFF \
  -DLLVM_ENABLE_ZLIB=OFF -DLLVM_ENABLE_ZSTD=OFF -DLLVM_ENABLE_LIBXML2=OFF
cmake --build llvm-build --parallel "$(nproc)" --target llvm-libraries llvm-config
export PATH="$work/llvm-build/bin:$PATH"
if [ "$(uname -m)" = x86_64 ]; then
  cmake --build llvm-build --parallel "$(nproc)" --target llc opt
  sh "$root/scripts/release/llvm/check.sh" "$work/llvm-project-$llvm.src"
fi

tar -xzf "$glslang_sha256"
cmake -S "glslang-$glslang" -B glslang-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$work" \
  -DENABLE_OPT=OFF -DENABLE_HLSL=OFF -DGLSLANG_TESTS=OFF -DBUILD_EXTERNAL=OFF -DENABLE_GLSLANG_JS=OFF
ninja -C glslang-build install

tar -xJf "$mesa_sha256"
# lavapipe alone, for no window system, with no disk cache; exporting the loader's interface alone
# (Mesa's src/vulkan/vulkan-icd-symbols.txt), not the LLVM linked in
echo '{ global: vk_icdGetInstanceProcAddr; vk_icdGetPhysicalDeviceProcAddr; vk_icdNegotiateLoaderICDInterfaceVersion; local: *; };' > lvp.map
meson setup mesa-build "mesa-$mesa" --buildtype=release -Db_ndebug=true \
  -Dc_args="-ffunction-sections -fdata-sections" -Dcpp_args="-ffunction-sections -fdata-sections" \
  -Dc_link_args="-Wl,--version-script=$work/lvp.map" -Dcpp_link_args="-Wl,--version-script=$work/lvp.map" \
  -Dplatforms= -Dvulkan-drivers=swrast -Dgallium-drivers= -Dopengl=false -Dglx=disabled -Degl=disabled \
  -Dgbm=disabled -Dgles1=disabled -Dgles2=disabled -Dglvnd=disabled -Dllvm=enabled -Dshared-llvm=disabled \
  -Dshader-cache=disabled -Dzlib=disabled -Dzstd=disabled -Dexpat=disabled -Dxmlconfig=disabled \
  -Dvalgrind=disabled -Dlibunwind=disabled -Dlmsensors=disabled -Dvideo-codecs= -Dmicrosoft-clc=disabled \
  -Dspirv-tools=disabled -Dintel-rt=disabled -Dgallium-va=disabled
ninja -C mesa-build src/gallium/targets/lavapipe/libvulkan_lvp.so
strip --strip-unneeded -o "$out/libvulkan_lvp.so" mesa-build/src/gallium/targets/lavapipe/libvulkan_lvp.so
