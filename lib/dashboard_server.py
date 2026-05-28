"""Stdlib-only HTTP server for the EasyNginx dashboard.

Bound to 127.0.0.1:9088. Token auth via X-EasyNginx-Token header or ?token=.
Read-only by design — this exposes inspection endpoints, not mutation,
so a leaked token can't trash your nginx config.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nginx as nginx_mod  # noqa: E402
from config import load_config  # noqa: E402


HOST = "127.0.0.1"
PORT = 9088
TOKEN = os.environ.get("EASYNGINX_DASH_TOKEN", "")


INDEX_HTML = """\
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EasyNginx Dashboard</title>
<style>
  :root { color-scheme: dark; }
  body { font: 14px/1.45 system-ui, sans-serif; margin: 0; padding: 24px;
         background: #0e1114; color: #e6e8ea; }
  h1 { margin: 0 0 16px; font-weight: 600; letter-spacing: -0.01em; }
  .card { background: #1a1f24; border: 1px solid #2a3138; border-radius: 8px;
          padding: 16px 20px; margin-bottom: 16px; }
  .row { display: flex; justify-content: space-between; padding: 8px 0;
         border-bottom: 1px solid #2a3138; }
  .row:last-child { border-bottom: none; }
  .badge { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
  .ok { background: #103324; color: #6ee7a8; }
  .warn { background: #3a2812; color: #f3c180; }
  .err { background: #3a1212; color: #f38080; }
  input { background: #0e1114; color: #e6e8ea; border: 1px solid #2a3138;
          padding: 6px 10px; border-radius: 4px; }
  button { background: #2563eb; color: white; border: 0; padding: 6px 14px;
           border-radius: 4px; cursor: pointer; }
  button:hover { background: #1d4ed8; }
  pre { background: #0a0d10; padding: 12px; border-radius: 4px; overflow: auto; }
  .muted { color: #8b94a0; }
</style>
</head><body>
<h1>EasyNginx</h1>

<div class="card">
  <strong>Auth:</strong> paste your dashboard token, then reload.
  <form onsubmit="event.preventDefault(); localStorage.token = document.getElementById('t').value; load();">
    <input id="t" type="password" placeholder="dashboard token" size="40">
    <button>Save</button>
  </form>
</div>

<div id="overview" class="card"><em class="muted">Loading…</em></div>
<div id="sites" class="card"><em class="muted">Loading…</em></div>
<div id="certs" class="card"><em class="muted">Loading…</em></div>

<script>
async function api(path) {
  const r = await fetch(path, { headers: { 'X-EasyNginx-Token': localStorage.token || '' }});
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

function row(label, value, badge) {
  const b = badge ? ` <span class="badge ${badge.cls}">${badge.text}</span>` : '';
  return `<div class="row"><span>${label}</span><span>${value}${b}</span></div>`;
}

async function load() {
  try {
    const o = await api('/api/overview');
    document.getElementById('overview').innerHTML = `
      <h2 style="margin-top:0;">Overview</h2>
      ${row('hostname', o.hostname)}
      ${row('distro', o.distro)}
      ${row('nginx', o.nginx_running ? 'running' : 'stopped',
            o.nginx_running ? {cls:'ok',text:'ok'} : {cls:'err',text:'down'})}
      ${row('sites', o.site_count)}
      ${row('certs', o.cert_count)}
      ${row('updated', new Date().toLocaleString())}
    `;

    const s = await api('/api/sites');
    document.getElementById('sites').innerHTML = `
      <h2 style="margin-top:0;">Sites (${s.length})</h2>
      ${s.map(x =>
        row(x.domain,
            `<span class="muted">${x.path}</span>`,
            { cls: x.enabled ? 'ok' : 'warn',
              text: x.enabled ? 'enabled' : 'disabled' })
      ).join('')}
    `;

    const c = await api('/api/certs');
    document.getElementById('certs').innerHTML = `
      <h2 style="margin-top:0;">Certificates (${c.length})</h2>
      ${c.map(x => {
        let badge = { cls: 'ok', text: x.days_left + 'd' };
        if (x.days_left < 0) badge = { cls: 'err', text: 'EXPIRED' };
        else if (x.days_left < 14) badge = { cls: 'err', text: x.days_left + 'd' };
        else if (x.days_left < 30) badge = { cls: 'warn', text: x.days_left + 'd' };
        return row(x.name, x.expires || '-', badge);
      }).join('')}
    `;
  } catch (e) {
    document.body.insertAdjacentHTML('afterbegin',
      `<div class="card" style="border-color:#3a1212;background:#1d1213;">${e.message}</div>`);
  }
}
load();
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def _auth_ok(self) -> bool:
        if not TOKEN:
            return False
        sent = self.headers.get("X-EasyNginx-Token", "")
        if sent and sent == TOKEN:
            return True
        qs = parse_qs(urlparse(self.path).query)
        return qs.get("token", [""])[0] == TOKEN

    def _send_json(self, code: int, body) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_html(self, code: int, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            self._send_html(200, INDEX_HTML)
            return

        if not self._auth_ok():
            self._send_json(401, {"error": "missing or invalid token"})
            return

        try:
            cfg = load_config()
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})
            return

        if path == "/api/overview":
            sites = nginx_mod.list_sites(cfg)
            certs = self._certs()
            running = self._nginx_running()
            self._send_json(200, {
                "hostname": os.uname().nodename if hasattr(os, "uname") else "?",
                "distro": f"{cfg.distro_id} ({cfg.distro_family})",
                "nginx_running": running,
                "site_count": len(sites),
                "cert_count": len(certs),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            return

        if path == "/api/sites":
            self._send_json(200, nginx_mod.list_sites(cfg))
            return

        if path == "/api/certs":
            self._send_json(200, self._certs())
            return

        self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args) -> None:  # noqa: N802
        # Keep dashboard logs out of the main nginx error stream.
        sys.stderr.write("[dash] " + (fmt % args) + "\n")

    # ----- helpers ------------------------------------------------------
    def _nginx_running(self) -> bool:
        import subprocess
        try:
            proc = subprocess.run(["systemctl", "is-active", "nginx"],
                                  capture_output=True, text=True, check=False)
            return proc.stdout.strip() == "active"
        except FileNotFoundError:
            return False

    def _certs(self) -> list[dict]:
        import subprocess
        live = Path("/etc/letsencrypt/live")
        out: list[dict] = []
        if not live.is_dir():
            return out
        for d in sorted(live.iterdir()):
            cert = d / "fullchain.pem"
            if not cert.exists():
                continue
            entry: dict = {"name": d.name}
            try:
                proc = subprocess.run(
                    ["openssl", "x509", "-noout", "-enddate", "-in", str(cert)],
                    capture_output=True, text=True, check=False,
                )
                if proc.returncode == 0 and proc.stdout.startswith("notAfter="):
                    raw = proc.stdout.split("=", 1)[1].strip()
                    dt = datetime.strptime(raw, "%b %d %H:%M:%S %Y %Z")
                    entry["expires"] = dt.isoformat()
                    entry["days_left"] = (dt - datetime.utcnow()).days
            except (FileNotFoundError, ValueError):
                pass
            out.append(entry)
        return out


def main() -> int:
    if not TOKEN:
        print("EASYNGINX_DASH_TOKEN must be set.", file=sys.stderr)
        return 1
    server = HTTPServer((HOST, PORT), Handler)
    print(f"EasyNginx dashboard listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
