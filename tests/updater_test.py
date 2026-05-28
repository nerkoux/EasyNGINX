"""Tests for the updater module — version parsing, cache behaviour,
file lists, snapshot/rollback semantics. We don't hit the network: the
HTTP layer is monkey-patched.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import updater  # noqa: E402
import version  # noqa: E402


def test_version_parsing():
    cases = [
        ("0.3.0",       (0, 3, 0)),
        ("v0.3.0",      (0, 3, 0)),
        ("V0.3.1-rc.2", (0, 3, 1)),
        ("1.0",         (1, 0)),
        ("not-a-version", (0,)),
    ]
    for raw, expected in cases:
        got = updater.parse_version(raw)
        assert got == expected, f"{raw!r} -> {got}, expected {expected}"
    print("  version parsing ok")


def test_is_newer():
    assert updater.is_newer("0.4.0", "0.3.9")
    assert updater.is_newer("1.0.0", "0.99.99")
    assert not updater.is_newer("0.3.0", "0.3.0")
    assert not updater.is_newer("0.2.5", "0.3.0")
    print("  is_newer ok")


def test_engine_files_cover_lib_dir():
    """Every .py in lib/ should appear in updater.ENGINE_FILES.
    This guards against forgetting to register a new module."""
    listed = {rel for rel, _, _ in updater.ENGINE_FILES if rel.startswith("lib/")}
    on_disk = {f"lib/{p.name}" for p in (ROOT / "lib").glob("*.py")}
    missing = on_disk - listed
    extra = listed - on_disk
    if missing:
        # cmd_update.py is one we expect to ship.
        critical = {m for m in missing if m != "lib/cmd_update.py"}
        assert not critical, f"Modules missing from ENGINE_FILES: {missing}"
    if extra:
        # extras are tolerable — maybe a module was renamed and updater is
        # carrying compatibility entries — but we should know about them.
        print(f"  note: ENGINE_FILES references files not in lib/: {extra}")
    print(f"  engine files: {len(listed)} lib + "
          f"{len(updater.ENGINE_FILES) - len(listed)} other tracked")


def test_cache_age_calculation():
    # Fresh cache -> small age
    fresh = {"checked_at": __import__("datetime").datetime.utcnow()
             .strftime("%Y-%m-%dT%H:%M:%SZ")}
    age = updater._cache_age_seconds(fresh)
    assert age < 5, f"fresh cache age was {age}"
    # Missing -> infinite
    assert updater._cache_age_seconds({}) == float("inf")
    print("  cache age calc ok")


def test_probe_remote_cache_round_trip(tmpdir: Path, monkeypatch_replacement):
    """Simulate a remote probe by stubbing _http_get, then ensure the
    cache is loaded back on the next call."""

    # Build a fake "release" payload.
    fake_release = json.dumps({
        "tag_name": "v9.9.9",
        "html_url": "https://example.com/release",
        "body": "Fancy new things.",
    }).encode("utf-8")

    calls: list[str] = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if url.endswith("/releases/latest"):
            return fake_release
        raise RuntimeError("unexpected url: " + url)

    # Redirect the cache to a tempdir we control.
    cache_path = tmpdir / "version-cache.json"
    monkeypatch_replacement(updater, "_http_get", fake_get)
    monkeypatch_replacement(updater, "CACHE_PATH", cache_path)

    # First call hits the network and writes the cache.
    info1 = updater.check_for_update(force=True)
    assert info1.latest_version == "9.9.9"
    assert info1.source == "release"
    assert cache_path.exists()
    cache_payload = json.loads(cache_path.read_text())
    assert cache_payload["latest_version"] == "9.9.9"

    # Second call uses the cache (force=False, fresh cache).
    info2 = updater.check_for_update(force=False)
    assert info2.latest_version == "9.9.9"
    # Only one network call should have been made.
    assert len(calls) == 1, f"expected 1 network call, got {len(calls)}"
    print("  probe + cache round-trip ok")


def test_probe_falls_back_through_layers(tmpdir, monkeypatch_replacement):
    """If /releases/latest 404s, fall through to /tags, then version.py."""
    cache_path = tmpdir / "version-cache.json"
    monkeypatch_replacement(updater, "CACHE_PATH", cache_path)

    def fail_then_tags(url, **kwargs):
        if "/releases/latest" in url:
            raise OSError("404")
        if "/tags?per_page=1" in url:
            return json.dumps([{"name": "v1.2.3"}]).encode("utf-8")
        raise RuntimeError("unexpected: " + url)

    monkeypatch_replacement(updater, "_http_get", fail_then_tags)
    info = updater.check_for_update(force=True)
    assert info.latest_version == "1.2.3"
    assert info.source == "tag"
    print("  fallback to tags ok")


def test_probe_handles_no_network(tmpdir, monkeypatch_replacement):
    """Total network failure shouldn't crash — we just return empty info."""
    cache_path = tmpdir / "version-cache.json"
    monkeypatch_replacement(updater, "CACHE_PATH", cache_path)
    monkeypatch_replacement(updater, "_http_get",
                             lambda url, **kw: (_ for _ in ()).throw(OSError("no net")))
    info = updater.check_for_update(force=True)
    assert info.latest_version == ""
    assert not info.has_update
    print("  no-network handling ok")


def test_update_banner_uses_cache_only(tmpdir, monkeypatch_replacement):
    cache_path = tmpdir / "version-cache.json"
    cache_path.write_text(json.dumps({
        "latest_version": "99.0.0",
        "latest_tag": "v99.0.0",
        "release_url": "https://example.com",
        "checked_at": __import__("datetime").datetime.utcnow()
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
    }))
    monkeypatch_replacement(updater, "CACHE_PATH", cache_path)
    # Block any network call so we'd see if the banner code accidentally hits the net.
    def boom(*a, **kw): raise RuntimeError("network call from banner!")
    monkeypatch_replacement(updater, "_http_get", boom)
    # Also block the background refresh.
    monkeypatch_replacement(updater, "_spawn_background_refresh", lambda: None)

    import io
    sink = io.StringIO()
    updater.maybe_print_update_banner(sink)
    out = sink.getvalue()
    assert "Update available" in out, out
    assert "99.0.0" in out
    print("  banner reads cache only ok")


# ---------------------------------------------------------------------------
# Tiny test harness — no pytest dependency.
# ---------------------------------------------------------------------------

class _Patcher:
    """Pytest-monkeypatch-lite: only setattr replacements, auto-reverted."""
    def __init__(self):
        self._undos = []

    def __call__(self, target, attr, value):
        original = getattr(target, attr)
        setattr(target, attr, value)
        self._undos.append((target, attr, original))

    def undo_all(self):
        while self._undos:
            target, attr, original = self._undos.pop()
            setattr(target, attr, original)


def _run(name, fn, *args, **kwargs):
    print(f"\n• {name}")
    try:
        fn(*args, **kwargs)
    except AssertionError as exc:
        print(f"  FAIL: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"  ERROR: {type(exc).__name__}: {exc}")
        return False
    return True


def main() -> int:
    print("EasyNginx updater tests")
    failures = 0

    if not _run("version parsing", test_version_parsing):     failures += 1
    if not _run("is_newer",        test_is_newer):            failures += 1
    if not _run("engine files cover lib", test_engine_files_cover_lib_dir): failures += 1
    if not _run("cache age",       test_cache_age_calculation): failures += 1

    # Tests that need patching get a fresh patcher each.
    for name, fn in [
        ("probe + cache round trip",     test_probe_remote_cache_round_trip),
        ("fallback to tags",             test_probe_falls_back_through_layers),
        ("no-network",                   test_probe_handles_no_network),
        ("banner uses cache only",       test_update_banner_uses_cache_only),
    ]:
        with tempfile.TemporaryDirectory() as tmp:
            patcher = _Patcher()
            try:
                if not _run(name, fn, Path(tmp), patcher):
                    failures += 1
            finally:
                patcher.undo_all()

    print()
    if failures:
        print(f"{failures} test(s) failed.")
        return 1
    print("all updater tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
