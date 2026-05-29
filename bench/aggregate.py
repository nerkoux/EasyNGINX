"""Aggregate raw bench CSV into a markdown summary.

Reads results/<stamp>/raw.csv on stdin or as argv[1] and prints a markdown
table to stdout. Reports median wall time, disk added, RSS added, and how
many runs passed for each (target, scenario) cell.
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict


def main(path: str) -> None:
    rows = []
    with open(path, encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)

    targets = sorted({r["target"] for r in rows})
    scenarios = sorted({r["scenario"] for r in rows})

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        grouped[(r["target"], r["scenario"])].append(r)

    print("# Benchmark summary\n")
    print("Median across runs. `n/a` means the tool doesn't support that scenario.\n")

    # Wall time table
    print("## Wall time (seconds)\n")
    header = "| Scenario | " + " | ".join(targets) + " |"
    sep = "|" + "---|" * (len(targets) + 1)
    print(header)
    print(sep)
    for s in scenarios:
        cells = [s]
        for t in targets:
            entries = grouped.get((t, s), [])
            ok_entries = [e for e in entries if e["ok"] == "1"]
            unsupported = any(e["ok"] == "n/a" for e in entries)
            if unsupported and not ok_entries:
                cells.append("n/a")
                continue
            if not ok_entries:
                cells.append("FAIL")
                continue
            secs = [float(e["wall_seconds"]) for e in ok_entries]
            cells.append(f"{statistics.median(secs):.2f}")
        print("| " + " | ".join(cells) + " |")
    print()

    # Disk-added table
    print("## Disk added (KB)\n")
    print(header)
    print(sep)
    for s in scenarios:
        cells = [s]
        for t in targets:
            entries = grouped.get((t, s), [])
            ok_entries = [e for e in entries if e["ok"] == "1"]
            if not ok_entries:
                cells.append("-")
                continue
            disk = [int(e["disk_added_kb"]) for e in ok_entries]
            cells.append(f"{statistics.median(disk)}")
        print("| " + " | ".join(cells) + " |")
    print()

    # RSS table
    print("## RSS added by tool daemons (KB)\n")
    print(header)
    print(sep)
    for s in scenarios:
        if not s.startswith("05"):
            continue
        cells = [s]
        for t in targets:
            entries = grouped.get((t, s), [])
            if not entries:
                cells.append("-")
                continue
            rss = [int(e["rss_added_kb"]) for e in entries if e["ok"] != "0"]
            if not rss:
                cells.append("-")
                continue
            cells.append(f"{statistics.median(rss)}")
        print("| " + " | ".join(cells) + " |")
    print()

    # Pass rates
    print("## Pass rate\n")
    print(header)
    print(sep)
    for s in scenarios:
        cells = [s]
        for t in targets:
            entries = grouped.get((t, s), [])
            if not entries:
                cells.append("-")
                continue
            total = len(entries)
            passed = sum(1 for e in entries if e["ok"] == "1")
            unsupported = any(e["ok"] == "n/a" for e in entries)
            if unsupported:
                cells.append("n/a")
            else:
                cells.append(f"{passed}/{total}")
        print("| " + " | ".join(cells) + " |")
    print()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: aggregate.py <raw.csv>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
