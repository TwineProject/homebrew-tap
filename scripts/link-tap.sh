#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd -P)"
tap_directory="$(brew --repository)/Library/Taps/twineproject/homebrew-tap"
if [[ -e "$tap_directory" || -L "$tap_directory" ]]; then
    if [[ "$(cd "$tap_directory" && pwd -P)" == "$repo" ]]; then
        exit 0
    fi
    echo "twineproject/tap already points to another checkout: $tap_directory" >&2
    exit 1
fi
mkdir -p "$(dirname "$tap_directory")"
ln -s "$repo" "$tap_directory"
echo "Linked twineproject/tap to $repo"
