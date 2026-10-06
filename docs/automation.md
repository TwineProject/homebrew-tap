# Configure unattended cask updates

The daily update workflow verifies a new Twine release, changes only
`Casks/twine-app.rb`, opens a PR as the tap's dedicated GitHub App, and enables
squash auto-merge for that PR's exact commit. GitHub merges after **Tap validation**
passes. That check independently runs the cask audit, updater tests, installation,
architecture checks, signature verification, and notarization checks.

`main` accepts PRs only. The `maintainers` team and the dedicated update App are
the only actors allowed to merge. Required checks apply to both, including
repository administrators. Human approval is not required, so a bot release PR
can merge unattended. The workflow never enables auto-merge on other authors'
PRs or changes outside the cask. Owners can still administer the repository's
settings and change these rules.

## One-time GitHub App setup

GitHub's built-in `GITHUB_TOKEN` leaves checks for bot-created PRs waiting for a
maintainer to approve their workflow runs. A dedicated GitHub App allows those
checks to run unattended. See [GitHub's token documentation](https://docs.github.com/en/actions/concepts/security/github_token).

1. [Register an App under TwineProject](https://github.com/organizations/TwineProject/settings/apps/new).
   Use **Twine Tap Updater** as the name and
   `https://github.com/TwineProject/homebrew-tap` as the homepage. If the name is
   taken, choose another and use its actual slug below.
2. Turn off **Active** under Webhook. No callback, OAuth, device flow, or webhook
   is needed.
3. Under **Repository permissions**, grant **Contents: Read and write** and
   **Pull requests: Read and write**. Metadata read access is implicit. Leave all
   other permissions off, including organization permissions.
4. Select **Only on this account**, then create the App.
5. Under **Install App**, install it on **Only select repositories**, selecting
   `homebrew-tap`.
6. Copy the **Client ID** from General settings. Generate and download a private
   key. Keep the key outside this checkout; do not commit it or paste it into chat.
7. Store the Client ID as a repository variable and the key as an Actions secret:

   ```sh
   gh variable set TAP_APP_CLIENT_ID --repo TwineProject/homebrew-tap --body 'YOUR_CLIENT_ID'
   gh secret set TAP_APP_PRIVATE_KEY --repo TwineProject/homebrew-tap < /absolute/path/to/downloaded-key.pem
   ```

The App is installed only on this tap. The workflow requests short-lived tokens
for this repository, and the App cannot change branch protection. No credential
for `aravind-n/twine` is needed to download its public releases.

## Protect main and enable the workflow

After the initial checkout is published to `main`, apply the branch protection
with the App's actual slug (the final part of its `github.com/apps/...` URL):

```sh
make protect-main APP_SLUG=twine-tap-updater
```

Run this with your administrator account, not the App's token. The setup script
requires the existing `maintainers` team to have access to this repository. It
replaces this tap's `main` branch protection with the policy described above:
required PR, zero required human approvals, up-to-date branch, **Tap validation**
provided by GitHub Actions, no force pushes or deletion, resolved conversations,
and maintainers/App merge restrictions. Run it only when configuring this tap.

The repository must allow auto-merge and squash merges. These settings have
already been enabled; merge commits and rebase merges are disabled, and merged
PR branches are deleted automatically.

Open **Actions → Check tap** and run it on `main` to verify the published setup.
Then run **Actions → Update Twine cask** on `main` to verify release discovery.
The update workflow verifies the App credentials even when the cask already
contains the latest release. In that case it exits without opening a PR.

## Publishing a new Twine version

Publish a stable `vMAJOR.MINOR.PATCH` release on `aravind-n/twine` with the signed,
notarized universal DMG and `SHA256SUMS`. Within the next daily run (12:17 UTC),
the update workflow proposes and enables auto-merge for the cask update. You can
also start it manually after releasing.

If validation fails, the workflow does not propose the update. If a PR's required
check fails, GitHub leaves it unmerged. The workflow reuses an open bot PR only
when its entire tree matches the validated checkout. It does not force-push a
branch or reopen a closed PR; closing a PR deliberately blocks that version's
automatic update. If an open PR falls behind `main`, a maintainer must update its
branch so checks run again before it can merge.

GitHub may disable a public repository's schedule after 60 days without activity.
Re-enable the workflow from Actions if that happens. This schedule monitors
releases; it does not update users' installed apps. Users run `brew update` and
`brew upgrade --cask twine-app` to install a newer version.
