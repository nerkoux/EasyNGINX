#!/usr/bin/env python3
"""EasyNginx — main CLI dispatcher.

Top-level command structure:

    easynginx create <domain>  list  info  edit  logs  enable  disable
                  remove  clone  maintenance
                  reload  restart  status  test  doctor  renew

    easynginx backup  backups  restore  inspect  verify
    easynginx cert list|renew|revoke|self-sign|upload
    easynginx audit
    easynginx tls <profile>
    easynginx hsts <domain> on|off [--preload]
    easynginx botblock <domain> on|off
    easynginx geoip allow|deny <domain> <CC,...>
    easynginx fail2ban install
    easynginx modsec install
    easynginx waf <domain> on|off
    easynginx metrics enable|disable
    easynginx stats <domain>
    easynginx healthz <domain> on|off
    easynginx php install [--version]
    easynginx preset wordpress|laravel|node|static
    easynginx cluster add|list|deploy
    easynginx dashboard start|stop|status|enable|disable
    easynginx self-update
    easynginx uninstall
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


def _add_create_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--domain")
    p.add_argument(
        "--type",
        choices=["reverse-proxy", "static", "php", "websocket",
                 "redirect", "load-balancer"],
    )
    p.add_argument("--upstream", help="Backend URL for proxy/websocket.")
    p.add_argument("--upstreams", help="Comma-separated upstreams for load balancer.")
    p.add_argument("--root", help="Document root for static or PHP.")
    p.add_argument("--redirect-to", help="Target URL for redirect-only sites.")
    p.add_argument("--alt-names", default="",
                   help="Comma-separated extra SAN names for the cert (e.g. www.example.com).")
    p.add_argument("--ssl", action="store_true")
    p.add_argument("--no-ssl", action="store_true")
    p.add_argument("--email")
    p.add_argument("--http2", dest="http2", action="store_true", default=None)
    p.add_argument("--no-http2", dest="http2", action="store_false")
    p.add_argument("--http3", dest="http3", action="store_true", default=False,
                   help="Enable HTTP/3 (QUIC) directives if nginx supports them.")
    p.add_argument("--gzip", dest="gzip", action="store_true", default=None)
    p.add_argument("--no-gzip", dest="gzip", action="store_false")
    p.add_argument("--brotli", dest="brotli", action="store_true", default=False,
                   help="Enable Brotli (auto-detected; falls back to gzip).")
    p.add_argument("--security-headers", dest="security_headers",
                   action="store_true", default=None)
    p.add_argument("--no-security-headers", dest="security_headers",
                   action="store_false")
    p.add_argument("--rate-limit", action="store_true", default=False)
    p.add_argument("--basic-auth", help="username:password (will be hashed).")
    p.add_argument("--cors", choices=["off", "open", "list"], default="off",
                   help="CORS policy: off (default), open (*), or list.")
    p.add_argument("--cors-origins", default="",
                   help="Comma-separated origins for --cors=list.")
    p.add_argument("--cloudflare", action="store_true", default=False,
                   help="Trust Cloudflare and set real_ip_header CF-Connecting-IP.")
    p.add_argument("--www-redirect", choices=["auto", "to-apex", "to-www", "off"],
                   default="auto",
                   help="How to handle www <-> apex redirects.")
    p.add_argument("--tls-profile", choices=["modern", "intermediate", "legacy"],
                   default="intermediate")
    p.add_argument("--hsts", action="store_true", default=False)
    p.add_argument("--hsts-preload", action="store_true", default=False)
    p.add_argument("--bot-block", action="store_true", default=False)
    p.add_argument("--custom-errors", action="store_true", default=False,
                   help="Drop in branded 404/500 error pages.")
    p.add_argument("--staging", action="store_true",
                   help="Use Let's Encrypt staging server.")
    p.add_argument("--dns-provider", default="",
                   help="DNS plugin name for DNS-01 wildcard (cloudflare, route53, digitalocean).")
    p.add_argument("--dns-credentials", default="",
                   help="Path to credentials file for the DNS plugin.")
    p.add_argument("-y", "--yes", action="store_true",
                   help="Assume yes for confirmations.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="easynginx",
        description="EasyNginx — friendly nginx virtual host manager. "
                    "Run `easynginx --help` to see commands, or "
                    "`easynginx <command> --help` for details.",
    )
    p.add_argument("--version", action="store_true",
                   help="Print EasyNginx version and exit.")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    # ----- Site management (bucket 1) ---------------------------------------
    create = sub.add_parser("create", help="Create a new virtual host (interactive).")
    _add_create_args(create)
    create.add_argument("domain_arg", nargs="?", help="Domain (positional shortcut).")

    sub.add_parser("list", help="List managed sites.")

    info = sub.add_parser("info", help="Show details for a site.")
    info.add_argument("domain")

    edit = sub.add_parser("edit", help="Open a site config in $EDITOR; rollback on validation failure.")
    edit.add_argument("domain")
    edit.add_argument("--editor", default=os.environ.get("EDITOR") or os.environ.get("VISUAL"))

    logs = sub.add_parser("logs", help="Tail access/error logs for a site.")
    logs.add_argument("domain")
    logs.add_argument("-n", "--lines", type=int, default=200,
                      help="How many lines to show before tailing.")
    logs.add_argument("-f", "--follow", action="store_true",
                      help="Follow new lines (default if stdout is a TTY).")
    logs.add_argument("--errors", action="store_true",
                      help="Show error log instead of access log.")
    logs.add_argument("--both", action="store_true",
                      help="Tail both access and error logs.")

    en = sub.add_parser("enable", help="Enable a site.")
    en.add_argument("domain")

    dis = sub.add_parser("disable", help="Disable a site.")
    dis.add_argument("domain")

    rm = sub.add_parser("remove", help="Remove a site.")
    rm.add_argument("domain")
    rm.add_argument("-y", "--yes", action="store_true")
    rm.add_argument("--keep-cert", action="store_true",
                    help="Keep the SSL certificate (default deletes via certbot).")

    clone = sub.add_parser("clone", help="Copy a site config under a new domain.")
    clone.add_argument("source")
    clone.add_argument("destination")
    clone.add_argument("--no-ssl", action="store_true",
                       help="Don't issue a fresh cert for the clone.")

    maint = sub.add_parser("maintenance",
                           help="Toggle maintenance mode for a site (returns 503).")
    maint.add_argument("domain")
    maint.add_argument("state", choices=["on", "off"])
    maint.add_argument("--page", help="Path to a custom HTML maintenance page.")

    sub.add_parser("reload", help="Reload nginx (zero-downtime).")
    sub.add_parser("restart", help="Restart nginx.")
    sub.add_parser("status", help="Show nginx service status.")
    sub.add_parser("test", help="Run nginx -t.")
    sub.add_parser("doctor", help="Run environment diagnostics.")

    # ----- Backup / Restore -------------------------------------------------
    bk = sub.add_parser("backup", help="Create a backup tarball.")
    bk.add_argument("--output-dir", default="/etc/easynginx/backups")
    bk.add_argument("--label", default=None)
    bk.add_argument("--note", default="")
    bk.add_argument("--no-ssl", dest="include_ssl", action="store_false", default=True)
    bk.add_argument("--with-www", dest="include_www", action="store_true", default=False)
    bk.add_argument("--with-php", dest="include_php", action="store_true", default=False)
    bk.add_argument("--include", action="append", default=[], metavar="PATH")

    bl = sub.add_parser("backups", help="List local backups.")
    bl.add_argument("--dir", default="/etc/easynginx/backups")

    insp = sub.add_parser("inspect", help="Show the manifest of a backup.")
    insp.add_argument("archive")

    ver = sub.add_parser("verify", help="Verify checksums inside a backup.")
    ver.add_argument("archive")

    rest = sub.add_parser("restore", help="Restore from a backup tarball.")
    rest.add_argument("archive", nargs="?")
    rest.add_argument("-y", "--yes", action="store_true")
    rest.add_argument("--skip-verify", action="store_true")
    rest.add_argument("--no-overwrite", dest="overwrite", action="store_false", default=True)

    # ----- Certs (bucket 4) -------------------------------------------------
    cert = sub.add_parser("cert", help="SSL certificate lifecycle.")
    cert_sub = cert.add_subparsers(dest="cert_action", metavar="<action>")
    cert_sub.add_parser("list", help="List certs with expiry.")
    cr = cert_sub.add_parser("renew", help="Renew certs (or one specific cert).")
    cr.add_argument("domain", nargs="?")
    cr.add_argument("--force", action="store_true")
    crv = cert_sub.add_parser("revoke", help="Revoke a certificate.")
    crv.add_argument("domain")
    crv.add_argument("--reason", default="unspecified")
    crv.add_argument("-y", "--yes", action="store_true")
    cs = cert_sub.add_parser("self-sign", help="Issue a self-signed cert (dev/local).")
    cs.add_argument("domain")
    cs.add_argument("--days", type=int, default=825)
    cs.add_argument("--apply", action="store_true",
                    help="Wire the cert into the existing site config.")
    cu = cert_sub.add_parser("upload", help="Bring your own cert.")
    cu.add_argument("domain")
    cu.add_argument("--cert", required=True, help="PEM file containing fullchain.")
    cu.add_argument("--key", required=True, help="PEM file containing the private key.")
    cu.add_argument("--apply", action="store_true",
                    help="Wire the cert into the existing site config.")

    sub.add_parser("renew", help="Run certbot renew + nginx reload (alias for `cert renew`).")

    # ----- Security (bucket 3) ---------------------------------------------
    sub.add_parser("audit", help="Scan all sites and report security gaps.")

    tls = sub.add_parser("tls", help="Set the global TLS profile.")
    tls.add_argument("profile", choices=["modern", "intermediate", "legacy"])

    hsts = sub.add_parser("hsts", help="Toggle HSTS for a site.")
    hsts.add_argument("domain")
    hsts.add_argument("state", choices=["on", "off"])
    hsts.add_argument("--preload", action="store_true")

    bb = sub.add_parser("botblock", help="Toggle bad-bot blocking for a site.")
    bb.add_argument("domain")
    bb.add_argument("state", choices=["on", "off"])

    geo = sub.add_parser("geoip", help="GeoIP allow/deny country list for a site.")
    geo.add_argument("action", choices=["allow", "deny", "off"])
    geo.add_argument("domain")
    geo.add_argument("countries", nargs="?", default="",
                     help="Comma-separated 2-letter country codes (e.g. US,CA,GB).")

    f2b = sub.add_parser("fail2ban", help="fail2ban integration.")
    f2b_sub = f2b.add_subparsers(dest="f2b_action", metavar="<action>")
    f2b_sub.add_parser("install", help="Install and configure fail2ban with nginx jails.")
    f2b_sub.add_parser("status", help="Show fail2ban status for nginx jails.")

    mod = sub.add_parser("modsec", help="ModSecurity / OWASP CRS integration.")
    mod_sub = mod.add_subparsers(dest="modsec_action", metavar="<action>")
    mod_sub.add_parser("install", help="Install ModSecurity and CRS.")

    waf = sub.add_parser("waf", help="Toggle ModSecurity WAF for a site.")
    waf.add_argument("domain")
    waf.add_argument("state", choices=["on", "off"])

    # ----- Observability (bucket 6) ----------------------------------------
    metrics = sub.add_parser("metrics", help="Toggle nginx stub_status endpoint.")
    metrics.add_argument("state", choices=["enable", "disable", "status"])

    stats = sub.add_parser("stats", help="Quick stats from a site's access log.")
    stats.add_argument("domain")
    stats.add_argument("--hours", type=int, default=24)

    hz = sub.add_parser("healthz", help="Add or remove a /healthz endpoint for a site.")
    hz.add_argument("domain")
    hz.add_argument("state", choices=["on", "off"])
    hz.add_argument("--upstream", help="If set, healthz proxies to this URL.")

    # ----- Presets (bucket 5) ----------------------------------------------
    php = sub.add_parser("php", help="PHP-FPM management.")
    php_sub = php.add_subparsers(dest="php_action", metavar="<action>")
    pi = php_sub.add_parser("install", help="Install PHP-FPM.")
    pi.add_argument("--version", default="auto",
                    help="PHP version to install (8.1, 8.2, 8.3, or 'auto').")
    php_sub.add_parser("status", help="Show PHP-FPM service status.")

    preset = sub.add_parser("preset", help="One-shot site presets for common stacks.")
    preset_sub = preset.add_subparsers(dest="preset_action", metavar="<stack>")
    pwp = preset_sub.add_parser("wordpress", help="WordPress preset.")
    pwp.add_argument("domain")
    pwp.add_argument("--root", help="Site root (default /var/www/<domain>).")
    pwp.add_argument("--ssl", action="store_true", default=True)
    pwp.add_argument("--email", default="")
    pla = preset_sub.add_parser("laravel", help="Laravel preset.")
    pla.add_argument("domain")
    pla.add_argument("--root", required=True, help="Path to Laravel project (the dir containing public/).")
    pla.add_argument("--ssl", action="store_true", default=True)
    pla.add_argument("--email", default="")
    pno = preset_sub.add_parser("node", help="Node.js reverse proxy preset.")
    pno.add_argument("domain")
    pno.add_argument("--port", type=int, required=True)
    pno.add_argument("--service-name", default="",
                     help="Optional systemd service name to register.")
    pno.add_argument("--service-cmd", default="",
                     help="Command to run for the service (e.g. 'node /opt/app/server.js').")
    pno.add_argument("--service-user", default="www-data")
    pno.add_argument("--service-cwd", default="")
    pno.add_argument("--ssl", action="store_true", default=True)
    pno.add_argument("--email", default="")
    pst = preset_sub.add_parser("static", help="Static site preset.")
    pst.add_argument("domain")
    pst.add_argument("--kind", choices=["nextjs", "hugo", "jekyll", "html"],
                     default="html")
    pst.add_argument("--root", help="Site root (default /var/www/<domain>).")
    pst.add_argument("--ssl", action="store_true", default=True)
    pst.add_argument("--email", default="")

    # ----- Cluster (bucket 8) ----------------------------------------------
    cl = sub.add_parser("cluster", help="Multi-server orchestration.")
    cl_sub = cl.add_subparsers(dest="cluster_action", metavar="<action>")
    cla = cl_sub.add_parser("add", help="Add a host to the cluster inventory.")
    cla.add_argument("name")
    cla.add_argument("host")
    cla.add_argument("--user", default="root")
    cla.add_argument("--port", type=int, default=22)
    cla.add_argument("--key", default="",
                     help="SSH private key path.")
    cl_sub.add_parser("list", help="List inventory.")
    cld = cl_sub.add_parser("deploy", help="Deploy a site to one or more hosts.")
    cld.add_argument("domain")
    cld.add_argument("--to", default="",
                     help="Comma-separated host names (or 'all').")

    # ----- Dashboard (bucket 9) --------------------------------------------
    dash = sub.add_parser("dashboard", help="Local web dashboard.")
    dash.add_argument("action",
                      choices=["start", "stop", "status", "enable", "disable", "token"])

    # ----- Admin (bucket 10) -----------------------------------------------
    upd = sub.add_parser("update", help="Check for and install updates.")
    upd_sub = upd.add_subparsers(dest="update_action", metavar="<action>")
    upd_check = upd_sub.add_parser("check", help="Check for an available update (force a refresh).")
    upd_check.add_argument("--json", action="store_true",
                           help="Print machine-readable JSON output.")
    upd_install = upd_sub.add_parser("install", help="Download and install the update.")
    upd_install.add_argument("--target", default=None,
                             help="Install a specific tag, branch, or sha (e.g. v0.4.0, main).")
    upd_install.add_argument("--force", action="store_true",
                             help="Reinstall even if you're already on the latest version.")
    upd_install.add_argument("-y", "--yes", action="store_true",
                             help="Skip confirmation prompt.")
    upd_sub.add_parser("rollback", help="Restore the previous engine snapshot.")
    upd_sub.add_parser("snapshots", help="List available rollback snapshots.")

    # `self-update` kept as an alias for muscle-memory; maps to update install.
    sub.add_parser("self-update", help="Alias for `easynginx update install`.")
    uninst = sub.add_parser("uninstall", help="Remove EasyNginx (configs preserved).")
    uninst.add_argument("--purge", action="store_true",
                        help="Also delete /etc/easynginx and backups.")
    uninst.add_argument("-y", "--yes", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    console = Console()

    if getattr(args, "version", False):
        from version import __version__ as v
        print(f"easynginx {v}")
        return 0

    # Print a one-line update notice if our cache says there's a newer version.
    # Skipped during update commands so the user isn't told "update available"
    # while actively running the updater.
    if args.command not in ("update", "self-update"):
        try:
            from updater import maybe_print_update_banner
            maybe_print_update_banner()
        except Exception:  # noqa: BLE001
            pass

    try:
        cfg = load_config()
    except FileNotFoundError as exc:
        console.error(str(exc))
        return 2

    cmd = args.command

    if cmd is None:
        parser.print_help()
        return 0

    try:
        # Site management (bucket 1)
        if cmd == "create":
            if getattr(args, "domain_arg", None) and not args.domain:
                args.domain = args.domain_arg
            return commands.cmd_create(args, cfg, console)
        if cmd == "list":   return commands.cmd_list(cfg, console)
        if cmd == "info":   return _import("cmd_site").cmd_info(args.domain, cfg, console)
        if cmd == "edit":   return _import("cmd_site").cmd_edit(args.domain, cfg, console, args.editor)
        if cmd == "logs":   return _import("cmd_site").cmd_logs(args, cfg, console)
        if cmd == "enable": return commands.cmd_enable(args.domain, cfg, console)
        if cmd == "disable":return commands.cmd_disable(args.domain, cfg, console)
        if cmd == "remove": return _import("cmd_site").cmd_remove(args, cfg, console)
        if cmd == "clone":  return _import("cmd_site").cmd_clone(args, cfg, console)
        if cmd == "maintenance":
            return _import("cmd_site").cmd_maintenance(args, cfg, console)

        if cmd == "reload":  return _import("cmd_admin").cmd_reload(console)
        if cmd == "restart": return _import("cmd_admin").cmd_restart(console)
        if cmd == "status":  return _import("cmd_admin").cmd_status(console)
        if cmd == "test":    return _import("cmd_admin").cmd_test(console)
        if cmd == "doctor":  return commands.cmd_doctor(cfg, console)

        # Backup
        if cmd == "backup":  return commands.cmd_backup(args, cfg, console)
        if cmd == "backups": return commands.cmd_list_backups(args, cfg, console)
        if cmd == "inspect": return commands.cmd_inspect_backup(args.archive, console)
        if cmd == "verify":  return commands.cmd_verify_backup(args.archive, console)
        if cmd == "restore": return commands.cmd_restore(args, cfg, console)

        # Certs
        if cmd == "cert":
            return _import("cmd_cert").dispatch(args, cfg, console)
        if cmd == "renew":
            return _import("cmd_cert").cmd_renew_all(cfg, console)

        # Security
        if cmd == "audit":
            return _import("cmd_security").cmd_audit(cfg, console)
        if cmd == "tls":
            return _import("cmd_security").cmd_tls_profile(args.profile, cfg, console)
        if cmd == "hsts":
            return _import("cmd_security").cmd_hsts(args, cfg, console)
        if cmd == "botblock":
            return _import("cmd_security").cmd_botblock(args, cfg, console)
        if cmd == "geoip":
            return _import("cmd_security").cmd_geoip(args, cfg, console)
        if cmd == "fail2ban":
            return _import("cmd_security").cmd_fail2ban(args, cfg, console)
        if cmd == "modsec":
            return _import("cmd_security").cmd_modsec(args, cfg, console)
        if cmd == "waf":
            return _import("cmd_security").cmd_waf(args, cfg, console)

        # Observability
        if cmd == "metrics":
            return _import("cmd_observability").cmd_metrics(args.state, cfg, console)
        if cmd == "stats":
            return _import("cmd_observability").cmd_stats(args, cfg, console)
        if cmd == "healthz":
            return _import("cmd_observability").cmd_healthz(args, cfg, console)

        # Presets
        if cmd == "php":
            return _import("cmd_preset").cmd_php(args, cfg, console)
        if cmd == "preset":
            return _import("cmd_preset").dispatch(args, cfg, console)

        # Cluster
        if cmd == "cluster":
            return _import("cmd_cluster").dispatch(args, cfg, console)

        # Dashboard
        if cmd == "dashboard":
            return _import("cmd_dashboard").dispatch(args, cfg, console)

        # Admin
        if cmd == "update":
            return _import("cmd_update").dispatch(args, cfg, console)
        if cmd == "self-update":
            # Map the legacy command to the new install action.
            args.update_action = "install"
            args.target = None
            args.force = False
            args.yes = False
            return _import("cmd_update").dispatch(args, cfg, console)
        if cmd == "uninstall":
            return _import("cmd_admin").cmd_uninstall(args, cfg, console)

    except KeyboardInterrupt:
        console.warn("Interrupted.")
        return 130
    except commands.EasyNginxError as exc:
        console.error(str(exc))
        return 1

    parser.print_help()
    return 0


def _import(name: str):
    """Import a command module on demand so startup stays fast."""
    return __import__(name)


if __name__ == "__main__":
    sys.exit(main())
