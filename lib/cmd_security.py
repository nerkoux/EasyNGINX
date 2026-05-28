"""Security & hardening commands."""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from helpers import normalize_country_codes, run, systemctl
from ui import Console


SNIPPETS_DIR = Path("/etc/nginx/easynginx-snippets")
TLS_SNIPPET = SNIPPETS_DIR / "tls.conf"
BOTBLOCK_SNIPPET = SNIPPETS_DIR / "bad-bots.conf"
GEOIP_SNIPPET = SNIPPETS_DIR / "geoip.conf"


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

def cmd_audit(cfg: Config, console: Console) -> int:
    sites = nginx_mod.list_sites(cfg)
    if not sites:
        console.info("No sites to audit.")
        return 0
    console.header("EasyNginx audit")
    issues = 0
    for site in sites:
        domain = site["domain"]
        text = Path(site["path"]).read_text(errors="ignore")
        report: list[str] = []
        if "ssl_certificate" not in text:
            report.append("no SSL configured")
        if "X-Frame-Options" not in text:
            report.append("missing X-Frame-Options header")
        if "X-Content-Type-Options" not in text:
            report.append("missing X-Content-Type-Options header")
        if "Strict-Transport-Security" not in text and site["has_ssl"]:
            report.append("HSTS not enabled (`easynginx hsts %s on`)" % domain)
        if "ssl_protocols" in text and "TLSv1.0" in text:
            report.append("weak protocol TLSv1.0 in config")
        # Walk document root for world-readable .env
        m = re.search(r"^\s*root\s+([^;]+);", text, re.MULTILINE)
        if m:
            doc_root = Path(m.group(1).strip())
            for env in doc_root.glob(".env*"):
                try:
                    mode = stat.S_IMODE(env.stat().st_mode)
                    if mode & 0o004:
                        report.append(f"{env} is world-readable (mode {oct(mode)})")
                except OSError:
                    continue
        # Cert expiry
        cert_match = re.search(r"^\s*ssl_certificate\s+([^;]+);", text, re.MULTILINE)
        if cert_match:
            cert = Path(cert_match.group(1).strip())
            if cert.exists():
                rc, out = run(["openssl", "x509", "-noout", "-enddate", "-in", str(cert)])
                if rc == 0 and out.startswith("notAfter="):
                    try:
                        dt = _dt.datetime.strptime(out.split("=", 1)[1].strip(),
                                                   "%b %d %H:%M:%S %Y %Z")
                        days = (dt - _dt.datetime.utcnow()).days
                        if days < 14:
                            report.append(f"cert expires in {days} days")
                    except ValueError:
                        pass

        if report:
            issues += len(report)
            print(f"  • {domain}")
            for line in report:
                console.hint(line)

    console.header("Summary")
    if issues == 0:
        console.ok("No issues found across managed sites.")
    else:
        console.warn(f"{issues} issue(s) across {len(sites)} site(s).")
    return 0


# ---------------------------------------------------------------------------
# TLS profiles
# ---------------------------------------------------------------------------

TLS_PROFILES = {
    "modern": """
ssl_protocols TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:EZ_SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
""".strip(),
    "intermediate": """
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:EZ_SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
""".strip(),
    "legacy": """
ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5:!EXPORT:!DES;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:EZ_SSL:10m;
ssl_session_timeout 1d;
""".strip(),
}


def cmd_tls_profile(profile: str, cfg: Config, console: Console) -> int:
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    body = TLS_PROFILES[profile]
    TLS_SNIPPET.write_text(
        f"# EasyNginx TLS profile: {profile}\n{body}\n",
        encoding="utf-8",
    )
    # Make sure conf.d-style nginx will include it. Try to add an include
    # line in the http {} block of nginx.conf if it isn't already there.
    nginx_conf = Path("/etc/nginx/nginx.conf")
    if nginx_conf.exists():
        text = nginx_conf.read_text()
        include_line = f"include {TLS_SNIPPET};"
        if include_line not in text:
            text = re.sub(
                r"(http\s*\{)",
                rf"\1\n    {include_line}",
                text, count=1,
            )
            nginx_conf.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"TLS profile set to '{profile}'.")
    return 0


# ---------------------------------------------------------------------------
# HSTS toggle
# ---------------------------------------------------------------------------

def cmd_hsts(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config for {args.domain}.")
    text = files.available.read_text()
    text = re.sub(r"^\s*add_header\s+Strict-Transport-Security[^;]+;\n?",
                  "", text, flags=re.MULTILINE)

    if args.state == "on":
        if args.preload:
            console.warn("Preload requires submitting your domain at hstspreload.org "
                         "and is permanent. Make sure ALL subdomains can serve HTTPS.")
            value = '"max-age=63072000; includeSubDomains; preload"'
        else:
            value = '"max-age=31536000; includeSubDomains"'
        injection = f"    add_header Strict-Transport-Security {value} always;\n"
        # Insert near other add_header lines if any, else just before closing brace.
        if "add_header" in text:
            text = re.sub(r"(add_header[^\n]+\n)", rf"\1{injection}", text, count=1)
        else:
            idx = text.rfind("}")
            text = text[:idx] + injection + text[idx:]

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"HSTS {args.state} for {args.domain}.")
    return 0


# ---------------------------------------------------------------------------
# Bot blocker
# ---------------------------------------------------------------------------

BAD_BOTS = [
    "AhrefsBot", "SemrushBot", "MJ12bot", "DotBot", "BLEXBot",
    "PetalBot", "SeznamBot", "SerendeputyBot", "Bytespider",
    "DataForSeoBot", "ZoominfoBot", "ClaudeBot", "GPTBot",
]


def _ensure_botblock_snippet() -> None:
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    if BOTBLOCK_SNIPPET.exists():
        return
    pattern = "|".join(re.escape(b) for b in BAD_BOTS)
    BOTBLOCK_SNIPPET.write_text(
        "# EasyNginx bad-bot blocklist\n"
        "map $http_user_agent $easynginx_bad_bot {\n"
        "    default 0;\n"
        f"    \"~*({pattern})\" 1;\n"
        "}\n",
        encoding="utf-8",
    )
    # Inject the map into http {} block once.
    nginx_conf = Path("/etc/nginx/nginx.conf")
    text = nginx_conf.read_text()
    include_line = f"include {BOTBLOCK_SNIPPET};"
    if include_line not in text:
        text = re.sub(r"(http\s*\{)", rf"\1\n    {include_line}", text, count=1)
        nginx_conf.write_text(text, encoding="utf-8")


def cmd_botblock(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    _ensure_botblock_snippet()
    files = nginx_mod.site_paths(args.domain, cfg)
    text = files.available.read_text()
    marker = "# >>> easynginx-botblock"
    end = "# <<< easynginx-botblock"
    block_re = re.compile(rf"{re.escape(marker)}.*?{re.escape(end)}\n?", re.DOTALL)
    text = block_re.sub("", text)

    if args.state == "on":
        block = (
            f"\n    {marker}\n"
            f"    if ($easynginx_bad_bot) {{ return 403; }}\n"
            f"    {end}\n"
        )
        idx = text.find("location /")
        if idx == -1:
            idx = text.rfind("}")
        text = text[:idx] + block + text[idx:]

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"Bot blocking {args.state} for {args.domain}.")
    return 0


# ---------------------------------------------------------------------------
# GeoIP allow / deny
# ---------------------------------------------------------------------------

def _ensure_geoip_module(console: Console) -> bool:
    """Best-effort hint about GeoIP availability."""
    rc, out = run(["nginx", "-V"])
    if rc != 0:
        return False
    return "geoip2" in out or "ngx_http_geoip2" in out or "--with-http_geoip_module" in out


def cmd_geoip(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    if args.action != "off":
        try:
            codes = normalize_country_codes(args.countries)
        except ValueError as exc:
            raise EasyNginxError(str(exc)) from exc
        if not codes:
            raise EasyNginxError("Provide at least one country code (e.g. US,CA,GB).")
    else:
        codes = []

    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    if not _ensure_geoip_module(console):
        console.warn(
            "Your nginx build doesn't appear to include GeoIP / GeoIP2.\n"
            "      Install the matching nginx module package "
            "(libnginx-mod-http-geoip2 / nginx-module-geoip2) and restart nginx, "
            "or this rule will fail nginx -t."
        )

    files = nginx_mod.site_paths(args.domain, cfg)
    text = files.available.read_text()
    marker = "# >>> easynginx-geoip"
    end = "# <<< easynginx-geoip"
    block_re = re.compile(rf"{re.escape(marker)}.*?{re.escape(end)}\n?", re.DOTALL)
    text = block_re.sub("", text)

    if args.action != "off":
        check = " || ".join(f'$geoip2_data_country_iso_code = "{c}"' for c in codes)
        if args.action == "allow":
            cond = f"if (!({check})) {{ return 403; }}"
        else:
            cond = f"if ({check}) {{ return 403; }}"
        block = f"\n    {marker}\n    {cond}\n    {end}\n"
        idx = text.find("location /")
        if idx == -1:
            idx = text.rfind("}")
        text = text[:idx] + block + text[idx:]

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"GeoIP {args.action} {','.join(codes) or '-'} for {args.domain}.")
    return 0


# ---------------------------------------------------------------------------
# fail2ban
# ---------------------------------------------------------------------------

def _install_pkg(cfg: Config, pkg: str) -> tuple[int, str]:
    if cfg.distro_family in ("debian",):
        return run(["apt-get", "install", "-y", pkg])
    if cfg.distro_family in ("rhel", "fedora"):
        return run(["dnf", "install", "-y", pkg])
    if cfg.distro_family == "arch":
        return run(["pacman", "-S", "--noconfirm", "--needed", pkg])
    if cfg.distro_family == "alpine":
        return run(["apk", "add", "--no-cache", pkg])
    return 1, f"Unsupported distro: {cfg.distro_family}"


F2B_JAILS = """\
# Managed by EasyNginx
[nginx-http-auth]
enabled = true
filter  = nginx-http-auth
port    = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 10m
bantime  = 1h

[nginx-bad-request]
enabled = true
filter  = nginx-bad-request
port    = http,https
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 10m
bantime  = 1h

[nginx-botsearch]
enabled = true
filter  = nginx-botsearch
port    = http,https
logpath = /var/log/nginx/access.log
maxretry = 2
findtime = 10m
bantime  = 6h
"""


def cmd_fail2ban(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "f2b_action", None)
    if action == "status":
        rc, out = run(["fail2ban-client", "status"])
        print(out)
        return rc
    # default: install
    if not shutil.which("fail2ban-client"):
        rc, out = _install_pkg(cfg, "fail2ban")
        if rc:
            raise EasyNginxError(f"Failed to install fail2ban: {out}")

    jail_d = Path("/etc/fail2ban/jail.d")
    jail_d.mkdir(parents=True, exist_ok=True)
    target = jail_d / "easynginx.conf"
    target.write_text(F2B_JAILS, encoding="utf-8")
    target.chmod(0o644)

    rc, out = systemctl("enable", "--now", "fail2ban")
    rc2, out2 = systemctl("restart", "fail2ban")
    if rc and rc2:
        console.warn("Could not start fail2ban via systemctl. Logs:")
        for line in (out + "\n" + out2).splitlines():
            console.hint(line)
    console.ok("fail2ban configured with nginx jails.")
    return 0


# ---------------------------------------------------------------------------
# ModSecurity / OWASP CRS (install + per-site WAF toggle)
# ---------------------------------------------------------------------------

MODSEC_RECIPE_PKG = {
    "debian": ["libnginx-mod-http-modsecurity", "modsecurity-crs"],
    "fedora": ["nginx-module-modsecurity", "modsecurity-crs"],
    "rhel":   ["nginx-module-modsecurity", "modsecurity-crs"],
    "arch":   ["modsecurity-crs"],
}

MODSEC_DIR = Path("/etc/nginx/modsec")


def cmd_modsec(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    pkgs = MODSEC_RECIPE_PKG.get(cfg.distro_family, [])
    if not pkgs:
        raise EasyNginxError(
            "Automated ModSecurity install isn't wired up for this distro. "
            "Install the ModSecurity nginx module manually, then run "
            "`easynginx waf <domain> on`."
        )
    console.info("Installing ModSecurity packages: " + ", ".join(pkgs))
    for p in pkgs:
        rc, out = _install_pkg(cfg, p)
        if rc:
            console.warn(f"Could not install {p}: {out.splitlines()[-1] if out else ''}")

    MODSEC_DIR.mkdir(parents=True, exist_ok=True)
    crs_main = Path("/usr/share/modsecurity-crs/owasp-crs.load")
    main_conf = MODSEC_DIR / "main.conf"
    body = "Include /etc/modsecurity/modsecurity.conf\n"
    if crs_main.exists():
        body += f"Include {crs_main}\n"
    main_conf.write_text(body, encoding="utf-8")
    console.ok(f"Wrote {main_conf}")
    console.hint("Enable per site with: easynginx waf <domain> on")
    return 0


def cmd_waf(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config for {args.domain}.")

    text = files.available.read_text()
    marker = "# >>> easynginx-modsec"
    end = "# <<< easynginx-modsec"
    block_re = re.compile(rf"{re.escape(marker)}.*?{re.escape(end)}\n?", re.DOTALL)
    text = block_re.sub("", text)

    if args.state == "on":
        block = (
            f"\n    {marker}\n"
            f"    modsecurity on;\n"
            f"    modsecurity_rules_file {MODSEC_DIR}/main.conf;\n"
            f"    {end}\n"
        )
        idx = text.find("location /")
        if idx == -1:
            idx = text.rfind("}")
        text = text[:idx] + block + text[idx:]

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed: {output}")
    nginx_mod.reload_nginx()
    console.ok(f"WAF {args.state} for {args.domain}.")
    return 0
