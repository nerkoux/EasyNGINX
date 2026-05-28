"""Cert lifecycle commands."""

from __future__ import annotations

import argparse
import datetime as _dt
import shutil
import subprocess
from pathlib import Path

import certbot
import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from helpers import run
from ui import Console

LE_LIVE = Path("/etc/letsencrypt/live")
EZ_CERT_DIR = Path("/etc/easynginx/certs")


def _list_letsencrypt_certs() -> list[dict]:
    out = []
    if not LE_LIVE.is_dir():
        return out
    for d in sorted(LE_LIVE.iterdir()):
        if not d.is_dir():
            continue
        cert = d / "fullchain.pem"
        if not cert.exists():
            continue
        rc, output = run(["openssl", "x509", "-noout", "-enddate", "-subject", "-in", str(cert)])
        info = {"name": d.name, "path": str(cert)}
        if rc == 0:
            for line in output.splitlines():
                if line.startswith("notAfter="):
                    raw = line.split("=", 1)[1]
                    try:
                        dt = _dt.datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z")
                        info["expires"] = dt.isoformat()
                        info["days_left"] = (dt - _dt.datetime.utcnow()).days
                    except ValueError:
                        pass
                if line.startswith("subject="):
                    info["subject"] = line.split("=", 1)[1].strip()
        out.append(info)
    return out


def _color_days(console: Console, days: int | None) -> str:
    if days is None:
        return "?"
    if days < 0:
        return f"{console._c['red']}EXPIRED ({days}d){console._c['reset']}"
    if days < 14:
        return f"{console._c['red']}{days}d{console._c['reset']}"
    if days < 30:
        return f"{console._c['yellow']}{days}d{console._c['reset']}"
    return f"{console._c['green']}{days}d{console._c['reset']}"


def cmd_list(cfg: Config, console: Console) -> int:
    certs = _list_letsencrypt_certs()
    if not certs:
        console.info("No Let's Encrypt certificates found.")
        return 0
    console.header("Certificates")
    for c in certs:
        days = c.get("days_left")
        print(f"  • {c['name']:<35} expires {c.get('expires', '?')}  ({_color_days(console, days)})")
        if c.get("subject"):
            console.hint(c["subject"])
    return 0


def cmd_renew(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    if not certbot.is_available():
        raise EasyNginxError("certbot is not installed.")
    if args.domain:
        cmd = ["certbot", "renew", "--cert-name", args.domain, "--no-random-sleep-on-renew"]
        if args.force:
            cmd.append("--force-renewal")
    else:
        cmd = ["certbot", "renew", "--quiet"]
        if args.force:
            cmd.append("--force-renewal")
    rc, output = run(cmd)
    if output:
        for line in output.splitlines():
            console.hint(line)
    if rc:
        raise EasyNginxError("certbot renew failed.")
    nginx_mod.reload_nginx()
    console.ok("Renewal complete and nginx reloaded.")
    return 0


def cmd_renew_all(cfg: Config, console: Console) -> int:
    """Plain `easynginx renew` — convenience alias."""
    args = argparse.Namespace(domain=None, force=False)
    return cmd_renew(args, cfg, console)


def cmd_revoke(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    cert_path = LE_LIVE / args.domain / "fullchain.pem"
    if not cert_path.exists():
        raise EasyNginxError(f"No certificate found for {args.domain} at {cert_path}.")
    if not args.yes and not console.confirm(
        f"Revoke certificate for {args.domain}?", default=False
    ):
        return 0
    rc, output = run([
        "certbot", "revoke",
        "--cert-name", args.domain,
        "--reason", args.reason,
        "--no-delete-after-revoke",
        "-n",
    ])
    if rc:
        for line in output.splitlines():
            console.hint(line)
        raise EasyNginxError("certbot revoke failed.")
    console.ok(f"Revoked {args.domain}.")
    return 0


def cmd_self_sign(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    if not shutil.which("openssl"):
        raise EasyNginxError("openssl is required for self-signed certs.")

    EZ_CERT_DIR.mkdir(parents=True, exist_ok=True)
    target = EZ_CERT_DIR / args.domain
    target.mkdir(exist_ok=True)
    key = target / "privkey.pem"
    crt = target / "fullchain.pem"

    rc, output = run([
        "openssl", "req", "-x509", "-nodes",
        "-newkey", "rsa:2048",
        "-keyout", str(key),
        "-out", str(crt),
        "-days", str(args.days),
        "-subj", f"/CN={args.domain}",
        "-addext", f"subjectAltName=DNS:{args.domain}",
    ])
    if rc:
        raise EasyNginxError(f"openssl failed: {output}")

    key.chmod(0o600)
    crt.chmod(0o644)
    console.ok(f"Self-signed cert for {args.domain} → {crt}")
    console.hint(f"Private key: {key}")

    if args.apply:
        return _apply_cert_to_site(args.domain, crt, key, cfg, console)
    return 0


def cmd_upload(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    cert_src = Path(args.cert)
    key_src = Path(args.key)
    if not cert_src.exists() or not key_src.exists():
        raise EasyNginxError("Both --cert and --key must point at existing files.")

    EZ_CERT_DIR.mkdir(parents=True, exist_ok=True)
    target = EZ_CERT_DIR / args.domain
    target.mkdir(exist_ok=True)
    crt = target / "fullchain.pem"
    key = target / "privkey.pem"
    shutil.copy2(cert_src, crt)
    shutil.copy2(key_src, key)
    crt.chmod(0o644)
    key.chmod(0o600)
    console.ok(f"Installed cert + key for {args.domain} into {target}.")

    if args.apply:
        return _apply_cert_to_site(args.domain, crt, key, cfg, console)
    return 0


def _apply_cert_to_site(domain: str, crt: Path, key: Path,
                        cfg: Config, console: Console) -> int:
    files = nginx_mod.site_paths(domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No site config for {domain}; create it first.")
    text = files.available.read_text()

    # Drop existing ssl directives we control.
    import re
    text = re.sub(r"^\s*ssl_certificate(_key)?\s+[^;]+;\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*listen\s+(\[::\]:)?443[^;]*;\n?", "", text, flags=re.MULTILINE)

    insert = (
        f"    listen 443 ssl http2;\n"
        f"    listen [::]:443 ssl http2;\n"
        f"    ssl_certificate {crt};\n"
        f"    ssl_certificate_key {key};\n"
    )
    # Insert after first "listen 80;" we find.
    text = re.sub(r"(listen\s+80;\s*\n)", rf"\1{insert}", text, count=1)

    files.available.write_text(text, encoding="utf-8")
    ok, output = v.nginx_test()
    if not ok:
        raise EasyNginxError(f"nginx -t failed:\n{output}")
    nginx_mod.reload_nginx()
    console.ok(f"Applied cert to {domain}.")
    return 0


# ---------------------------------------------------------------------------
# Dispatcher for `easynginx cert <action>`
# ---------------------------------------------------------------------------

def dispatch(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "cert_action", None)
    if action == "list" or action is None:
        return cmd_list(cfg, console)
    if action == "renew":
        return cmd_renew(args, cfg, console)
    if action == "revoke":
        return cmd_revoke(args, cfg, console)
    if action == "self-sign":
        return cmd_self_sign(args, cfg, console)
    if action == "upload":
        return cmd_upload(args, cfg, console)
    raise EasyNginxError(f"Unknown cert action: {action}")
