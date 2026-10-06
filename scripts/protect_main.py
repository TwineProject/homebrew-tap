#!/usr/bin/env python3
"""Configure the tap's main branch after publishing the initial checkout."""

import json
import os
import re
import subprocess

REPOSITORY = "TwineProject/homebrew-tap"


def main():
    app_slug = os.environ.get("APP_SLUG", "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app_slug):
        raise ValueError("Set APP_SLUG to the installed tap update App's slug")
    subprocess.run(["gh", "api", f"apps/{app_slug}", "--silent"], check=True)
    subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/branches/main", "--silent"], check=True
    )
    actions_app = json.loads(subprocess.check_output(
        ["gh", "api", "apps/github-actions"], text=True
    ))
    protection = {
        "required_status_checks": {
            "strict": True,
            "contexts": [],
            "checks": [{"context": "Tap validation", "app_id": actions_app["id"]}],
        },
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "require_code_owner_reviews": False,
            "require_last_push_approval": False,
            "dismiss_stale_reviews": True,
            "bypass_pull_request_allowances": {"users": [], "teams": [], "apps": []},
        },
        "restrictions": {"users": [], "teams": ["maintainers"], "apps": [app_slug]},
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    }
    subprocess.run(
        ["gh", "api", "--method", "PUT",
         f"repos/{REPOSITORY}/branches/main/protection", "--input", "-", "--silent"],
        input=json.dumps(protection), text=True, check=True,
    )
    print("main requires a PR and passing Tap validation; only maintainers and the bot can merge")


if __name__ == "__main__":
    main()
