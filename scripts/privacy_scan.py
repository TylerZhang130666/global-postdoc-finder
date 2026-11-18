#!/usr/bin/env python3
"""Flag common personal-data patterns before publication."""
import argparse, re
from datetime import date
from pathlib import Path
SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".toml", ".html", ".xml"}
PATTERNS = {
    "email": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "phone-like": re.compile(r"(?<!\w)(?:\+?\d[\d .()\-]{7,}\d)(?!\w)"),
    "Windows path": re.compile(r"(?i)\b[A-Z]:\\(?:[^\s<>:\"|?*]+\\)*[^\s<>:\"|?*]*"),
    "home path": re.compile(r"/(?:home|Users)/[^/\s]+"),
    "ORCID-like ID": re.compile(r"\b\d{4}-\d{4}-\d{4}-[\dX]{4}\b"),
}

ISO_DATE = re.compile(r"(?<![+\w])\d{4}-\d{2}-\d{2}(?![\d-])")
PUBLIC_JOB_URL = re.compile(r'https://(?:postdocs\.yale\.edu/posts/|jobs\.csiro\.au/job/)[^\s<>"\'?]+')
SVG_VIEWBOX = re.compile(r'viewBox="[\d.\s-]+"', re.I)

def phone_scan_text(line: str) -> str:
    """Avoid reporting valid ISO calendar dates as phone numbers."""
    def replace_date(match):
        try: date.fromisoformat(match.group())
        except ValueError: return match.group()
        return " " * len(match.group())
    # Only these published job-path patterns are exempt, never URL query data,
    # credentials, other hosts or phone/email text outside the URL.
    line = PUBLIC_JOB_URL.sub(lambda m: ' ' * len(m.group()), line)
    line = SVG_VIEWBOX.sub(lambda m: ' ' * len(m.group()), line)
    if re.match(r'^\s*"title"\s*:',line):
        # Recruitment cohort years in a JSON title are not a telephone number.
        def cohort(match):
            start,end=map(int,match.groups())
            return ' '*len(match.group()) if 1900<=start<=end<=2100 and end-start<=4 else match.group()
        line=re.sub(r'\b((?:19|20)\d{2})\s+-\s+((?:19|20)\d{2})\b',cohort,line)
    return ISO_DATE.sub(replace_date, line)
def scan(root: Path) -> int:
    findings = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES: continue
        try: lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            print(f"WARN non-UTF-8: {path.relative_to(root)}"); findings += 1; continue
        for number, line in enumerate(lines, 1):
            for label, pattern in PATTERNS.items():
                searchable = phone_scan_text(line) if label == "phone-like" else line
                if pattern.search(searchable): print(f"{path.relative_to(root)}:{number}: {label}"); findings += 1
    print(f"Found {findings} potential issue(s)." if findings else "No common patterns found; review manually.")
    return 1 if findings else 0
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("root", nargs="?", default=".", type=Path)
    raise SystemExit(scan(parser.parse_args().root.resolve()))
