#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
cask=twine-app
if brew list --cask "$cask" >/dev/null 2>&1; then
    echo "Uninstall $cask before running the installation smoke check" >&2
    exit 1
fi

app_directory="$(mktemp -d "${TMPDIR:-/tmp}/twine-cask-install.XXXXXX")"
cleanup() {
    if brew list --cask "$cask" >/dev/null 2>&1; then
        brew uninstall --cask "$cask"
    fi
    rm -rf "$app_directory"
}
trap cleanup EXIT

brew install --cask --appdir="$app_directory" "twineproject/tap/$cask"
app="$app_directory/Twine.app"
test -d "$app"
expected="$(sed -n 's/^  version "\([^"]*\)"$/\1/p' "$repo/Casks/$cask.rb")"
actual="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")"
[[ "$actual" == "$expected" ]]
architectures="$(lipo -archs "$app/Contents/MacOS/Twine")"
[[ " $architectures " == *" arm64 "* ]]
[[ " $architectures " == *" x86_64 "* ]]
codesign --verify --deep --strict "$app"
xcrun stapler validate "$app"
spctl --assess --type execute --verbose=2 "$app"
archive="$(brew --cache --cask "twineproject/tap/$cask")"
if [[ "$archive" == *.dmg ]]; then
    codesign --verify --strict "$archive"
    xcrun stapler validate "$archive"
    spctl --assess --type open --context context:primary-signature --verbose=2 "$archive"
fi
echo "Installed and verified signed, notarized Twine $actual in $app_directory"
