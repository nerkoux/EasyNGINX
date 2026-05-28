#!/usr/bin/env python3
"""EasyNginx CLI entry point.

Subcommands:
    create-host                       Interactive site creation (default).
    create-host list                  List managed sites.
    create-host enable  <domain>      Enable a previously-disabled site.
    create-host disable <domain>      Disable a site without deleting it.
    create-host remove  <domain>      Remove site config and SSL hooks.
    create-host renew                 Force certbot renew + nginx reload.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow `python3 main.py` invocations where lib/ is the script dir.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui import Console  # noqa: E402
from config import load_config  # noqa: E402
import commands  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="create-host",
        description="EasyNginx — beginner-friendly nginx virtual host manager.",
    )
    sub = p.add_subparsers(dest="command")

    create = sub.add_parser("create", help="Create a new virtual host (default).")
    create.add_argument("--domain")
    create.add_argument(
        "--type",
        choices=["reverse-proxy", "static", "php", "websocket", "redirect", "load-balancer"],
    )
    create.add_argument("--upstream", help="Backend URL for proxy/websocket.")
    create.add_argument("--upstreams", help="Comma-separated upstreams for load balancer.")
    create.add_argument("--root", help="Document root for static or PHP.")
    create.add_argument("--redirect-to", help="Target URL for redirect-only sites.")
    create.add_argument("--ssl", action="store_true")
    create.add_argument("--no-ssl", action="store_true")
    create.add_argument("--email")
    create.add_argument("--http2", dest="http2", action="store_true", default=None)
    create.add_argument("--no-http2", dest="http2", action="store_false")
    create.add_argument("--gzip", dest="gzip", action="store_true", default=None)
    create.add_argument("--no-gzip", dest="gzip", action="store_false")
    create.add_argument("--security-headers", dest="security_headers",
                        action="store_true", default=None)
    create.add_argument("--no-security-headers", dest="security_headers", action="store_false")
    create.add_argument("--rate-limit", action="store_true", default=False)
    create.add_argument("--basic-auth", help="username:password (will be hashed).")
    create.add_argument("--staging", action="store_true",
                        help="Use Let's Encrypt staging server.")
    create.add_argument("-y", "--yes", action="store_true",
                        help="Assume yes for confirmations.")

    sub.add_parser("list", help="List EasyNginx-managed sites.")

    en = sub.add_parser("enable", help="Enable a site.")
    en.add_argument("domain")

    dis = sub.add_parser("disable", help="Disable a site.")
    dis.add_argument("domain")

    rm = sub.add_parser("remove", help="Remove a site.")
    rm.add_argument("domain")
    rm.add_argument("-y", "--yes", action="store_true")

    sub.add_parser("renew", help="Run certbot renew and reload nginx.")
    sub.add_parser("doctor", help="Run environment diagnostics.")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    try:
        cfg = load_config()
    except FileNotFoundError as exc:
        console.error(str(exc))
        return 2

    cmd = args.command or "create"

    try:
        if cmd == "create":
            return commands.cmd_create(args, cfg, console)
        if cmd == "list":
            return commands.cmd_list(cfg, console)
        if cmd == "enable":
            return commands.cmd_enable(args.domain, cfg, console)
        if cmd == "disable":
            return commands.cmd_disable(args.domain, cfg, console)
        if cmd == "remove":
            return commands.cmd_remove(args.domain, cfg, console, assume_yes=args.yes)
        if cmd == "renew":
            return commands.cmd_renew(cfg, console)
        if cmd == "doctor":
            return commands.cmd_doctor(cfg, console)
    except KeyboardInterrupt:
        console.warn("Interrupted.")
        return 130
    except commands.EasyNginxError as exc:
        console.error(str(exc))
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
