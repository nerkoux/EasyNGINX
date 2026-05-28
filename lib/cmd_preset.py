"""Site presets and PHP-FPM installer."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

import nginx as nginx_mod
import templates as tmpl
import validation as v
from commands import EasyNginxError, _zone_id
from config import Config
from helpers import run, systemctl
from ui import Console


# ---------------------------------------------------------------------------
# PHP install
# ---------------------------------------------------------------------------

PHP_PKG_TEMPLATES = {
    "debian": "php{ver}-fpm",
    "fedora": "php-fpm",
    "rhel":   "php-fpm",
    "arch":   "php-fpm",
    "alpine": "php{ver_short}-fpm",
}


def cmd_php(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "php_action", None)
    if action == "status":
        rc, out = systemctl("status", "php-fpm", "--no-pager")
        if out:
            print(out)
        return rc

    # default: install
    version = getattr(args, "version", "auto")
    family = cfg.distro_family

    pkg_template = PHP_PKG_TEMPLATES.get(family)
    if not pkg_template:
        raise EasyNginxError(f"Automated PHP install isn't wired up for {family}.")

    if version == "auto":
        ver = "8.3"
    else:
        ver = version

    pkg = pkg_template.format(ver=ver, ver_short=ver.replace(".", ""))
    extras = []
    if family == "debian":
        extras = [f"php{ver}-cli", f"php{ver}-mysql", f"php{ver}-curl",
                  f"php{ver}-mbstring", f"php{ver}-xml", f"php{ver}-zip"]
    elif family in ("fedora", "rhel"):
        extras = ["php-cli", "php-mysqlnd", "php-mbstring", "php-xml", "php-zip"]
    elif family == "arch":
        extras = ["php"]

    install_cmd = _install_cmd(family)
    if not install_cmd:
        raise EasyNginxError(f"No package manager wired for {family}.")
    rc, out = run(install_cmd + [pkg, *extras])
    if rc:
        raise EasyNginxError(f"PHP install failed: {out.splitlines()[-3:]}")

    service = "php-fpm" if family != "debian" else f"php{ver}-fpm"
    systemctl("enable", "--now", service)
    console.ok(f"PHP-FPM installed ({pkg}). Service: {service}")
    return 0


def _install_cmd(family: str) -> list[str] | None:
    if family == "debian":
        return ["apt-get", "install", "-y"]
    if family in ("rhel", "fedora"):
        return ["dnf", "install", "-y"]
    if family == "arch":
        return ["pacman", "-S", "--noconfirm", "--needed"]
    if family == "alpine":
        return ["apk", "add", "--no-cache"]
    return None


# ---------------------------------------------------------------------------
# Preset dispatcher
# ---------------------------------------------------------------------------

def dispatch(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "preset_action", None)
    if action == "wordpress":
        return _preset_wordpress(args, cfg, console)
    if action == "laravel":
        return _preset_laravel(args, cfg, console)
    if action == "node":
        return _preset_node(args, cfg, console)
    if action == "static":
        return _preset_static(args, cfg, console)
    raise EasyNginxError(f"Unknown preset: {action}")


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def _detect_php_socket() -> str:
    candidates: list[Path] = []
    for base in (Path("/run/php"), Path("/var/run/php"), Path("/run/php-fpm")):
        if base.is_dir():
            candidates.extend(base.glob("*.sock"))
    for p in (Path("/var/run/php-fpm/www.sock"), Path("/run/php-fpm/www.sock")):
        if p.exists():
            candidates.append(p)
    if not candidates:
        return "/run/php/php-fpm.sock"
    candidates.sort(key=lambda p: p.name)
    return str(candidates[0])


def _ensure_root(domain: str, root: str | None) -> Path:
    target = Path(root) if root else Path(f"/var/www/{domain}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _write_and_validate(domain: str, body: str, cfg: Config, console: Console) -> None:
    nginx_mod.write_site(domain, body, cfg)
    nginx_mod.enable_site(domain, cfg)
    ok, output = v.nginx_test()
    if not ok:
        nginx_mod.remove_site(domain, cfg)
        raise EasyNginxError(f"nginx -t failed:\n{output}")
    nginx_mod.reload_nginx()


def _maybe_issue_cert(domain: str, email: str, console: Console) -> None:
    if not email:
        console.hint("Skipping SSL — pass --email to issue a Let's Encrypt cert.")
        return
    import certbot
    if not certbot.is_available():
        console.warn("certbot is not installed.")
        return
    ok, output = certbot.issue(domain, email)
    if ok:
        console.ok(f"Certificate issued for {domain}.")
    else:
        console.warn("certbot failed; site is live on HTTP.")
        for line in output.splitlines()[-10:]:
            console.hint(line)


# ---------------------------------------------------------------------------
# WordPress preset
# ---------------------------------------------------------------------------

WP_TEMPLATE = """\
# Managed by EasyNginx (preset: wordpress)
server {
    listen 80;
    listen [::]:80;
    server_name {{ domain }};

    root {{ root }};
    index index.php index.html;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 64m;

    location = /favicon.ico { log_not_found off; access_log off; }
    location = /robots.txt  { log_not_found off; access_log off; allow all; }

    # WordPress pretty permalinks
    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \\.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\\.php)(/.+)$;
        fastcgi_pass unix:{{ php_socket }};
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    # Block access to sensitive files
    location ~ /\\.(?!well-known).* { deny all; }
    location ~* /(?:wp-config\\.php|readme\\.html|license\\.txt) { deny all; }
    location ~* /wp-content/uploads/.*\\.php$ { deny all; }

    # Static asset caching
    location ~* \\.(?:css|js|woff2?|ttf|eot|otf|jpe?g|png|gif|svg|webp|ico)$ {
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }
}
"""

def _preset_wordpress(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    root = _ensure_root(args.domain, args.root)
    body = tmpl.render(WP_TEMPLATE, {
        "domain": args.domain,
        "root": str(root),
        "php_socket": _detect_php_socket(),
    })
    _write_and_validate(args.domain, body, cfg, console)
    if args.ssl:
        _maybe_issue_cert(args.domain, args.email, console)
    console.ok(f"WordPress site ready: {args.domain}")
    console.hint(f"Drop WordPress files into {root}.")
    return 0


# ---------------------------------------------------------------------------
# Laravel preset
# ---------------------------------------------------------------------------

LARAVEL_TEMPLATE = """\
# Managed by EasyNginx (preset: laravel)
server {
    listen 80;
    listen [::]:80;
    server_name {{ domain }};

    root {{ root }}/public;
    index index.php index.html;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 64m;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \\.php$ {
        try_files $uri =404;
        fastcgi_split_path_info ^(.+\\.php)(/.+)$;
        fastcgi_pass unix:{{ php_socket }};
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\\.(?!well-known).* { deny all; }

    location ~* \\.(?:css|js|woff2?|ttf|jpe?g|png|gif|svg|webp|ico)$ {
        expires 30d;
        access_log off;
        add_header Cache-Control "public, max-age=2592000, immutable";
    }
}
"""

def _preset_laravel(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    project = Path(args.root)
    if not project.exists():
        raise EasyNginxError(f"Project root does not exist: {project}")
    if not (project / "public").exists():
        raise EasyNginxError(f"{project}/public is missing — is this a Laravel project?")

    storage = project / "storage"
    if storage.exists():
        try:
            shutil.chown(storage, group="www-data")
        except (LookupError, PermissionError, OSError):
            pass
        try:
            os.chmod(storage, 0o775)
        except OSError:
            pass

    body = tmpl.render(LARAVEL_TEMPLATE, {
        "domain": args.domain,
        "root": str(project),
        "php_socket": _detect_php_socket(),
    })
    _write_and_validate(args.domain, body, cfg, console)
    if args.ssl:
        _maybe_issue_cert(args.domain, args.email, console)
    console.ok(f"Laravel site ready: {args.domain}")
    return 0


# ---------------------------------------------------------------------------
# Node.js preset
# ---------------------------------------------------------------------------

NODE_TEMPLATE = """\
# Managed by EasyNginx (preset: node)
server {
    listen 80;
    listen [::]:80;
    server_name {{ domain }};

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    client_max_body_size 25m;

    location / {
        proxy_pass http://127.0.0.1:{{ port }};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
"""

NODE_SERVICE = """\
[Unit]
Description={service_name} (managed by EasyNginx)
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={cwd}
ExecStart={cmd}
Restart=on-failure
RestartSec=5
Environment=NODE_ENV=production
Environment=PORT={port}

[Install]
WantedBy=multi-user.target
"""


def _preset_node(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    if args.port < 1 or args.port > 65535:
        raise EasyNginxError("Port must be 1-65535.")

    body = tmpl.render(NODE_TEMPLATE, {"domain": args.domain, "port": args.port})
    _write_and_validate(args.domain, body, cfg, console)

    if args.service_name and args.service_cmd:
        cwd = args.service_cwd or "/opt"
        unit = NODE_SERVICE.format(
            service_name=args.service_name,
            user=args.service_user,
            cwd=cwd,
            cmd=args.service_cmd,
            port=args.port,
        )
        service_path = Path(f"/etc/systemd/system/{args.service_name}.service")
        service_path.write_text(unit, encoding="utf-8")
        systemctl("daemon-reload")
        systemctl("enable", "--now", args.service_name)
        console.ok(f"Registered systemd service: {args.service_name}")
    else:
        console.hint("Skipped systemd unit — pass --service-name and --service-cmd to register one.")

    if args.ssl:
        _maybe_issue_cert(args.domain, args.email, console)
    console.ok(f"Node.js reverse proxy ready: {args.domain} → :{args.port}")
    return 0


# ---------------------------------------------------------------------------
# Static site preset
# ---------------------------------------------------------------------------

STATIC_TEMPLATE = """\
# Managed by EasyNginx (preset: static / {{ kind }})
server {
    listen 80;
    listen [::]:80;
    server_name {{ domain }};

    root {{ root }};
    index index.html;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    gzip on;
    gzip_comp_level 5;
    gzip_min_length 256;
    gzip_vary on;
    gzip_types
        application/javascript application/json application/xml
        text/css text/plain image/svg+xml;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    {% if spa %}
    location / {
        try_files $uri $uri/ /index.html;
    }
    {% endif %}

    {% if hugo_or_jekyll %}
    location / {
        try_files $uri $uri/ =404;
    }
    {% endif %}

    location ~* \\.(?:css|js|woff2?|ttf|jpe?g|png|gif|svg|webp|ico)$ {
        expires 365d;
        access_log off;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
}
"""

def _preset_static(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)
    root = _ensure_root(args.domain, args.root)
    spa = args.kind in ("nextjs", "html")
    hj = args.kind in ("hugo", "jekyll")
    body = tmpl.render(STATIC_TEMPLATE, {
        "domain": args.domain,
        "root": str(root),
        "kind": args.kind,
        "spa": spa,
        "hugo_or_jekyll": hj,
    })
    _write_and_validate(args.domain, body, cfg, console)
    if args.ssl:
        _maybe_issue_cert(args.domain, args.email, console)
    console.ok(f"Static site ready: {args.domain} ({args.kind})")
    return 0
