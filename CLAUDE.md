# Notes for Claude

## This repository is public

`origin` is a public GitHub repository. Anyone can read, copy and index what gets pushed, and it stays in the
history even after it's deleted. Before every commit and every push:

1. Stage files by name. Don't use `git add -A` or `git add .`. Check the list with `git status`.
2. Read the whole diff that will be published: `git diff --cached` before committing, and
   `git log -p @{upstream}..HEAD` before pushing. Look for:
   - credentials: passwords, API keys, tokens, private keys, `.env` files, URLs with a login in them
   - details about this computer or its users: absolute paths containing a user name, user names, the host
     name, e-mail addresses other than the GitHub noreply address, IP addresses, Wi-Fi names
   - local data: `data/` (the children's learning progress), `aufnahmen/` (recordings), logs,
     `sounds/eigene/` (often copyrighted), build output
3. Run `python3 tools/push_check.py`. The same check runs as the pre-push hook in `.githooks/pre-push`. If
   `git config core.hooksPath` doesn't print `.githooks`, tell the user the hook is off in this clone.
4. If anything is flagged, stop and show it to the user. Never bypass the hook (`git push --no-verify` or
   similar) on your own. Only the user decides that a finding is a false alarm.

Also:

- Don't write paths from this machine into tracked files. Work them out at runtime, as
  `tools/make_desktop_app.py` does with `Path(__file__)` and `shutil.which`.
- Commits use the GitHub noreply address. Don't change `user.name` or `user.email`.
- Keep the `.gitignore` entries for secrets and local data.
- Commit and push only when the user asks.
