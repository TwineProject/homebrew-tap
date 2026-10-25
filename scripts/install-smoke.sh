#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
cask=handshake
qualified_cask="${TAP:-twineproject/tap}/$cask"
case "$qualified_cask" in
    standing-desks/tap/handshake|twineproject/tap/handshake) ;;
    *) echo "Unsupported Handshake cask: $qualified_cask" >&2; exit 1 ;;
esac
for installed_token in "$cask" twine-app twine-ade; do
    if brew list --cask "$installed_token" >/dev/null 2>&1; then
        echo "Uninstall $installed_token before running the installation smoke check" >&2
        exit 1
    fi
done

app_directory="$(mktemp -d "${TMPDIR:-/tmp}/handshake-cask-install.XXXXXX")"
cleanup() {
    if brew list --cask "$cask" >/dev/null 2>&1; then
        brew uninstall --cask "$qualified_cask"
    fi
    rm -rf "$app_directory"
}
trap cleanup EXIT

brew install --cask --appdir="$app_directory" "$qualified_cask"
app="$app_directory/Handshake.app"
test -d "$app"
expected="$(sed -n 's/^  version "\([^"]*\)"$/\1/p' "$repo/Casks/$cask.rb")"
actual="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")"
[[ "$actual" == "$expected" ]]
architectures="$(lipo -archs "$app/Contents/MacOS/Handshake")"
required_architecture="$(sed -n 's/^  depends_on arch: :\([a-z0-9_]*\)$/\1/p' "$repo/Casks/$cask.rb")"
case "$required_architecture" in
    arm64) [[ "$architectures" == arm64 ]] ;;
    "")
        [[ " $architectures " == *" arm64 "* ]]
        [[ " $architectures " == *" x86_64 "* ]]
        ;;
    *) echo "Unsupported cask architecture requirement: $required_architecture" >&2; exit 1 ;;
esac
codesign --verify --deep --strict "$app"
xcrun stapler validate "$app"
spctl --assess --type execute --verbose=2 "$app"
archive="$(brew --cache --cask "$qualified_cask")"
if [[ "$archive" == *.dmg ]]; then
    codesign --verify --strict "$archive"
    xcrun stapler validate "$archive"
    spctl --assess --type open --context context:primary-signature --verbose=2 "$archive"
fi
echo "Installed and verified signed, notarized Handshake $actual in $app_directory"
