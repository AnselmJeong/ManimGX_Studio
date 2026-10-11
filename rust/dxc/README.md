# Windows shader compiler

The wheel and editable installation carry the same pinned official `dxcompiler.dll`
beside the engine. The engine selects it explicitly by absolute path. `dxil.dll` is
optional with this compiler version and is not distributed. `LICENSE-DXC` carries
the compiler's complete notices, including its SPIR-V dependencies.

With `MANIMGX_SOURCES` set, this crate collects the original binary release and
matching compiler source, plus every Git submodule at that revision. Ordinary
non-Windows builds do not fetch DXC. The source bundle can build ManimGX offline
using the included compiler payload.

To rebuild the compiler itself, unpack these source archives from the complete
source bundle's `sources/` directory. These commands run in a shell with `tar`:

```sh
mkdir -p dxc-src
tar -xf sources/01b62ad47db7dee3dd33f90e7339cf9e860b3f93.tar.gz -C dxc-src --strip-components=1
mkdir -p dxc-src/external/DirectX-Headers dxc-src/external/SPIRV-Headers dxc-src/external/SPIRV-Tools
tar -xf sources/980971e835876dc0cde415e8f9bc646e64667bf7.tar.gz -C dxc-src/external/DirectX-Headers --strip-components=1
tar -xf sources/496543121ce6419f23d6fa5d7194ba66c36212d2.tar.gz -C dxc-src/external/SPIRV-Headers --strip-components=1
tar -xf sources/ef96ed763b43b59b33b31b362f09a02b729fa1c9.tar.gz -C dxc-src/external/SPIRV-Tools --strip-components=1
cmake -S dxc-src -B dxc-build -C dxc-src/cmake/caches/PredefinedParams.cmake \
  -DCMAKE_BUILD_TYPE=Release -DLLVM_INCLUDE_TESTS=OFF -DHLSL_INCLUDE_TESTS=OFF \
  -DSPIRV_BUILD_TESTS=OFF -DSPIRV_SKIP_TESTS=ON -DSPIRV_BUILD_FUZZER=OFF \
  -DSPIRV_TOOLS_USE_MIMALLOC=OFF
cmake --build dxc-build --config Release --target dxcompiler
```

DXC's `docs/BuildingAndTestingDXC.rst` describes the required C++ compiler, CMake,
Python, and Windows SDK/WDK. Choose the generator and target architecture for your
toolchain. Optional upstream test and fuzzing programs are disabled here; their
separate dependencies are not part of the compiler library. The main source's
`.gitmodules` has a stale `googletest` declaration, but the pinned Git tree contains
only the three submodules above, none with nested Git submodules.
