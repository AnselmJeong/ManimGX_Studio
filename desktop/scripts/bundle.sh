#!/usr/bin/env bash
set -euo pipefail
studio_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$studio_root"
profile="${1:-release}"
if [[ "$profile" != debug && "$profile" != release ]]; then
    echo 'Usage: bundle.sh [debug|release]' >&2
    exit 1
fi
if [[ "$profile" == release ]]; then
    cargo build --locked --release -j 6
else
    cargo build --locked -j 6
fi
app="$studio_root/dist/ManimGX Studio.app"
resources="$app/Contents/Resources"
mkdir -p "$app/Contents/MacOS" "$resources"
cp "target/$profile/manimgx-studio" "$app/Contents/MacOS/manimgx-studio"
strip "$app/Contents/MacOS/manimgx-studio"
uv python install 3.14.4 --install-dir "$studio_root/.runtime/python"
python_root="$studio_root/.runtime/python/cpython-3.14.4-macos-aarch64-none"
if [[ ! -x "$python_root/bin/python3" ]]; then
    echo 'This package script currently targets Apple Silicon macOS.' >&2
    exit 1
fi
uv export --project runtime --frozen --no-dev --no-emit-project --format requirements-txt --output-file .runtime/requirements.txt
uv pip install --python "$python_root/bin/python3" \
    --target "$python_root/lib/python3.14/site-packages" \
    --require-hashes --only-binary :all: -r .runtime/requirements.txt
rsync -a --delete "$python_root/" "$resources/python/"
cp runtime/worker.py runtime/ai_worker.py runtime/codex_client.py "$resources/"
mkdir -p "$resources/assets"
cp assets/*.jpg "$resources/assets/"
cp ../LICENSE "$resources/LICENSE"
cp ../LICENSE-THIRD-PARTY "$resources/MANIMGX-LICENSE-THIRD-PARTY"
cp THIRD-PARTY.md "$resources/THIRD-PARTY.md"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>ManimGX Studio</string>
<key>CFBundleDisplayName</key><string>ManimGX Studio</string>
<key>CFBundleIdentifier</key><string>ai.academa.manimgx-studio</string>
<key>CFBundleExecutable</key><string>manimgx-studio</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.2.0</string>
<key>CFBundleVersion</key><string>2</string>
<key>LSMinimumSystemVersion</key><string>13.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSPrincipalClass</key><string>NSApplication</string>
</dict></plist>
PLIST
# Sign nested native code inside-out. This is a local ad-hoc build, not notarized.
while IFS= read -r -d '' library; do codesign --force --sign - "$library"; done < <(find "$resources/python" -type f \( -name '*.so' -o -name '*.dylib' \) -print0)
codesign --force --sign - "$resources/python/bin/python3.14"
codesign --force --sign - "$app"
codesign --verify --deep --strict "$app"
echo "$app"
