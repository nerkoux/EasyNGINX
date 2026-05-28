"""Top-level command implementations for EasyNginx.

Each function here corresponds to an `easynginx <subcommand>` CLI verb.
The interactive `cmd_create` is the workhorse; everything else manages
existing sites or runs maintenance tasks.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import os
import re
import secrets
import shutil
import subprocess
from base64 import b64encode
from pathlib import Path
from urllib.parse import urlparse

import backup as backup_mod
import certbot
import firewall
import nginx as nginx_mod
import templates as tmpl
import validation as v
from config import Config
from ui import Console


class EasyNginxError(Exception):
    """Raised for user-facing failures."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zone_id(domain: str) -> str:
    """Stable nginx-friendly id from a domain name."""
    return re.sub(r"[^a-z0-9]+", "_", domain.lower()).strip("_") or "site"


def _basic_auth_file(cfg: Config, domain: str) -> Path:
    return cfg.config_dir / "auth" / f"{domain}.htpasswd"


def _write_basic_auth(cfg: Config, domain: str, spec: str) -> Path:
    """Accept user:password and write an apr1-style htpasswd line.

    We use a salted SHA-1 hash (the `{SHA}` scheme) which nginx supports
    everywhere without needing the `htpasswd` binary. Apache's apr1 needs
    OpenSSL gymnastics that aren't worth the dependency here.
    """
    if ":" not in spec:
        raise EasyNginxError("--basic-auth must be in the form user:password.")
    user, password = spec.split(":", 1)
    user = user.strip()
    if not user or not password:
        raise EasyNginxError("Basic auth user and password cannot be empty.")

    digest = hashlib.sha1(password.encode("utf-8")).digest()
    line = f"{user}:{{SHA}}{b64encode(digest).decode('ascii')}\n"

    path = _basic_auth_file(cfg, domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(line, encoding="utf-8")
    path.chmod(0o640)
    return path


def _detect_php_socket() -> str | None:
    """Find a likely PHP-FPM unix socket. Returns None if nothing obvious."""
    candidates: list[Path] = []
    for base in (Path("/run/php"), Path("/var/run/php"), Path("/run/php-fpm")):
        if base.is_dir():
            candidates.extend(base.glob("*.sock"))
    if not candidates:
        for p in (Path("/var/run/php-fpm/www.sock"),
                  Path("/run/php-fpm/www.sock")):
            if p.exists():
                candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.name)
    return str(candidates[0])


def _format_upstream_block(urls: list[str]) -> str:
    lines = []
    for url in urls:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        lines.append(f"    server {host}:{port};")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Interactive site creation
# ---------------------------------------------------------------------------

SITE_TYPES = [
    ("reverse-proxy", "Reverse proxy (Node, Python, Docker apps...)"),
    ("static",        "Static website (HTML/CSS/JS)"),
    ("php",           "PHP site (WordPress, Laravel) via PHP-FPM"),
    ("websocket",     "WebSocket app (Socket.IO, raw ws)"),
    ("redirect",      "Redirect-only (HTTP → HTTPS or domain → domain)"),
    ("load-balancer", "Load balancer across multiple upstreams"),
]


def _gather_inputs(args: argparse.Namespace, cfg: Config, console: Console) -> dict:
    """Resolve every config value, mixing CLI flags with interactive prompts."""

    console.header("EasyNginx — create a new virtual host")

    # Domain
    if args.domain:
        ok, err = v.validate_domain(args.domain)
        if not ok:
            raise EasyNginxError(f"--domain: {err}")
        domain = args.domain.lower().strip().rstrip(".")
    else:
        domain = console.ask(
            "Domain", validator=v.validate_domain
        ).lower().rstrip(".")

    # Refuse duplicates unless overwriting on purpose.
    existing = nginx_mod.site_paths(domain, cfg)
    if existing.available.exists() and not args.yes:
        if not console.confirm(
            f"A config for {domain} already exists. Overwrite?", default=False
        ):
            raise EasyNginxError("Aborted: config already exists for this domain.")

    # Site type
    if args.type:
        site_type = args.type
    else:
        site_type = console.choose("Site type", SITE_TYPES, default_index=0)

    ctx: dict = {
        "domain": domain,
        "site_type": site_type,
        "zone_id": _zone_id(domain),
        "rate_limit": bool(args.rate_limit),
        "gzip": True if args.gzip is None else bool(args.gzip),
        "security_headers": True if args.security_headers is None
                            else bool(args.security_headers),
        "basic_auth": False,
        "basic_auth_file": "",
        "upstream": "",
        "upstreams": [],
        "upstream_block": "",
        "root": "",
        "redirect_to": "",
        "php_socket": "",
    }

    # Type-specific inputs
    if site_type == "reverse-proxy":
        upstream = args.upstream or console.ask(
            "Backend URL (e.g. http://127.0.0.1:3000)",
            validator=v.validate_url,
        )
        ok, err = v.validate_url(upstream)
        if not ok:
            raise EasyNginxError(f"--upstream: {err}")
        ctx["upstream"] = upstream

    elif site_type == "websocket":
        upstream = args.upstream or console.ask(
            "WebSocket backend URL",
            default="http://127.0.0.1:3000",
            validator=v.validate_url,
        )
        ok, err = v.validate_url(upstream)
        if not ok:
            raise EasyNginxError(f"--upstream: {err}")
        ctx["upstream"] = upstream

    elif site_type == "static":
        root = args.root or console.ask(
            "Document root (must exist)",
            default=f"/var/www/{domain}",
            validator=lambda p: v.validate_path(p, must_exist=False),
        )
        Path(root).mkdir(parents=True, exist_ok=True)
        ctx["root"] = root

    elif site_type == "php":
        root = args.root or console.ask(
            "Document root",
            default=f"/var/www/{domain}",
            validator=lambda p: v.validate_path(p, must_exist=False),
        )
        Path(root).mkdir(parents=True, exist_ok=True)
        ctx["root"] = root
        sock = _detect_php_socket()
        ctx["php_socket"] = console.ask(
            "PHP-FPM unix socket",
            default=sock or "/run/php/php-fpm.sock",
            validator=lambda p: v.validate_path(p, must_exist=False),
        )

    elif site_type == "redirect":
        target = args.redirect_to or console.ask(
            "Redirect target (e.g. https://example.com)",
            validator=v.validate_url,
        )
        ok, err = v.validate_url(target)
        if not ok:
            raise EasyNginxError(f"--redirect-to: {err}")
        ctx["redirect_to"] = target.rstrip("/")

    elif site_type == "load-balancer":
        raw = args.upstreams or console.ask(
            "Comma-separated upstream URLs",
            validator=v.validate_upstream_list,
        )
        ok, err = v.validate_upstream_list(raw)
        if not ok:
            raise EasyNginxError(f"--upstreams: {err}")
        urls = [u.strip() for u in raw.split(",") if u.strip()]
        ctx["upstreams"] = urls
        ctx["upstream_block"] = _format_upstream_block(urls)

    # Optional extras (only ask interactively if no flag was given)
    if args.rate_limit is False and args.type is None:
        ctx["rate_limit"] = console.confirm("Enable rate limiting (20r/s)?",
                                            default=False)

    if args.basic_auth:
        path = _write_basic_auth(cfg, domain, args.basic_auth)
        ctx["basic_auth"] = True
        ctx["basic_auth_file"] = str(path)
    elif args.type is None and console.confirm(
        "Protect with basic auth?", default=False
    ):
        user = console.ask("  Username", validator=lambda s: (bool(s.strip()),
                                                              "Required."))
        pw = getpass.getpass("  Password: ")
        if not pw:
            raise EasyNginxError("Password cannot be empty.")
        path = _write_basic_auth(cfg, domain, f"{user}:{pw}")
        ctx["basic_auth"] = True
        ctx["basic_auth_file"] = str(path)

    # SSL
    if args.no_ssl:
        ctx["ssl"] = False
    elif args.ssl:
        ctx["ssl"] = True
    else:
        ctx["ssl"] = console.confirm("Enable HTTPS via Let's Encrypt?",
                                     default=True)

    if ctx["ssl"]:
        if not certbot.is_available():
            console.warn("certbot is not installed; SSL will be skipped.")
            ctx["ssl"] = False
        else:
            email = args.email
            if not email:
                email = console.ask("  Email for Let's Encrypt",
                                    validator=v.validate_email)
            ok, err = v.validate_email(email)
            if not ok:
                raise EasyNginxError(f"--email: {err}")
            ctx["email"] = email
            ctx["ssl_staging"] = bool(args.staging)
    else:
        ctx["email"] = ""
        ctx["ssl_staging"] = False

    return ctx


def _preflight(ctx: dict, cfg: Config, console: Console) -> None:
    """Run safety checks before touching nginx config."""
    console.header("Pre-flight checks")

    domain = ctx["domain"]

    # DNS
    matches, dns_addrs, local_addrs = v.dns_points_here(domain)
    if not dns_addrs:
        console.warn(f"DNS lookup for {domain} returned nothing. "
                     f"SSL issuance will fail until the record exists.")
    elif matches:
        console.ok(f"DNS for {domain} → {', '.join(dns_addrs)} (matches this host)")
    else:
        console.warn(f"DNS for {domain} → {', '.join(dns_addrs)} but this host "
                     f"is {', '.join(local_addrs) or 'unknown'}.")
        console.hint("If you're behind a CDN/proxy this can be fine.")

    # Ports
    if v.port_listening(80):
        console.ok("Port 80 is listening (likely nginx).")
    else:
        if v.port_free(80):
            console.warn("Port 80 is free — nginx may not be running.")
        else:
            console.warn("Port 80 is in use by something else.")

    if ctx.get("ssl"):
        if v.port_listening(443):
            console.ok("Port 443 is listening.")
        elif not v.port_free(443):
            console.warn("Port 443 appears to be in use by another process.")

    # Upstream reachability
    upstream = ctx.get("upstream")
    if upstream:
        if v.upstream_reachable(upstream):
            console.ok(f"Upstream {upstream} is reachable.")
        else:
            console.warn(f"Upstream {upstream} is not reachable yet. "
                         f"Nginx will return 502 until it comes up.")

    for url in ctx.get("upstreams", []):
        if not v.upstream_reachable(url):
            console.warn(f"Upstream {url} is not reachable.")


def _render(ctx: dict, cfg: Config) -> str:
    template_map = {
        "reverse-proxy":  "reverse_proxy.conf",
        "static":         "static_site.conf",
        "php":            "php_site.conf",
        "websocket":      "websocket.conf",
        "redirect":       "redirect.conf",
        "load-balancer":  "load_balancer.conf",
    }
    name = template_map.get(ctx["site_type"])
    if not name:
        raise EasyNginxError(f"Unknown site type: {ctx['site_type']}")
    return tmpl.render_file(cfg.paths.templates / name, ctx)


def cmd_create(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ctx = _gather_inputs(args, cfg, console)
    _preflight(ctx, cfg, console)

    config_text = _render(ctx, cfg)

    console.header("Writing config")
    files = nginx_mod.write_site(ctx["domain"], config_text, cfg)
    console.ok(f"Wrote {files.available}")

    try:
        nginx_mod.enable_site(ctx["domain"], cfg)
        console.ok("Site enabled.")
    except OSError as exc:
        raise EasyNginxError(f"Failed to enable site: {exc}") from exc

    ok, output = v.nginx_test()
    if not ok:
        console.error("nginx -t failed:")
        for line in output.splitlines():
            console.hint(line)
        # Roll back
        nginx_mod.disable_site(ctx["domain"], cfg)
        if files.backup.exists():
            nginx_mod.restore_backup(ctx["domain"], cfg)
            nginx_mod.enable_site(ctx["domain"], cfg)
            console.warn("Restored previous config from backup.")
        else:
            try:
                files.available.unlink(missing_ok=True)  # type: ignore[arg-type]
            except TypeError:
                if files.available.exists():
                    files.available.unlink()
        raise EasyNginxError("Aborted because nginx config failed validation.")

    console.ok("nginx config validated.")

    ok, output = nginx_mod.reload_nginx()
    if not ok:
        console.error("nginx reload failed:")
        for line in output.splitlines():
            console.hint(line)
        raise EasyNginxError("nginx reload failed; investigate before retrying.")
    console.ok("nginx reloaded.")

    # Best-effort firewall reminder.
    if cfg.firewall_tool not in ("none", ""):
        firewall.open_http_https(cfg.firewall_tool)

    # SSL
    if ctx.get("ssl"):
        console.header("Issuing SSL certificate")
        ok, output = certbot.issue(
            ctx["domain"],
            ctx["email"],
            staging=ctx.get("ssl_staging", False),
        )
        if ok:
            console.ok(f"Let's Encrypt certificate issued for {ctx['domain']}.")
        else:
            console.error("certbot failed:")
            for line in output.splitlines()[-15:]:
                console.hint(line)
            console.warn("Site is live on HTTP. Re-run `easynginx create` or "
                         "`certbot --nginx -d <domain>` once DNS is in order.")

    console.header("Done")
    scheme = "https" if ctx.get("ssl") else "http"
    console.ok(f"{ctx['domain']} is live at {scheme}://{ctx['domain']}/")
    return 0


# ---------------------------------------------------------------------------
# Other subcommands
# ---------------------------------------------------------------------------

def cmd_list(cfg: Config, console: Console) -> int:
    sites = nginx_mod.list_sites(cfg)
    if not sites:
        console.info("No sites found.")
        return 0
    console.header("Managed sites")
    for site in sites:
        flags = []
        flags.append("enabled" if site["enabled"] else "disabled")
        if site["has_ssl"]:
            flags.append("ssl")
        print(f"  • {site['domain']:<40} [{', '.join(flags)}]")
        console.hint(site["path"])
    return 0


def cmd_enable(domain: str, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(domain)
    if not ok:
        raise EasyNginxError(err)
    nginx_mod.enable_site(domain, cfg)
    ok, output = v.nginx_test()
    if not ok:
        nginx_mod.disable_site(domain, cfg)
        raise EasyNginxError(f"nginx -t failed after enable:\n{output}")
    nginx_mod.reload_nginx()
    console.ok(f"Enabled {domain}.")
    return 0


def cmd_disable(domain: str, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(domain)
    if not ok:
        raise EasyNginxError(err)
    nginx_mod.disable_site(domain, cfg)
    nginx_mod.reload_nginx()
    console.ok(f"Disabled {domain}.")
    return 0


def cmd_remove(domain: str, cfg: Config, console: Console,
               assume_yes: bool = False) -> int:
    ok, err = v.validate_domain(domain)
    if not ok:
        raise EasyNginxError(err)
    if not assume_yes and not console.confirm(
        f"Remove site {domain}? Files will be deleted.", default=False
    ):
        return 0
    nginx_mod.remove_site(domain, cfg)
    auth_file = _basic_auth_file(cfg, domain)
    if auth_file.exists():
        auth_file.unlink()
    nginx_mod.reload_nginx()
    console.ok(f"Removed {domain}.")
    console.hint("To delete the SSL certificate too: certbot delete --cert-name "
                 f"{domain}")
    return 0


def cmd_renew(cfg: Config, console: Console) -> int:
    if not certbot.is_available():
        raise EasyNginxError("certbot is not installed.")
    console.info("Running certbot renew...")
    ok, output = certbot.renew()
    if output:
        for line in output.splitlines():
            console.hint(line)
    if not ok:
        raise EasyNginxError("certbot renew failed.")
    nginx_mod.reload_nginx()
    console.ok("Renewal complete and nginx reloaded.")
    return 0


def cmd_doctor(cfg: Config, console: Console) -> int:
    console.header("EasyNginx doctor")
    print(f"  distro:        {cfg.distro_id} ({cfg.distro_family})")
    print(f"  package mgr:   {cfg.package_manager}")
    print(f"  firewall:      {cfg.firewall_tool}")
    print(f"  share dir:     {cfg.share_dir}")
    print(f"  templates:     {cfg.paths.templates}")
    print(f"  sites avail:   {cfg.paths.sites_available}")
    print(f"  sites enabled: {cfg.paths.sites_enabled}")

    if shutil.which("nginx"):
        console.ok("nginx is installed.")
    else:
        console.error("nginx is NOT on PATH.")

    if certbot.is_available():
        console.ok("certbot is installed.")
    else:
        console.warn("certbot is missing.")

    ok, output = v.nginx_test()
    if ok:
        console.ok("nginx -t passes.")
    else:
        console.error("nginx -t failed:")
        for line in output.splitlines():
            console.hint(line)

    return 0


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------

def _human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def cmd_backup(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    out_dir = Path(args.output_dir)
    opts = backup_mod.BackupOptions(
        include_ssl=args.include_ssl,
        include_www=args.include_www,
        include_php=args.include_php,
        extra_paths=list(args.include),
        note=args.note,
    )

    console.header("Creating backup")
    try:
        result = backup_mod.create_backup(
            out_dir, options=opts, label=args.label or "manual"
        )
    except FileNotFoundError as exc:
        raise EasyNginxError(str(exc)) from exc

    console.ok(f"Wrote {result.path}")
    console.hint(f"size      : {_human_size(result.size_bytes)}")
    console.hint(f"files     : {result.file_count}")
    console.hint(f"sha256    : {result.sha256}")
    console.hint(f"checksum  : {result.path}.sha256")
    return 0


def cmd_list_backups(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    primary = Path(args.dir)
    found = backup_mod.find_backups([primary] if primary.exists() else None)
    if not found:
        # Fall back to the discovery search across common locations.
        found = backup_mod.find_backups()

    if not found:
        console.info("No backups found.")
        console.hint("Create one with: sudo easynginx backup")
        return 0

    console.header("Available backups")
    for path in found:
        try:
            manifest = backup_mod.inspect_backup(path)
        except backup_mod.RestoreError as exc:
            console.warn(f"{path}: {exc}")
            continue

        size = path.stat().st_size
        host = manifest.get("hostname", "?")
        when = manifest.get("created_at", "?")
        label = manifest.get("label", "")
        files = len(manifest.get("files", []))
        print(f"  • {path}")
        console.hint(f"created : {when}  host: {host}  label: {label}")
        console.hint(f"size    : {_human_size(size)}   files: {files}")
        if manifest.get("note"):
            console.hint(f"note    : {manifest['note']}")
    return 0


def cmd_inspect_backup(archive: str, console: Console) -> int:
    try:
        manifest = backup_mod.inspect_backup(Path(archive))
    except backup_mod.RestoreError as exc:
        raise EasyNginxError(str(exc)) from exc

    console.header(f"Manifest for {archive}")
    print(f"  version    : {manifest.get('version')}")
    print(f"  created    : {manifest.get('created_at')}")
    print(f"  hostname   : {manifest.get('hostname')}")
    print(f"  distro     : {manifest.get('distro_id')} "
          f"({manifest.get('distro_family')})")
    print(f"  label      : {manifest.get('label')}")
    if manifest.get("note"):
        print(f"  note       : {manifest['note']}")

    opts = manifest.get("options", {})
    flags = []
    if opts.get("include_ssl"):  flags.append("ssl")
    if opts.get("include_www"):  flags.append("www")
    if opts.get("include_php"):  flags.append("php")
    print(f"  contents   : {', '.join(flags) or 'core only'}")

    print(f"  targets    : {len(manifest.get('targets', []))} root paths")
    for t in manifest.get("targets", []):
        console.hint(t)
    print(f"  files      : {len(manifest.get('files', []))}")
    return 0


def cmd_verify_backup(archive: str, console: Console) -> int:
    console.header(f"Verifying {archive}")
    try:
        ok, issues = backup_mod.verify_backup(Path(archive))
    except backup_mod.RestoreError as exc:
        raise EasyNginxError(str(exc)) from exc
    if ok:
        console.ok("All checksums match.")
        return 0
    console.error("Verification failed:")
    for line in issues:
        console.hint(line)
    return 1


def _pick_backup_interactive(console: Console) -> Path | None:
    candidates = backup_mod.find_backups()
    if not candidates:
        console.warn("No backups found in the usual locations.")
        manual = console.ask(
            "Path to backup .tar.gz", allow_empty=True,
            validator=lambda s: (Path(s).exists(), "File does not exist."),
        )
        return Path(manual) if manual else None

    console.header("Pick a backup to restore")
    for i, path in enumerate(candidates, 1):
        try:
            mf = backup_mod.inspect_backup(path)
            label = mf.get("label", "")
            when = mf.get("created_at", "?")
            host = mf.get("hostname", "?")
            print(f"  {i}. {path.name}")
            console.hint(f"{when}  host: {host}  label: {label}")
        except backup_mod.RestoreError:
            print(f"  {i}. {path.name}  (manifest unreadable)")
    print(f"  {len(candidates) + 1}. Provide a custom path")

    while True:
        raw = input(f"  Choose [1-{len(candidates) + 1}]: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(candidates):
                return candidates[idx - 1]
            if idx == len(candidates) + 1:
                manual = console.ask(
                    "Path to backup .tar.gz",
                    validator=lambda s: (Path(s).exists(), "File does not exist."),
                )
                return Path(manual)
        console.warn("Invalid selection.")


def cmd_restore(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    archive = Path(args.archive) if args.archive else _pick_backup_interactive(console)
    if not archive:
        console.warn("Restore cancelled.")
        return 0
    if not archive.exists():
        raise EasyNginxError(f"Backup not found: {archive}")

    try:
        manifest = backup_mod.inspect_backup(archive)
    except backup_mod.RestoreError as exc:
        raise EasyNginxError(str(exc)) from exc

    console.header("Restore preview")
    print(f"  archive  : {archive}")
    print(f"  created  : {manifest.get('created_at')}")
    print(f"  hostname : {manifest.get('hostname')}")
    print(f"  distro   : {manifest.get('distro_id')} "
          f"({manifest.get('distro_family')})")
    print(f"  files    : {len(manifest.get('files', []))}")

    if manifest.get("distro_family") and manifest["distro_family"] != cfg.distro_family:
        console.warn(
            f"Backup is from {manifest['distro_family']} but this host is "
            f"{cfg.distro_family}. Paths will be restored as captured."
        )

    if not args.yes and not console.confirm(
        "This will overwrite /etc/nginx and /etc/easynginx (a safety snapshot will be taken first). Continue?",
        default=False,
    ):
        console.warn("Restore cancelled.")
        return 0

    snapshot_dir = cfg.config_dir / "backups" / "snapshots"
    try:
        result = backup_mod.restore_backup(
            archive,
            safety_snapshot_dir=snapshot_dir,
            overwrite=args.overwrite,
            skip_verify=args.skip_verify,
        )
    except backup_mod.RestoreError as exc:
        raise EasyNginxError(str(exc)) from exc

    if result["snapshot_path"]:
        console.ok(f"Pre-restore snapshot saved to {result['snapshot_path']}")

    for top in result["restored"]:
        console.ok(f"Restored {top}")

    # Validate and reload.
    ok, output = v.nginx_test()
    if not ok:
        console.error("nginx -t failed after restore:")
        for line in output.splitlines():
            console.hint(line)
        if result["snapshot_path"]:
            console.warn(
                "Your previous /etc/nginx is preserved at "
                f"{result['snapshot_path']}. Extract it manually if you need to roll back."
            )
        raise EasyNginxError("Restore left nginx in a bad state. Investigate before reloading.")

    console.ok("nginx -t passed.")
    ok, _ = nginx_mod.reload_nginx()
    if ok:
        console.ok("nginx reloaded.")
    else:
        console.warn("nginx reload reported an issue; check 'systemctl status nginx'.")

    console.header("Restore complete")
    return 0
