#!/usr/bin/env python3
"""Flag common personal-data patterns before publication."""
import argparse, re
from pathlib import Path
SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".toml"}
PATTERNS = {
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "phone-like": re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)"),
    "Windows path": re.compile(r"(?i)\b[A-Z]:\\(?:[^\s<>:\"|?*]+\\)*[^\s<>:\"|?*]*"),
    "home path": re.compile(r"/(?:home|Users)/[^/\s]+"),
    "ORCID-like ID": re.compile(r"\b\d{4}-\d{4}-\d{4}-[\dX]{4}\b"),
}
def scan(root: Path) -> int:
    findings = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES: continue
        try: lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            print(f"WARN non-UTF-8: {path.relative_to(root)}"); findings += 1; continue
        for number, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line): print(f"{path.relative_to(root)}:{number}: {label}"); findings += 1
    print(f"Found {findings} potential issue(s)." if findings else "No common patterns found; review manually.")
    return 1 if findings else 0
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("root", nargs="?", default=".", type=Path)
    raise SystemExit(scan(parser.parse_args().root.resolve()))
