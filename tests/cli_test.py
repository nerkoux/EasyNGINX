"""Smoke-test the CLI parser surface.

We don't run any actual nginx commands. We just confirm:
- Every documented subcommand parses.
- argparse exposes each command without import errors.
- --help works.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Make stdout/stderr tolerant of unicode on Windows consoles.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import main as easy_main  # noqa: E402


COMMANDS = [
    ["--version"],
    ["create", "--help"],
    ["list", "--help"],
    ["info", "--help"],
    ["edit", "--help"],
    ["logs", "--help"],
    ["enable", "--help"],
    ["disable", "--help"],
    ["remove", "--help"],
    ["clone", "--help"],
    ["maintenance", "--help"],
    ["reload", "--help"],
    ["restart", "--help"],
    ["status", "--help"],
    ["test", "--help"],
    ["doctor", "--help"],
    ["backup", "--help"],
    ["backups", "--help"],
    ["inspect", "--help"],
    ["verify", "--help"],
    ["restore", "--help"],
    ["cert", "--help"],
    ["cert", "list", "--help"],
    ["cert", "renew", "--help"],
    ["cert", "revoke", "--help"],
    ["cert", "self-sign", "--help"],
    ["cert", "upload", "--help"],
    ["audit", "--help"],
    ["tls", "--help"],
    ["hsts", "--help"],
    ["botblock", "--help"],
    ["geoip", "--help"],
    ["fail2ban", "--help"],
    ["modsec", "--help"],
    ["waf", "--help"],
    ["metrics", "--help"],
    ["stats", "--help"],
    ["healthz", "--help"],
    ["php", "--help"],
    ["preset", "--help"],
    ["preset", "wordpress", "--help"],
    ["preset", "laravel", "--help"],
    ["preset", "node", "--help"],
    ["preset", "static", "--help"],
    ["cluster", "--help"],
    ["cluster", "add", "--help"],
    ["cluster", "deploy", "--help"],
    ["dashboard", "--help"],
    ["update", "--help"],
    ["update", "check", "--help"],
    ["update", "install", "--help"],
    ["update", "rollback", "--help"],
    ["update", "snapshots", "--help"],
    ["self-update", "--help"],
    ["uninstall", "--help"],
]


def main() -> int:
    parser = easy_main.build_parser()
    print("EasyNginx CLI surface tests")
    failures = 0
    sink = io.StringIO()  # capture --help output so it doesn't spam the terminal
    for argv in COMMANDS:
        try:
            with redirect_stdout(sink), redirect_stderr(sink):
                parser.parse_args(argv)
        except SystemExit as exc:
            # --help and --version exit with 0; that's expected.
            if exc.code != 0:
                print(f"  FAIL {' '.join(argv)} -> exit {exc.code}")
                failures += 1
            else:
                print(f"  ok   {' '.join(argv)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {' '.join(argv)} -> {type(exc).__name__}: {exc}")
            failures += 1

    if failures:
        print(f"\n{failures} commands failed to parse.")
        return 1
    print(f"\nAll {len(COMMANDS)} commands parse cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
