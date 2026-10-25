# Handshake Homebrew tap

Homebrew distribution for [Handshake](https://github.com/standing-desks/handshake), a native
macOS workspace for coordinating coding agents. The GitHub repository
is `TwineProject/homebrew-tap`, which Homebrew addresses as `twineproject/tap`.

Handshake requires macOS 26 or later. Architecture requirements follow the release
package: ARM64 packages require Apple Silicon; universal packages also support Intel.

The cask is `handshake`. The legacy `twine-app` and `twine-ade` tokens map to it.

Existing users stay on `twineproject/tap`; no cross-tap migration is required.

## Install and update

To install:

```sh
brew install --cask twineproject/tap/handshake
```

To update:

```sh
# Once when migrating from twine-app or twine-ade on Homebrew 6 or newer:
brew trust --cask twineproject/tap/handshake
brew update
brew upgrade --cask twineproject/tap/handshake
```

Homebrew's [tap trust](https://docs.brew.sh/Tap-Trust) does not follow a cask
rename. Trust the new canonical cask before updating; this keeps trust limited
to Handshake. Omit the trust command on older Homebrew versions that do not
provide it. The update migrates the existing package identity and retains its
installation directory.

To uninstall:

```sh
brew uninstall --cask twineproject/tap/handshake
```

Normal uninstall preserves saved sessions, workflows, transcripts, and settings.
The cask does not define a `zap` action that deletes this user data.

If you installed Twine or Handshake by dragging it into Applications, move the
existing `Twine.app` or `Handshake.app` out of Applications before the first
Homebrew installation. Quit the app before upgrading it.

The cask installs the published DMG for the release. Release packages are
Developer ID signed and notarized, and Homebrew verifies the download checksum before
installation. See [Handshake's install notes](https://standing-desks.github.io/handshake/documentation/guide/#install).

## Migration status

The 0.4.0 cask intentionally contains `REPLACE_WITH_FINAL_RELEASE_SHA256`.
This placeholder fails audit and must be replaced with the checksum of the
finalized release artifact before publishing the migration. Never substitute a
local candidate's checksum.

## Validate locally

The migration can be checked without Homebrew using `make test`, `actionlint`,
and `shellcheck scripts/*.sh`. Run Homebrew checks only in a separate test account
or VM with its own Homebrew, or in this tap's CI. Do not register this development
checkout over a maintainer's installed tap.

Install Homebrew, Python 3, GitHub CLI, `actionlint`, and `shellcheck`. Authenticate
GitHub CLI with `gh auth login` to run the release updater.

```sh
make check
make audit-online
make install-smoke
```

`make audit-online` validates the pinned release independently of which version
is currently latest on GitHub. The updater discovers new stable releases;
the audit and installation checks validate the selected package.

`make install-smoke` installs into a temporary application directory and checks
the bundle version, required architectures, and code signature. It validates the
stapled notarization tickets and Gatekeeper acceptance for the app and DMG, then
uninstalls the cask. It does not launch Handshake and refuses to run if this cask is
already installed.

The Homebrew checks register this checkout as `twineproject/tap` through a local
symlink. They refuse to replace an existing tap pointing at a different checkout.
To remove the local registration later, run `brew untap twineproject/tap`.

To update the cask locally after publishing a stable release, run `make update`.
Set `RELEASE_TAG` to a published `vMAJOR.MINOR.PATCH` tag to select a release.

```sh
make update
make check
make audit-online
make install-smoke
git diff -- Casks/handshake.rb
```

The updater accepts published `vMAJOR.MINOR.PATCH` releases from `standing-desks/handshake`,
prefers a DMG, and falls back to a ZIP. It determines the architecture from the
selected asset's filename, accepting ARM64 or universal packages regardless of
release version and rejecting ambiguous packages. ARM64 packages add
`depends_on arch: :arm64`; universal packages remove that requirement. The
version, download URL, and checksum come from the selected release.
The updater downloads the archive and `SHA256SUMS` and verifies the checksum
before changing the cask. It rejects drafts, prereleases, nightlies, and
incomplete releases, and never downgrades the cask or replaces a published
version in place.

## Update automation

The **Update Handshake cask** workflow runs when this tap receives a
`repository_dispatch` event of type `handshake-release-published` or the legacy
`twine-release-published` event. A workflow in
`standing-desks/handshake` must send that event when a stable release is published. You
can also start the updater manually from Actions; it has no timed schedule.

Release notifications select the published stable tag from `standing-desks/handshake`;
manual runs select its latest published stable release. It verifies the download checksum, validates the cask, and
opens a PR as a dedicated GitHub App. The workflow waits for the required
**Tap validation** check, then squash-merges that PR's exact validated commit.

Only the `maintainers` team and update App can merge to `main`. Both must use PRs
and pass the checks, including administrators. The bot merges only its own
verified update to `Casks/handshake.rb`; it does not merge other contributions.
Human approval is not required for these release updates. GitHub's general
auto-merge option is disabled; automatic merging is performed by this updater.

The update workflow requires a `TAP_APP_CLIENT_ID` repository variable and a
`TAP_APP_PRIVATE_KEY` Actions secret for the dedicated GitHub App. The App needs
access only to this tap, with Contents and Pull requests read/write permissions.
No token for the source repository is required. Repository owners can manage the
settings and team membership.

Homebrew installs new versions when users run `brew upgrade`. Handshake has no
automatic updater inside the app.
