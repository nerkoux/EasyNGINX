"""Smoke test: render every template, ensure validators behave."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import templates as tmpl  # noqa: E402
import validation as v    # noqa: E402


def test_domain_validator():
    cases = [
        ("example.com", True),
        ("api.example.co.uk", True),
        ("*.example.com", True),
        ("invalid_domain", False),
        ("", False),
        ("-bad.com", False),
        ("a" * 250 + ".com", False),
    ]
    for value, expected in cases:
        ok, _ = v.validate_domain(value)
        assert ok is expected, f"{value!r} expected {expected} got {ok}"
    print("  domain validator ok")


def test_email_validator():
    assert v.validate_email("admin@example.com")[0]
    assert not v.validate_email("not-an-email")[0]
    assert not v.validate_email("")[0]
    print("  email validator ok")


def test_url_validator():
    assert v.validate_url("http://127.0.0.1:3000")[0]
    assert v.validate_url("https://example.com")[0]
    assert not v.validate_url("ftp://example.com")[0]
    assert not v.validate_url("nope")[0]
    print("  url validator ok")


def test_template_render():
    tmpls = ROOT / "templates"
    base = {
        "domain": "api.example.com",
        "zone_id": "api_example_com",
        "upstream": "http://127.0.0.1:3000",
        "root": "/var/www/api.example.com",
        "redirect_to": "https://example.com",
        "php_socket": "/run/php/php-fpm.sock",
        "upstreams": ["http://127.0.0.1:3000", "http://127.0.0.1:3001"],
        "upstream_block": "    server 127.0.0.1:3000;\n    server 127.0.0.1:3001;",
        "rate_limit": True,
        "gzip": True,
        "security_headers": True,
        "basic_auth": False,
        "basic_auth_file": "",
    }

    for name in ("reverse_proxy", "static_site", "php_site",
                 "websocket", "redirect", "load_balancer"):
        out = tmpl.render_file(tmpls / f"{name}.conf", base)
        assert "{{" not in out, f"{name}: unrendered variable"
        assert "{%" not in out, f"{name}: unrendered block"
        assert "api.example.com" in out
    print("  template rendering ok")


def test_template_block_falsey():
    out = tmpl.render(
        "{% if gzip %}gzip on;{% endif %}\nserver {}", {"gzip": False}
    )
    assert "gzip on" not in out
    print("  template falsy blocks ok")


def main():
    print("EasyNginx smoke tests")
    test_domain_validator()
    test_email_validator()
    test_url_validator()
    test_template_render()
    test_template_block_falsey()
    print("all smoke tests passed.")


if __name__ == "__main__":
    main()
