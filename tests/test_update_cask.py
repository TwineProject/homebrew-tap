import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from scripts.update_cask import app_source, release_asset, update_cask, verified_checksum


# Synthetic examples stay independent of the live cask and published releases.
BASE_VERSION = "1.2.3"
NEXT_VERSION = "1.2.4"
VERSION_PAIRS = (("0.0.7", "0.0.8"), (BASE_VERSION, NEXT_VERSION),
                 ("1.9.9", "1.10.0"), ("9.9.9", "10.0.0"))
PAYLOAD = b"released app"
CHECKSUM = hashlib.sha256(PAYLOAD).hexdigest()


def cask_source(version=BASE_VERSION, architecture="universal"):
    requirement = "  depends_on arch: :arm64\n" if architecture == "arm64" else ""
    return f"""\
cask "twine-app" do
  version "{version}"
  sha256 "{'0' * 64}"

  url "https://github.com/aravind-n/twine/releases/download/v#{{version}}/Twine-#{{version}}-macos-{architecture}.zip"

{requirement}  depends_on macos: :tahoe

  app "Twine-#{{version}}/Twine.app"
end
"""


def release(version=NEXT_VERSION, extensions=("dmg", "zip"), architecture="universal"):
    return {
        "tag_name": f"v{version}", "draft": False, "prerelease": False,
        "published_at": "2026-10-06T12:00:00Z",
        "assets": [{"name": f"Twine-{version}-macos-{architecture}.{extension}"}
                   for extension in extensions] + [{"name": "SHA256SUMS"}],
    }


def download(args, **kwargs):
    target = Path(args[args.index("--dir") + 1])
    name = args[args.index("--pattern") + 1]
    (target / name).write_bytes(PAYLOAD)
    (target / "SHA256SUMS").write_text(f"{CHECKSUM}  ./{name}\n")


class UpdateCaskTests(unittest.TestCase):
    def test_only_published_stable_releases_are_accepted(self):
        for field, value in (("draft", True), ("prerelease", True),
                             ("published_at", None), ("tag_name", "nightly-20261006-abc"),
                             ("tag_name", f"v{NEXT_VERSION}-beta.1"),
                             ("tag_name", "v01.2.3")):
            with self.subTest(field=field, value=value):
                candidate = release()
                candidate[field] = value
                with self.assertRaises(ValueError):
                    release_asset(candidate)

    def test_dmg_is_preferred_and_zip_is_supported(self):
        self.assertEqual(release_asset(release())[1], "dmg")
        self.assertEqual(release_asset(release(extensions=("zip",)))[1], "zip")

    def test_architecture_is_taken_from_assets_at_any_version(self):
        for version in ("0.0.8", NEXT_VERSION, "42.0.0"):
            for architecture in ("arm64", "universal"):
                for extension in ("dmg", "zip"):
                    with self.subTest(version=version, architecture=architecture,
                                      extension=extension):
                        candidate = release(version, (extension,), architecture)
                        selected = release_asset(candidate)
                        self.assertEqual(selected[:3], (version, extension, architecture))
                        self.assertEqual(selected[3]["name"],
                                         f"Twine-{version}-macos-{architecture}.{extension}")

    def test_ambiguous_architecture_assets_are_rejected(self):
        for extra in (release(architecture="arm64")["assets"][0],
                      release()["assets"][0]):
            with self.subTest(extra=extra):
                candidate = release(architecture="arm64")
                candidate["assets"].append(extra)
                with self.assertRaisesRegex(ValueError, "ambiguous"):
                    release_asset(candidate)

    def test_zip_app_layout_and_ambiguous_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "app.zip"
            for source, expected in (("Twine.app", "Twine.app"),
                                     (f"Twine-{NEXT_VERSION}/Twine.app",
                                      "Twine-#{version}/Twine.app")):
                with zipfile.ZipFile(archive, "w") as package:
                    package.writestr(source + "/Contents/Info.plist", b"plist")
                self.assertEqual(app_source(archive, NEXT_VERSION, "zip"), expected)
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("Twine.app/Contents/Info.plist", b"plist")
                package.writestr(f"Twine-{NEXT_VERSION}/Twine.app/Contents/Info.plist", b"plist")
            with self.assertRaises(ValueError):
                app_source(archive, NEXT_VERSION, "zip")

    def test_incomplete_or_ambiguous_assets_are_rejected(self):
        for assets in ([], [{"name": "SHA256SUMS"}], [release()["assets"][0]],
                       [{"name": f"Twine-{NEXT_VERSION}-macos-unknown.dmg"},
                        {"name": "SHA256SUMS"}],
                       release()["assets"] + [release()["assets"][0]],
                       release()["assets"] + [{"name": "SHA256SUMS"}]):
            with self.subTest(assets=assets):
                candidate = release()
                candidate["assets"] = assets
                with self.assertRaises(ValueError):
                    release_asset(candidate)

    def test_checksum_formats_and_tampered_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "package.dmg"
            checksums = Path(directory) / "SHA256SUMS"
            archive.write_bytes(PAYLOAD)
            asset = {"digest": f"sha256:{CHECKSUM}"}
            for filename in (archive.name, f"./{archive.name}", f"*{archive.name}"):
                checksums.write_text(f"{CHECKSUM}  {filename}\n")
                self.assertEqual(verified_checksum(archive, checksums, asset), CHECKSUM)
            archive.write_bytes(b"changed app")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                verified_checksum(archive, checksums, asset)

    def test_missing_duplicate_or_inconsistent_checksums_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "package.dmg"
            checksums = Path(directory) / "SHA256SUMS"
            archive.write_bytes(PAYLOAD)
            entry = f"{CHECKSUM}  {archive.name}\n"
            for contents in ("", entry + entry):
                checksums.write_text(contents)
                with self.assertRaises(ValueError):
                    verified_checksum(archive, checksums, {})
            checksums.write_text(entry)
            with self.assertRaisesRegex(ValueError, "digest disagrees"):
                verified_checksum(archive, checksums, {"digest": "sha256:" + "0" * 64})

    def test_same_or_older_release_does_not_download_or_change_cask(self):
        for older, current in VERSION_PAIRS:
            with self.subTest(older=older, current=current), \
                    tempfile.TemporaryDirectory() as directory:
                source = cask_source(current)
                cask = Path(directory) / "twine-app.rb"
                cask.write_text(source)
                with patch("scripts.update_cask.subprocess.run") as downloads:
                    for version in (current, older):
                        self.assertEqual(update_cask(release(version), cask), (current, False))
                    downloads.assert_not_called()
                self.assertEqual(cask.read_text(), source)

    def test_verified_updates_accept_patch_minor_and_major_releases(self):
        for current, version in VERSION_PAIRS:
            for architecture in ("arm64", "universal"):
                with self.subTest(current=current, version=version, architecture=architecture), \
                        tempfile.TemporaryDirectory() as directory:
                    cask = Path(directory) / "twine-app.rb"
                    cask.write_text(cask_source(current))
                    with patch("scripts.update_cask.subprocess.run", side_effect=download):
                        self.assertEqual(update_cask(release(version, architecture=architecture),
                                                     cask), (version, True))
                    result = cask.read_text()
                    self.assertIn(f'version "{version}"', result)
                    self.assertIn(f'Twine-#{{version}}-macos-{architecture}.dmg"', result)
                    self.assertIn(CHECKSUM, result)
                    self.assertIn('app "Twine.app"', result)
                    self.assertIn('depends_on macos: :tahoe', result)
                    self.assertEqual(result.count('depends_on arch: :arm64'),
                                     1 if architecture == "arm64" else 0)

    def test_architecture_requirements_follow_the_selected_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(cask_source())
            with patch("scripts.update_cask.subprocess.run", side_effect=download):
                for patch_number, architecture in enumerate(("arm64", "arm64", "universal", "arm64"), 4):
                    version = f"1.2.{patch_number}"
                    self.assertEqual(update_cask(release(version, architecture=architecture), cask),
                                     (version, True))
                    result = cask.read_text()
                    self.assertEqual(result.count('depends_on arch: :arm64'),
                                     1 if architecture == "arm64" else 0)
                    if architecture == "arm64":
                        self.assertLess(result.index('depends_on arch:'),
                                        result.index('depends_on macos:'))
            with patch("scripts.update_cask.subprocess.run") as downloads:
                self.assertEqual(update_cask(release(version, architecture=architecture), cask),
                                 (version, False))
                downloads.assert_not_called()
            self.assertEqual(cask.read_text(), result)

    def test_failed_download_verification_leaves_cask_unchanged(self):
        for architecture in ("arm64", "universal"):
            with self.subTest(architecture=architecture), \
                    tempfile.TemporaryDirectory() as directory:
                source = cask_source()
                cask = Path(directory) / "twine-app.rb"
                cask.write_text(source)

                def tampered_download(args, **kwargs):
                    download(args, **kwargs)
                    target = Path(args[args.index("--dir") + 1])
                    name = args[args.index("--pattern") + 1]
                    (target / "SHA256SUMS").write_text(f"{'0' * 64}  {name}\n")

                with patch("scripts.update_cask.subprocess.run", side_effect=tampered_download):
                    with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                        update_cask(release(architecture=architecture), cask)
                self.assertEqual(cask.read_text(), source)


if __name__ == "__main__":
    unittest.main()
