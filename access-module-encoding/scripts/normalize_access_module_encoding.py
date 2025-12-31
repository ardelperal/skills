#!/usr/bin/env python
import argparse
from pathlib import Path
import sys


def _classify_bytes(data):
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            data[3:].decode("utf-8")
            return "utf8-bom", data[3:]
        except UnicodeDecodeError:
            return "utf8-bom-invalid", data[3:]
    if data.startswith(b"\xff\xfe"):
        return "utf16-le", data
    if data.startswith(b"\xfe\xff"):
        return "utf16-be", data
    if b"\x00" in data:
        return "binary", data
    try:
        data.decode("utf-8")
        return "utf8", data
    except UnicodeDecodeError:
        return "ansi-cp1252", data


def classify(data):
    label, payload = _classify_bytes(data)
    if label in ("utf8", "ansi-cp1252"):
        if not any(b >= 0x80 for b in payload):
            return "ascii-only"
    return label


def decode_bytes(data, label):
    if label == "utf8":
        return data.decode("utf-8")
    if label == "utf8-bom":
        return data.decode("utf-8-sig")
    if label == "ascii-only":
        return data.decode("ascii")
    if label == "ansi-cp1252":
        return data.decode("cp1252")
    if label in ("utf16-le", "utf16-be"):
        return data.decode("utf-16")
    return None


def gather_files(root, extensions):
    exts = []
    for ext in extensions:
        ext = ext.strip()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        exts.append(ext.lower())
    files = []
    for ext in exts:
        files.extend(root.rglob(f"*{ext}"))
    return sorted(set(files))


def normalize_file(path, dry_run, backup, backup_ext):
    data = path.read_bytes()
    label = classify(data)
    if label in ("binary", "utf8-bom-invalid"):
        return label, "skip"
    try:
        text = decode_bytes(data, label)
        if text is None:
            return label, "skip"
    except UnicodeDecodeError:
        return label, "decode-error"

    new_bytes = text.encode("utf-8")
    if new_bytes == data:
        return label, "ok"
    if dry_run:
        return label, "dry-run"

    if backup:
        backup_path = path.with_name(path.name + backup_ext)
        if backup_path.exists():
            return label, "backup-exists"
        backup_path.write_bytes(data)

    path.write_bytes(new_bytes)
    return label, "write"


def main():
    parser = argparse.ArgumentParser(
        description="Normalize Access/VBA modules to UTF-8 without BOM."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit file paths to normalize. If omitted, scan by extension.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan when no files are provided.",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=[".bas", ".cls"],
        help="Extensions to scan when no files are provided.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak copies before writing.",
    )
    parser.add_argument(
        "--backup-ext",
        default=".bak",
        help="Backup extension (default: .bak).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if a file cannot be converted.",
    )
    args = parser.parse_args()

    if args.files:
        paths = [Path(p) for p in args.files]
    else:
        root = Path(args.root)
        if not root.exists():
            print(f"root-not-found: {root}", file=sys.stderr)
            return 2
        paths = gather_files(root, args.extensions)

    if not paths:
        print("no-files-found", file=sys.stderr)
        return 2

    results = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            label, action = normalize_file(path, args.dry_run, args.backup, args.backup_ext)
        except Exception:
            label, action = "unknown", "error"
        results.append((path, path.stat().st_size, label, action))

    print("file\tbytes\tclass\taction")
    for path, size, label, action in results:
        print(f"{path}\t{size}\t{label}\t{action}")

    class_counts = {}
    action_counts = {}
    for _, _, label, action in results:
        class_counts[label] = class_counts.get(label, 0) + 1
        action_counts[action] = action_counts.get(action, 0) + 1

    print("\nsummary:")
    for label in sorted(class_counts):
        print(f"class_{label}\t{class_counts[label]}")
    for action in sorted(action_counts):
        print(f"action_{action}\t{action_counts[action]}")

    problems = action_counts.get("skip", 0) + action_counts.get("decode-error", 0) + action_counts.get("error", 0)
    if args.strict and problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())