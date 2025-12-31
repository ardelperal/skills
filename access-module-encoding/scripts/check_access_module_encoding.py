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


def classify_file(path):
    data = path.read_bytes()
    label, payload = _classify_bytes(data)
    non_ascii = any(b >= 0x80 for b in payload)
    if not non_ascii:
        return "ascii-only", len(data), False, True
    return label, len(data), non_ascii, True


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


def main():
    parser = argparse.ArgumentParser(
        description="Check encoding consistency for Access/VBA modules."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit file paths to scan. If omitted, scan by extension.",
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
        "--strict",
        action="store_true",
        help="Exit 1 if mixed text encodings or problem encodings are found.",
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
        label, size, non_ascii, ok = classify_file(path)
        results.append((path, size, label, non_ascii, ok))

    print("file\tbytes\tclass\tnon_ascii")
    for path, size, label, non_ascii, _ in results:
        print(f"{path}\t{size}\t{label}\t{non_ascii}")

    counts = {}
    for _, _, label, _, _ in results:
        counts[label] = counts.get(label, 0) + 1

    text_encs = set()
    problem = False
    for label in counts:
        if label in ("utf8-bom", "utf8-bom-invalid", "utf16-le", "utf16-be", "binary"):
            problem = True
        if label in ("utf8", "ansi-cp1252"):
            text_encs.add(label)

    mixed_text = len(text_encs) > 1

    print("\nsummary:")
    for label in sorted(counts):
        print(f"{label}\t{counts[label]}")
    print(f"mixed_text_encodings\t{mixed_text}")
    print(f"problem_encodings\t{problem}")

    if args.strict and (mixed_text or problem):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
