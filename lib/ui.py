"""Tiny console helper — colored output and prompts."""

from __future__ import annotations

import sys


class Console:
    def __init__(self) -> None:
        self.color = sys.stdout.isatty()
        self._c = {
            "reset": "\033[0m" if self.color else "",
            "bold":  "\033[1m" if self.color else "",
            "red":   "\033[31m" if self.color else "",
            "green": "\033[32m" if self.color else "",
            "yellow":"\033[33m" if self.color else "",
            "blue":  "\033[34m" if self.color else "",
            "cyan":  "\033[36m" if self.color else "",
            "dim":   "\033[2m" if self.color else "",
        }

    def _tag(self, color: str, label: str) -> str:
        c = self._c
        return f"{c[color]}[{label}]{c['reset']}"

    def info(self, msg: str) -> None:
        print(f"{self._tag('cyan', 'easynginx')} {msg}")

    def ok(self, msg: str) -> None:
        print(f"{self._tag('green', ' ok ')} {msg}")

    def warn(self, msg: str) -> None:
        print(f"{self._tag('yellow', 'warn')} {msg}")

    def error(self, msg: str) -> None:
        print(f"{self._tag('red', 'err ')} {msg}", file=sys.stderr)

    def hint(self, msg: str) -> None:
        c = self._c
        print(f"{c['dim']}      {msg}{c['reset']}")

    def header(self, title: str) -> None:
        c = self._c
        bar = "─" * max(8, len(title))
        print(f"\n{c['bold']}{title}{c['reset']}\n{c['dim']}{bar}{c['reset']}")

    # ----- prompts -----------------------------------------------------------
    def ask(self, label: str, default: str | None = None,
            validator=None, allow_empty: bool = False) -> str:
        suffix = f" [{default}]" if default else ""
        while True:
            try:
                raw = input(f"  {label}{suffix}: ").strip()
            except EOFError:
                raw = ""
            if not raw and default is not None:
                raw = default
            if not raw and not allow_empty:
                self.warn("This field is required.")
                continue
            if validator:
                ok, err = validator(raw)
                if not ok:
                    self.warn(err or "Invalid input.")
                    continue
            return raw

    def confirm(self, label: str, default: bool = True) -> bool:
        choices = "Y/n" if default else "y/N"
        while True:
            raw = input(f"  {label} [{choices}]: ").strip().lower()
            if not raw:
                return default
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self.warn("Please answer yes or no.")

    def choose(self, label: str, options: list[tuple[str, str]],
               default_index: int = 0) -> str:
        """options: list of (key, description)."""
        print(f"  {label}")
        for i, (key, desc) in enumerate(options, 1):
            print(f"    {i}. {desc}")
        while True:
            raw = input(f"  Choose [1-{len(options)}, default {default_index + 1}]: ").strip()
            if not raw:
                return options[default_index][0]
            if raw.isdigit():
                idx = int(raw)
                if 1 <= idx <= len(options):
                    return options[idx - 1][0]
            for key, _ in options:
                if raw.lower() == key.lower():
                    return key
            self.warn("Invalid selection.")
