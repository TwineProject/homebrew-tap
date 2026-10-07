# Twine Homebrew tap

Homebrew distribution for [Twine](https://github.com/aravind-n/twine), a native
macOS workspace for coordinating coding agents. The GitHub repository
is `TwineProject/homebrew-tap`, which Homebrew addresses as `twineproject/tap`.

Twine requires macOS 26 or later. Version 0.2.0 supports Apple Silicon and Intel;
starting with 0.2.1, releases support Apple Silicon only.

## Install and update

Once this repository is published on GitHub:

```sh
brew install --cask twineproject/tap/twine-app
```

To update:

```sh
brew update
brew upgrade --cask twine-app
```

To uninstall:

```sh
brew uninstall --cask twine-app
```

Normal uninstall preserves saved sessions, workflows, transcripts, and settings.
The cask does not define a `zap` action that deletes this user data.

If you already installed Twine by dragging it into Applications, move the existing
`Twine.app` out of Applications before the first Homebrew installation. Quit
Twine before upgrading it.

The cask installs the published DMG for the release. Release packages are
Developer ID signed and notarized, and Homebrew verifies the download checksum before
installation. See [Twine's install notes](https://aravind-n.github.io/twine/documentation/guide/#install).

## Validate locally

Install Homebrew, Python 3, GitHub CLI, `actionlint`, and `shellcheck`. Authenticate
GitHub CLI with `gh auth login` to run the release updater.

```sh
make check
make audit-online
make install-smoke
```

`make install-smoke` installs into a temporary application directory and checks
the bundle version, required architectures, and code signature. It validates the
stapled notarization tickets and Gatekeeper acceptance for the app and DMG, then
uninstalls the cask. It does not launch Twine and refuses to run if this cask is
already installed.

The Homebrew checks register this checkout as `twineproject/tap` through a local
symlink. They refuse to replace an existing tap pointing at a different checkout.
To remove the local registration later, run `brew untap twineproject/tap`.

To update the cask locally after publishing a stable release:

```sh
make update
# Or select a particular published stable release:
make update RELEASE_TAG=v0.2.0
make check
make audit-online
make install-smoke
git diff -- Casks/twine-app.rb
```

The updater accepts published `vMAJOR.MINOR.PATCH` releases from `aravind-n/twine`,
prefers a DMG, and falls back to a ZIP. Releases before 0.2.1 use universal
packages; 0.2.1 and later require ARM64 packages. When updating to an ARM64
release, the updater adds `depends_on arch: :arm64` alongside the new version,
download URL, and checksum. The currently published 0.2.0 cask stays universal.
The updater downloads the archive and `SHA256SUMS` and verifies the checksum
before changing the cask. It rejects drafts, prereleases, nightlies, and
incomplete releases, and never downgrades the cask or replaces a published
version in place.

## Update automation

The **Update Twine cask** workflow runs when this tap receives a
`repository_dispatch` event of type `twine-release-published`. A workflow in
`aravind-n/twine` must send that event when a stable release is published. You
can also start the updater manually from Actions; it has no timed schedule.

The updater checks the latest published stable release directly from
`aravind-n/twine`. It verifies the download checksum, validates the cask, and
opens a PR as a dedicated GitHub App. The workflow waits for the required
**Tap validation** check, then squash-merges that PR's exact validated commit.

Only the `maintainers` team and update App can merge to `main`. Both must use PRs
and pass the checks, including administrators. The bot merges only its own
verified update to `Casks/twine-app.rb`; it does not merge other contributions.
Human approval is not required for these release updates. GitHub's general
auto-merge option is disabled; automatic merging is performed by this updater.

The update workflow requires a `TAP_APP_CLIENT_ID` repository variable and a
`TAP_APP_PRIVATE_KEY` Actions secret for the dedicated GitHub App. The App needs
access only to this tap, with Contents and Pull requests read/write permissions.
No token for the source repository is required. Repository owners can manage the
settings and team membership.

Homebrew installs new versions when users run `brew upgrade`. Twine has no
automatic updater inside the app.
