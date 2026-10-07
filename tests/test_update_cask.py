import hashlib
from pathlib import Path
import re
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from scripts.update_cask import app_source, release_asset, update_cask, verified_checksum


def release(version="0.2.0", extensions=("dmg", "zip"), architecture="universal"):
    return {
        "tag_name": f"v{version}", "draft": False, "prerelease": False,
        "published_at": "2026-10-06T12:00:00Z",
        "assets": [{"name": f"Twine-{version}-macos-{architecture}.{extension}"}
                   for extension in extensions] + [{"name": "SHA256SUMS"}],
    }


class UpdateCaskTests(unittest.TestCase):
    def test_only_published_stable_releases_are_accepted(self):
        for field, value in (("draft", True), ("prerelease", True),
                             ("published_at", None), ("tag_name", "nightly-20261006-abc"),
                             ("tag_name", "v0.2.0-beta.1"), ("tag_name", "v01.2.3")):
            with self.subTest(field=field, value=value):
                candidate = release()
                candidate[field] = value
                with self.assertRaises(ValueError):
                    release_asset(candidate)

    def test_dmg_is_preferred_and_zip_is_supported(self):
        self.assertEqual(release_asset(release())[1], "dmg")
        self.assertEqual(release_asset(release(extensions=("zip",)))[1], "zip")

    def test_arm64_packages_are_required_from_0_2_1(self):
        for version in ("0.2.1", "0.3.0", "1.0.0"):
            for extension in ("dmg", "zip"):
                with self.subTest(version=version, extension=extension):
                    candidate = release(version, (extension,), "arm64")
                    selected = release_asset(candidate)
                    self.assertEqual(selected[1], extension)
                    self.assertEqual(selected[2]["name"],
                                     f"Twine-{version}-macos-arm64.{extension}")
                    with self.assertRaisesRegex(ValueError, "no arm64"):
                        release_asset(release(version, (extension,)))

    def test_ambiguous_arm64_assets_are_rejected(self):
        candidate = release("0.2.1", architecture="arm64")
        candidate["assets"].append(candidate["assets"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate release asset"):
            release_asset(candidate)

    def test_zip_app_layout_and_ambiguous_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "app.zip"
            for source, expected in (("Twine.app", "Twine.app"),
                                     ("Twine-0.2.0/Twine.app", "Twine-#{version}/Twine.app")):
                with zipfile.ZipFile(archive, "w") as package:
                    package.writestr(source + "/Contents/Info.plist", b"plist")
                self.assertEqual(app_source(archive, "0.2.0", "zip"), expected)
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("Twine.app/Contents/Info.plist", b"plist")
                package.writestr("Twine-0.2.0/Twine.app/Contents/Info.plist", b"plist")
            with self.assertRaises(ValueError):
                app_source(archive, "0.2.0", "zip")

    def test_incomplete_or_ambiguous_assets_are_rejected(self):
        for assets in ([], [{"name": "SHA256SUMS"}],
                       [{"name": "Twine-0.2.0-macos-universal.dmg"}],
                       release()["assets"] + [release()["assets"][0]],
                       release()["assets"] + [{"name": "SHA256SUMS"}]):
            with self.subTest(assets=assets):
                candidate = release()
                candidate["assets"] = assets
                with self.assertRaises(ValueError):
                    release_asset(candidate)

    def test_checksum_formats_and_tampered_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "Twine-0.2.0-macos-universal.dmg"
            checksums = Path(directory) / "SHA256SUMS"
            archive.write_bytes(b"released app")
            expected = hashlib.sha256(archive.read_bytes()).hexdigest()
            asset = {"digest": f"sha256:{expected}"}
            for filename in (archive.name, f"./{archive.name}", f"*{archive.name}"):
                checksums.write_text(f"{expected}  {filename}\n")
                self.assertEqual(verified_checksum(archive, checksums, asset), expected)
            archive.write_bytes(b"changed app")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                verified_checksum(archive, checksums, asset)

    def test_missing_duplicate_or_inconsistent_checksums_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "Twine-0.2.0-macos-universal.dmg"
            checksums = Path(directory) / "SHA256SUMS"
            archive.write_bytes(b"released app")
            expected = hashlib.sha256(archive.read_bytes()).hexdigest()
            entry = f"{expected}  {archive.name}\n"
            for contents in ("", entry + entry):
                checksums.write_text(contents)
                with self.assertRaises(ValueError):
                    verified_checksum(archive, checksums, {})
            checksums.write_text(entry)
            with self.assertRaisesRegex(ValueError, "digest disagrees"):
                verified_checksum(archive, checksums, {"digest": "sha256:" + "0" * 64})

    def test_same_or_older_release_does_not_download_or_change_cask(self):
        source = 'cask "twine-app" do\n  version "0.2.0"\nend\n'
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(source)
            with patch("scripts.update_cask.subprocess.run") as download:
                for version in ("0.2.0", "0.1.9"):
                    self.assertEqual(update_cask(release(version), cask), ("0.2.0", False))
                download.assert_not_called()
            self.assertEqual(cask.read_text(), source)

    def test_verified_new_release_updates_zip_to_dmg(self):
        original = (Path(__file__).resolve().parents[1] /
                    "Casks/twine-app.rb").read_text()
        source = re.sub(r'^  version "[^"]+"$', '  version "0.0.0"', original,
                        flags=re.MULTILINE)
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(source)

            def download(args, **kwargs):
                target = Path(args[args.index("--dir") + 1])
                name = "Twine-0.2.0-macos-universal.dmg"
                (target / name).write_bytes(b"released app")
                checksum = hashlib.sha256(b"released app").hexdigest()
                (target / "SHA256SUMS").write_text(f"{checksum}  ./{name}\n")

            with patch("scripts.update_cask.subprocess.run", side_effect=download):
                self.assertEqual(update_cask(release(), cask), ("0.2.0", True))
            result = cask.read_text()
            self.assertIn('version "0.2.0"', result)
            self.assertIn('macos-universal.dmg"', result)
            self.assertIn('app "Twine.app"', result)

    def test_verified_arm64_updates_add_a_single_architecture_requirement(self):
        source = (Path(__file__).resolve().parents[1] / "Casks/twine-app.rb").read_text()
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(source)

            def download(args, **kwargs):
                name = args[args.index("--pattern") + 1]
                target = Path(args[args.index("--dir") + 1])
                (target / name).write_bytes(b"ARM64 released app")
                checksum = hashlib.sha256(b"ARM64 released app").hexdigest()
                (target / "SHA256SUMS").write_text(f"{checksum}  ./{name}\n")

            with patch("scripts.update_cask.subprocess.run", side_effect=download):
                for version in ("0.2.1", "0.2.2"):
                    self.assertEqual(update_cask(release(version, architecture="arm64"), cask),
                                     (version, True))
                    result = cask.read_text()
                    self.assertIn(f'version "{version}"', result)
                    self.assertIn('Twine-#{version}-macos-arm64.dmg"', result)
                    self.assertIn(hashlib.sha256(b"ARM64 released app").hexdigest(), result)
                    self.assertEqual(result.count('depends_on arch: :arm64'), 1)
                    self.assertIn('depends_on macos: :tahoe', result)
                    self.assertLess(result.index('depends_on arch:'), result.index('depends_on macos:'))

            with patch("scripts.update_cask.subprocess.run") as download:
                self.assertEqual(update_cask(release("0.2.2", architecture="arm64"), cask),
                                 ("0.2.2", False))
                download.assert_not_called()
            self.assertEqual(cask.read_text(), result)

    def test_failed_arm64_verification_preserves_universal_cask(self):
        source = (Path(__file__).resolve().parents[1] / "Casks/twine-app.rb").read_text()
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(source)

            def download(args, **kwargs):
                target = Path(args[args.index("--dir") + 1])
                name = "Twine-0.2.1-macos-arm64.dmg"
                (target / name).write_bytes(b"tampered ARM64 app")
                (target / "SHA256SUMS").write_text(f"{'0' * 64}  {name}\n")

            with patch("scripts.update_cask.subprocess.run", side_effect=download):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    update_cask(release("0.2.1", architecture="arm64"), cask)
            self.assertEqual(cask.read_text(), source)

    def test_failed_download_verification_leaves_cask_unchanged(self):
        source = '  version "0.1.0"\n'
        with tempfile.TemporaryDirectory() as directory:
            cask = Path(directory) / "twine-app.rb"
            cask.write_text(source)

            def download(args, **kwargs):
                target = Path(args[args.index("--dir") + 1])
                name = "Twine-0.2.0-macos-universal.dmg"
                (target / name).write_bytes(b"tampered")
                (target / "SHA256SUMS").write_text(f"{'0' * 64}  {name}\n")

            with patch("scripts.update_cask.subprocess.run", side_effect=download):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    update_cask(release(), cask)
            self.assertEqual(cask.read_text(), source)


if __name__ == "__main__":
    unittest.main()
