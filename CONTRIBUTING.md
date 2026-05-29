# Contributing to EasyNginx

Thanks for thinking about contributing. EasyNginx is a small, focused project, and the bar for new code is "does it make life easier for someone who's setting up nginx on a fresh server".

## Quick paths

- **Found a bug?** Open an issue with the `doctor` output, your distro, and the failing command.
- **Have a feature idea?** Open an issue first so we can scope it before you write code.
- **Want to add a distro or module?** PRs welcome — see [Adding a distro](#adding-a-distro) and [Adding a command](#adding-a-command).
- **Docs typo or improvement?** PR straight to `web/docs/`. Anyone can review.

## Development setup

EasyNginx is a Python CLI plus a bash bootstrap installer. The engine has no third-party dependencies — only the Python standard library — so there's no `pip install` or virtualenv to worry about.

```bash
git clone https://github.com/nerkoux/EasyNGINX.git
cd EasyNGINX

# Run tests
python3 tests/smoke_test.py
python3 tests/backup_test.py
python3 tests/cli_test.py
python3 tests/updater_test.py
```

Tests use only the Python standard library too. They don't touch real nginx — they monkeypatch HTTP, use a temp filesystem for backups, and parse the CLI surface without invoking it.

For docs:

```bash
cd web
npm install
npm start                         # http://localhost:3000
```

## Adding a command

1. Add an argparse block in `lib/main.py`.
2. Implement the handler in `lib/cmd_<area>.py` (or a new `cmd_<topic>.py`).
3. Wire it in the dispatch section of `main.py`.
4. Add a test case to `tests/cli_test.py` so its `--help` is exercised.
5. Document it under `web/docs/commands/`.

## Adding a distro

1. Update the `case` block in `install.sh` `detect_distro()`.
2. Add the distro_family if it's new in `lib/config.py` `_detect_nginx_paths()`.
3. Add packages and the firewall tool in `install.sh`.
4. Test the install path on a real VM or container.

## Style

- Engine code targets Python 3.8+ standard library only.
- Bash scripts pass `bash -n install.sh` (syntax check) and ideally `shellcheck`.
- Keep functions short. Prefer dispatch tables over chains of `if`/`elif`.
- New nginx config should always go through a template under `templates/` rather than string concatenation.

## Safety rules

These are non-negotiable:

- **Never reload nginx with an unvalidated config.** Always run `nginx -t` first.
- **Never overwrite a file without a snapshot.** All writes go through `nginx_mod.write_site` (sites) or `_safety_snapshot` (restore).
- **Never modify paths outside the engine's allow-list during updates.** See `ENGINE_FILES` in `lib/updater.py`.
- **Never bind a service to anything but `127.0.0.1` by default.** Dashboard, metrics endpoint, etc.

## Releases (maintainers)

```bash
scripts/release.sh 0.2.0
git push && git push --tags
```

The script bumps `lib/version.py`, commits, tags, and prints push instructions. Existing installs see the update banner within 24 hours.

## Code of Conduct

We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
