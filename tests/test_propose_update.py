import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "propose_update.py"
spec = importlib.util.spec_from_file_location("propose_update", SCRIPT)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class ProposeUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="twine-pr-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "checkout"
        self.remote = Path(self.temp.name) / "remote.git"
        self.root.mkdir()
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Test maintainer")
        self.git("config", "user.email", "maintainer@example.test")
        (self.root / "Casks").mkdir()
        self.cask = self.root / updater.CASK
        self.cask.write_text('cask "twine-app" do\n  version "0.2.0"\nend\n')
        (self.root / "README.md").write_text("Tap documentation\n")
        self.git("add", ".")
        self.git("commit", "-m", "tap: add initial cask")
        self.git("init", "--bare", str(self.remote))
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "origin", "main")
        self.cask.write_text(self.cask.read_text().replace("0.2.0", "0.3.0"))
        self.pulls = []
        self.overrides = {}
        self.gh_calls = []
        self.branch = "cask/twine-app-0.3.0"
        self.bot = "twine-tap-updater[bot]"
        self.real_run = updater.run

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE
        ).rstrip("\n")

    def remote_head(self):
        return self.git("--git-dir", str(self.remote), "rev-parse", self.branch)

    def fake_run(self, root, *args):
        if args[0] != "gh":
            return self.real_run(root, *args)
        self.gh_calls.append(args)
        if args[1:3] == ("api", "--method"):
            return json.dumps(self.pulls)
        if args[1:3] == ("api", f"users/{self.bot}"):
            return '{"id": 123}'
        if args[1:3] == ("auth", "setup-git"):
            return ""
        if args[1:3] == ("pr", "create"):
            return "https://github.com/TwineProject/homebrew-tap/pull/7"
        if args[1:3] == ("pr", "view"):
            head = self.remote_head()
            files = self.git("diff", "--name-only", "main", head).splitlines()
            pull = {
                "number": 7, "author": {"login": self.bot}, "baseRefName": "main",
                "headRefName": self.branch, "headRefOid": head,
                "isCrossRepository": False, "isDraft": False, "state": "OPEN",
                "files": [{"path": path} for path in files],
            }
            return json.dumps(pull | self.overrides)
        if args[1:3] == ("pr", "merge"):
            return "Auto-merge enabled"
        raise AssertionError(f"Unexpected GitHub command: {args}")

    def propose(self):
        with patch.object(updater, "run", self.fake_run):
            updater.propose_update(self.root, "0.3.0", "twine-tap-updater", updater.REPOSITORY)

    def publish_existing_branch(self, extra_change=False):
        self.git("switch", "-c", self.branch)
        if extra_change:
            (self.root / "README.md").write_text("Unexpected documentation edit\n")
        self.git("add", ".")
        self.git("commit", "-m", "cask: replace Twine release with 0.3.0")
        self.git("push", "origin", self.branch)
        self.git("switch", "main")
        self.cask.write_text(self.cask.read_text().replace("0.2.0", "0.3.0"))

    def merge_calls(self):
        return [args for args in self.gh_calls if args[1:3] == ("pr", "merge")]

    def test_new_pr_merges_only_the_published_cask_commit(self):
        self.propose()
        head = self.remote_head()
        self.assertEqual(self.git("diff", "--name-only", "main", head), updater.CASK)
        self.assertEqual(self.git("show", "-s", "--format=%an", head), self.bot)
        self.assertEqual(self.merge_calls(), [(
            "gh", "pr", "merge", "7", "--repo", updater.REPOSITORY,
            "--auto", "--squash", "--match-head-commit", head,
        )])

    def test_refuses_changes_outside_the_cask(self):
        (self.root / "README.md").write_text("Unexpected edit\n")
        with self.assertRaisesRegex(ValueError, "change only"):
            self.propose()
        self.assertFalse(self.merge_calls())
        self.assertEqual(self.git("ls-remote", "--heads", "origin", self.branch), "")

    def test_refuses_untracked_files(self):
        (self.root / "unexpected.txt").write_text("Unexpected file\n")
        with self.assertRaisesRegex(ValueError, "change only"):
            self.propose()
        self.assertFalse(self.merge_calls())

    def test_retry_reuses_validated_branch_and_enables_merge(self):
        self.publish_existing_branch()
        head = self.remote_head()
        self.pulls = [{"number": 7, "state": "open", "user": {"login": self.bot}}]
        self.propose()
        self.assertEqual(self.remote_head(), head)
        self.assertEqual(len(self.merge_calls()), 1)
        self.assertFalse(any(args[1:3] == ("pr", "create") for args in self.gh_calls))

    def test_refuses_existing_branch_with_unvalidated_changes(self):
        self.publish_existing_branch(extra_change=True)
        with self.assertRaisesRegex(ValueError, "differs from the validated"):
            self.propose()
        self.assertFalse(self.merge_calls())

    def test_refuses_existing_pr_from_another_author(self):
        self.pulls = [{"number": 7, "state": "open", "user": {"login": "someone-else"}}]
        with self.assertRaisesRegex(ValueError, "not opened by"):
            self.propose()
        self.assertFalse(self.merge_calls())

    def test_does_not_reopen_closed_pr(self):
        self.pulls = [{"number": 7, "state": "closed", "user": {"login": self.bot}}]
        self.propose()
        self.assertFalse(self.merge_calls())
        self.assertEqual(self.git("ls-remote", "--heads", "origin", self.branch), "")

    def test_refuses_changed_pr_before_enabling_merge(self):
        self.overrides = {"headRefOid": "0" * 40}
        with self.assertRaisesRegex(ValueError, "exactly the validated"):
            self.propose()
        self.assertFalse(self.merge_calls())


if __name__ == "__main__":
    unittest.main()
