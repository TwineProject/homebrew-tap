#!/usr/bin/env python3
"""Publish a validated cask update and request merge through branch protection."""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPOSITORY = "TwineProject/homebrew-tap"
CASK = "Casks/twine-app.rb"


def run(root, *args):
    return subprocess.run(
        args, cwd=root, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.rstrip("\n")


def propose_update(root, version, app_slug, repository):
    if repository != REPOSITORY:
        raise ValueError("The update bot is restricted to TwineProject/homebrew-tap")
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise ValueError("Expected a stable MAJOR.MINOR.PATCH version")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app_slug):
        raise ValueError("Expected the GitHub App's slug")
    if f'  version "{version}"' not in (root / CASK).read_text():
        raise ValueError("The cask does not contain the validated version")

    branch = f"cask/twine-app-{version}"
    bot = f"{app_slug}[bot]"
    pulls = json.loads(run(
        root, "gh", "api", "--method", "GET", f"repos/{repository}/pulls",
        "-f", "state=all", "-f", f"head=TwineProject:{branch}",
        "-f", "base=main", "-f", "per_page=100",
    ))
    existing = max(pulls, key=lambda pull: pull["number"], default=None)
    if existing is not None:
        if existing["state"] != "open":
            print(f"PR #{existing['number']} is closed; leaving this release alone")
            return
        if existing["user"]["login"] != bot:
            raise ValueError("The existing PR was not opened by the tap update bot")

    changes = run(root, "git", "status", "--porcelain", "--untracked-files=all")
    if changes not in (f" M {CASK}", f"M  {CASK}"):
        raise ValueError("A release update must change only Casks/twine-app.rb")
    run(root, "git", "add", "--", CASK)
    validated_tree = run(root, "git", "write-tree")
    run(root, "gh", "auth", "setup-git", "--hostname", "github.com")

    remote = run(root, "git", "ls-remote", "--heads", "origin", branch)
    if remote:
        run(root, "git", "fetch", "--no-tags", "origin", f"refs/heads/{branch}")
        head = run(root, "git", "rev-parse", "FETCH_HEAD")
        if run(root, "git", "rev-parse", f"{head}^{{tree}}") != validated_tree:
            raise ValueError("The existing branch differs from the validated update")
    else:
        if existing is not None:
            raise ValueError("The existing PR's branch is missing")
        user = json.loads(run(root, "gh", "api", f"users/{bot}"))
        run(root, "git", "switch", "-c", branch)
        run(
            root, "git", "-c", f"user.name={bot}",
            "-c", f"user.email={user['id']}+{bot}@users.noreply.github.com",
            "commit", "-m", f"cask: replace Twine release with {version}",
        )
        head = run(root, "git", "rev-parse", "HEAD")
        run(root, "git", "push", "origin", f"HEAD:refs/heads/{branch}")

    if existing is None:
        with tempfile.TemporaryDirectory(prefix="twine-cask-pr-") as directory:
            body = Path(directory) / "body.md"
            body.write_text(
                f"Update Twine to the published stable release v{version}.\n\n"
                "The updater verified the archive against SHA256SUMS. Cask style, "
                "audit, updater tests, and installation checks passed before this PR.\n\n"
                f"Upstream release: https://github.com/aravind-n/twine/releases/tag/v{version}\n"
            )
            print(run(
                root, "gh", "pr", "create", "--repo", repository,
                "--base", "main", "--head", branch,
                "--title", f"cask: replace Twine release with {version}",
                "--body-file", str(body),
            ))

    pull = json.loads(run(
        root, "gh", "pr", "view", branch, "--repo", repository, "--json",
        "number,author,baseRefName,headRefName,headRefOid,isCrossRepository,isDraft,files,state",
    ))
    if (
        pull["state"] != "OPEN"
        or pull["isDraft"]
        or pull["isCrossRepository"]
        or pull["author"]["login"] != bot
        or pull["baseRefName"] != "main"
        or pull["headRefName"] != branch
        or pull["headRefOid"] != head
        or [file["path"] for file in pull["files"]] != [CASK]
    ):
        raise ValueError("The PR must contain exactly the validated bot cask update")
    print(run(
        root, "gh", "pr", "merge", str(pull["number"]), "--repo", repository,
        "--auto", "--squash", "--match-head-commit", head,
    ))


if __name__ == "__main__":
    propose_update(
        Path(__file__).resolve().parent.parent,
        os.environ["VERSION"], os.environ["APP_SLUG"], os.environ["GH_REPO"],
    )
