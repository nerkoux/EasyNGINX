"""Multi-server orchestration over SSH.

Inventory lives at /etc/easynginx/cluster.yaml. We use a tiny YAML-ish
loader so we don't pull in PyYAML.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import nginx as nginx_mod
import validation as v
from commands import EasyNginxError
from config import Config
from ui import Console


INVENTORY = Path("/etc/easynginx/cluster.yaml")


# ---------------------------------------------------------------------------
# Mini-YAML reader/writer (only supports the subset we use here).
# ---------------------------------------------------------------------------

def _load_inventory() -> list[dict]:
    if not INVENTORY.exists():
        return []
    hosts: list[dict] = []
    current: dict | None = None
    for raw in INVENTORY.read_text().splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("- "):
            if current:
                hosts.append(current)
            current = {}
            rest = line[2:].strip()
            if rest:
                k, _, val = rest.partition(":")
                current[k.strip()] = val.strip().strip('"')
        elif current is not None and line.startswith("  ") and ":" in line:
            k, _, val = line.strip().partition(":")
            current[k.strip()] = val.strip().strip('"')
    if current:
        hosts.append(current)
    return hosts


def _save_inventory(hosts: list[dict]) -> None:
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# EasyNginx cluster inventory"]
    for h in hosts:
        lines.append(f"- name: \"{h['name']}\"")
        for k, v in h.items():
            if k == "name":
                continue
            lines.append(f"  {k}: \"{v}\"")
    INVENTORY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    INVENTORY.chmod(0o600)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _cmd_add(args: argparse.Namespace, console: Console) -> int:
    hosts = _load_inventory()
    if any(h["name"] == args.name for h in hosts):
        raise EasyNginxError(f"Host '{args.name}' already in inventory.")
    entry = {
        "name": args.name,
        "host": args.host,
        "user": args.user,
        "port": str(args.port),
    }
    if args.key:
        entry["key"] = args.key
    hosts.append(entry)
    _save_inventory(hosts)
    console.ok(f"Added {args.name} ({args.user}@{args.host}:{args.port}).")
    return 0


def _cmd_list(console: Console) -> int:
    hosts = _load_inventory()
    if not hosts:
        console.info("Inventory is empty.")
        console.hint("Add a host with: easynginx cluster add <name> <host> --user root")
        return 0
    console.header("Cluster inventory")
    for h in hosts:
        target = f"{h.get('user', 'root')}@{h['host']}:{h.get('port', '22')}"
        print(f"  • {h['name']:<20} {target}")
        if h.get("key"):
            console.hint(f"key: {h['key']}")
    return 0


def _ssh_base(host: dict) -> list[str]:
    cmd = ["ssh",
           "-o", "StrictHostKeyChecking=accept-new",
           "-o", "BatchMode=yes",
           "-p", str(host.get("port", 22))]
    if host.get("key"):
        cmd += ["-i", host["key"]]
    cmd.append(f"{host.get('user', 'root')}@{host['host']}")
    return cmd


def _scp_base(host: dict) -> list[str]:
    cmd = ["scp",
           "-o", "StrictHostKeyChecking=accept-new",
           "-o", "BatchMode=yes",
           "-P", str(host.get("port", 22))]
    if host.get("key"):
        cmd += ["-i", host["key"]]
    return cmd


def _deploy_to_host(host: dict, domain: str, config_text: str,
                    console: Console) -> bool:
    """Copy config to remote, run easynginx test, reload, rollback on failure."""
    console.info(f"→ {host['name']} ({host['host']})")
    if not shutil.which("ssh") or not shutil.which("scp"):
        raise EasyNginxError("ssh/scp are required for cluster deploy.")

    target_user_host = f"{host.get('user', 'root')}@{host['host']}"
    remote_path = f"/etc/nginx/sites-available/{domain}.conf"
    remote_backup = f"/etc/easynginx/backups/{domain}.cluster-prev"

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".conf") as fh:
        fh.write(config_text)
        local_tmp = fh.name

    try:
        # 1. Snapshot remote, if any.
        snap = subprocess.run(
            _ssh_base(host) + [
                f"sudo mkdir -p /etc/easynginx/backups && "
                f"if [ -f {remote_path} ]; then sudo cp {remote_path} {remote_backup}; fi"
            ],
            capture_output=True, text=True,
        )
        if snap.returncode:
            console.warn(f"  remote snapshot failed: {snap.stderr.strip()}")

        # 2. Upload to a temp location, then sudo-move into place.
        scp_target = f"{target_user_host}:/tmp/easynginx-{domain}.conf"
        rc = subprocess.call(_scp_base(host) + [local_tmp, scp_target])
        if rc:
            console.error(f"  scp failed (rc={rc})")
            return False

        # 3. Move into place + symlink + test + reload.
        deploy_cmd = (
            f"sudo mv /tmp/easynginx-{domain}.conf {remote_path} && "
            f"sudo ln -sf {remote_path} /etc/nginx/sites-enabled/{domain}.conf 2>/dev/null || true && "
            f"sudo nginx -t && sudo systemctl reload nginx"
        )
        result = subprocess.run(
            _ssh_base(host) + [deploy_cmd],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            console.error(f"  remote deploy failed; rolling back:")
            for line in (result.stderr or result.stdout).splitlines()[-10:]:
                console.hint(line)
            subprocess.run(
                _ssh_base(host) + [
                    f"if [ -f {remote_backup} ]; then "
                    f"sudo cp {remote_backup} {remote_path} && "
                    f"sudo nginx -t && sudo systemctl reload nginx; "
                    f"else sudo rm -f {remote_path}; fi"
                ],
                capture_output=True, text=True,
            )
            return False
        console.ok(f"  {host['name']} deployed.")
        return True
    finally:
        Path(local_tmp).unlink(missing_ok=True)  # type: ignore[arg-type]


def _cmd_deploy(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    ok, err = v.validate_domain(args.domain)
    if not ok:
        raise EasyNginxError(err)

    files = nginx_mod.site_paths(args.domain, cfg)
    if not files.available.exists():
        raise EasyNginxError(f"No local config for {args.domain}; create it first.")

    config_text = files.available.read_text()
    hosts = _load_inventory()
    if not hosts:
        raise EasyNginxError("Inventory is empty. Use `easynginx cluster add` first.")

    if args.to and args.to != "all":
        wanted = {n.strip() for n in args.to.split(",") if n.strip()}
        targets = [h for h in hosts if h["name"] in wanted]
        missing = wanted - {h["name"] for h in targets}
        if missing:
            raise EasyNginxError(f"Unknown hosts: {', '.join(sorted(missing))}")
    else:
        targets = hosts

    console.header(f"Deploying {args.domain} to {len(targets)} host(s)")
    success = 0
    for host in targets:
        if _deploy_to_host(host, args.domain, config_text, console):
            success += 1

    console.header("Summary")
    if success == len(targets):
        console.ok(f"Deployed to all {success} hosts.")
        return 0
    console.warn(f"{success}/{len(targets)} hosts succeeded.")
    return 1


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch(args: argparse.Namespace, cfg: Config, console: Console) -> int:
    action = getattr(args, "cluster_action", None)
    if action == "add":
        return _cmd_add(args, console)
    if action == "list":
        return _cmd_list(console)
    if action == "deploy":
        return _cmd_deploy(args, cfg, console)
    raise EasyNginxError(f"Unknown cluster action: {action}")
