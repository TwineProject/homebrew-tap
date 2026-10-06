#!/usr/bin/env python3
"""Update the Twine cask from a published stable GitHub release."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


UPSTREAM = "aravind-n/twine"
CASK = Path(__file__).resolve().parents[1] / "Casks/twine-app.rb"
VERSION = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"


def version_tuple(version):
    if not re.fullmatch(VERSION, version):
        raise ValueError(f"Invalid stable version: {version}")
    return tuple(int(part) for part in version.split("."))


def release_asset(release):
    if release["draft"] or release["prerelease"] or not release["published_at"]:
        raise ValueError("Only published stable releases can update the cask")
    tag = release["tag_name"]
    if not tag.startswith("v"):
        raise ValueError(f"Expected a vMAJOR.MINOR.PATCH tag, got {tag}")
    version = tag[1:]
    version_tuple(version)
    assets = release["assets"]
    for extension in ("dmg", "zip"):
        name = f"Twine-{version}-macos-universal.{extension}"
        matches = [asset for asset in assets if asset["name"] == name]
        if len(matches) > 1:
            raise ValueError(f"Duplicate release asset: {name}")
        if matches:
            if sum(asset["name"] == "SHA256SUMS" for asset in assets) != 1:
                raise ValueError("Expected exactly one SHA256SUMS release asset")
            return version, extension, matches[0]
    raise ValueError("Release has no universal Twine DMG or ZIP")


def verified_checksum(archive, checksums, asset):
    matches = []
    for line in checksums.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})\s+\*?(?:\./)?(.+)", line)
        if match and match[2] == archive.name:
            matches.append(match[1])
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one checksum for {archive.name}")
    expected = matches[0]
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError(f"Checksum mismatch for {archive.name}")
    if asset.get("digest") and asset["digest"] != f"sha256:{expected}":
        raise ValueError("GitHub asset digest disagrees with SHA256SUMS")
    return expected


def app_source(archive, version, extension):
    if extension == "dmg":
        return "Twine.app"
    with zipfile.ZipFile(archive) as package:
        suffix = "/Contents/Info.plist"
        matches = [name[:-len(suffix)] for name in package.namelist()
                   if name.endswith("Twine.app" + suffix)]
    if matches == ["Twine.app"]:
        return "Twine.app"
    if matches == [f"Twine-{version}/Twine.app"]:
        return "Twine-#{version}/Twine.app"
    raise ValueError("ZIP must contain exactly one Twine.app in a supported layout")


def update_cask(release, cask=CASK):
    version, extension, asset = release_asset(release)
    contents = cask.read_text()
    current = re.findall(r'^  version "([^"]+)"$', contents, re.MULTILINE)
    if len(current) != 1:
        raise ValueError("Expected exactly one cask version")
    if version_tuple(version) <= version_tuple(current[0]):
        print(f"Keeping Twine {current[0]}; latest selected release is {version}")
        return current[0], False

    with tempfile.TemporaryDirectory(prefix="twine-cask-") as directory:
        subprocess.run(
            ["gh", "release", "download", release["tag_name"], "--repo", UPSTREAM,
             "--pattern", asset["name"], "--pattern", "SHA256SUMS", "--dir", directory],
            check=True,
        )
        directory = Path(directory)
        checksum = verified_checksum(
            directory / asset["name"], directory / "SHA256SUMS", asset
        )
        application = app_source(directory / asset["name"], version, extension)

    replacements = {
        "version": version,
        "sha256": checksum,
        "url": (f"https://github.com/{UPSTREAM}/releases/download/v#{{version}}/"
                f"Twine-#{{version}}-macos-universal.{extension}"),
        "app": application,
    }
    for field, value in replacements.items():
        contents, count = re.subn(
            rf'^  {field} "[^"]+"$', f'  {field} "{value}"', contents,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError(f"Expected exactly one cask {field}")
    temporary = cask.with_suffix(".rb.tmp")
    temporary.write_text(contents)
    temporary.replace(cask)
    print(f"Updated Twine {current[0]} to {version} ({extension}, SHA-256 verified)")
    return version, True


def main():
    tag = os.environ.get("RELEASE_TAG", "")
    if tag:
        if not tag.startswith("v"):
            raise ValueError("RELEASE_TAG must be vMAJOR.MINOR.PATCH")
        version_tuple(tag[1:])
    endpoint = f"repos/{UPSTREAM}/releases/" + (f"tags/{tag}" if tag else "latest")
    response = subprocess.run(
        ["gh", "api", endpoint], check=True, capture_output=True, text=True
    )
    version, changed = update_cask(json.loads(response.stdout))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            stream.write(f"version={version}\nchanged={str(changed).lower()}\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
