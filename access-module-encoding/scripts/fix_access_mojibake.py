#!/usr/bin/env python
import argparse
import json
from pathlib import Path
import sys


SUSPICIOUS_TOKENS = [
    "\u00c3",
    "\u00c2",
    "\u00e2\u20ac",
    "\ufffd",
]

SPANISH_DEFAULTS = {
    "m\ufffdtodo": "m\u00e9todo",
    "S\ufffd": "S\u00ed",
    "ra\ufffdz": "ra\u00edz",
    "edici\ufffdn": "edici\u00f3n",
    "p_A\ufffdo": "p_A\u00f1o",
    "par\ufffdmetro": "par\u00e1metro",
    "Prop\ufffdsito": "Prop\u00f3sito",
    "Par\ufffdmetros": "Par\u00e1metros",
    "seg\ufffdn": "seg\u00fan",
    "jer\ufffdrquico": "jer\u00e1rquico",
    "L\ufffdgica": "L\u00f3gica",
    "M\ufffdxDeIDEdicion": "M\u00e1xDeIDEdicion",
    "conexi\ufffdn": "conexi\u00f3n",
    "Validaci\ufffdn": "Validaci\u00f3n",
    "l\ufffdgica": "l\u00f3gica",
    "publicaci\ufffdn": "publicaci\u00f3n",
    "\ufffdDesea": "\u00bfDesea",
    "acci\ufffdn": "acci\u00f3n",
    "M\ufffdnDeIDEdicion": "M\u00ednDeIDEdicion",
    "jer\ufffdrquica": "jer\u00e1rquica",
    "num\ufffdrico": "num\u00e9rico",
    "par\ufffdmetros": "par\u00e1metros",
    "Construcci\ufffdn": "Construcci\u00f3n",
    "Ejecuci\ufffdn": "Ejecuci\u00f3n",
    "visualizaci\ufffdn": "visualizaci\u00f3n",
    "Nemot\ufffdcnico": "Nemot\u00e9cnico",
    "validaci\ufffdn": "validaci\u00f3n",
    "Telef\ufffdnica": "Telef\u00f3nica",
    "\ufffdrbol": "\u00e1rbol",
    "S\ufffdlo": "S\u00f3lo",
    "a\ufffdo": "a\u00f1o",
    "n\ufffdmero": "n\u00famero",
    "est\ufffd": "est\u00e1",
    "T\ufffdCNICA": "T\u00c9CNICA",
}

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


def encode_text(text, label):
    if label == "ansi-cp1252":
        return text.encode("cp1252")
    if label == "ascii-only":
        return text.encode("ascii")
    return text.encode("utf-8")


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


def mojibake_score(text):
    return sum(text.count(token) for token in SUSPICIOUS_TOKENS)


def fix_utf8_in_cp1252(text):
    try:
        repaired = text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        repaired = None
    if repaired is not None:
        if mojibake_score(repaired) < mojibake_score(text):
            return repaired, True
        return text, False

    lines = text.splitlines(keepends=True)
    new_lines = []
    changed = False
    for line in lines:
        try:
            repaired_line = line.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            new_lines.append(line)
            continue
        if mojibake_score(repaired_line) < mojibake_score(line):
            new_lines.append(repaired_line)
            changed = True
        else:
            new_lines.append(line)
    if not changed:
        return text, False
    repaired = "".join(new_lines)
    if mojibake_score(repaired) < mojibake_score(text):
        return repaired, True
    return text, False


def apply_map(text, mapping):
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


def normalize_file(path, apply, backup, backup_ext, fix_utf8, mapping, apply_map_flag):
    data = path.read_bytes()
    label = classify(data)
    if label in ("binary", "utf8-bom-invalid"):
        return label, "skip", 0, 0
    try:
        text = decode_bytes(data, label)
        if text is None:
            return label, "skip", 0, 0
    except UnicodeDecodeError:
        return label, "decode-error", 0, 0

    before = mojibake_score(text)
    changed = False

    if fix_utf8:
        text, did_fix = fix_utf8_in_cp1252(text)
        changed = changed or did_fix

    if apply_map_flag and mapping:
        mapped = apply_map(text, mapping)
        if mapped != text:
            text = mapped
            changed = True

    after = mojibake_score(text)

    if not changed:
        return label, "ok", before, after

    if not apply:
        return label, "dry-run", before, after

    if backup:
        backup_path = path.with_name(path.name + backup_ext)
        if backup_path.exists():
            return label, "backup-exists", before, after
        backup_path.write_bytes(data)

    path.write_bytes(encode_text(text, label))
    return label, "write", before, after


def main():
    parser = argparse.ArgumentParser(
        description="Detect and fix common mojibake in Access/VBA modules."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit file paths to fix. If omitted, scan by extension.",
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
        "--apply",
        action="store_true",
        help="Write fixes in place (default is dry-run).",
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
        "--no-fix-utf8",
        action="store_true",
        help="Disable utf8-in-cp1252 repair.",
    )
    parser.add_argument(
        "--map",
        help="JSON file with explicit replacements (applied only with --fix-map).",
    )
    parser.add_argument(
        "--fix-map",
        action="store_true",
        help="Apply replacements from --map.",
    )
    parser.add_argument(
        "--spanish-defaults",
        action="store_true",
        help="Apply built-in replacements for common Spanish mojibake.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if a file cannot be processed.",
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

    mapping = {}
    apply_map_flag = False
    if args.spanish_defaults:
        mapping.update(SPANISH_DEFAULTS)
        apply_map_flag = True
    if args.map:
        mapping.update(json.loads(Path(args.map).read_text(encoding="utf-8")))
    if args.fix_map:
        apply_map_flag = True
    if not mapping:
        mapping = None

    results = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            label, action, before, after = normalize_file(
                path,
                args.apply,
                args.backup,
                args.backup_ext,
                not args.no_fix_utf8,
                mapping,
                apply_map_flag,
            )
        except Exception:
            label, action, before, after = "unknown", "error", 0, 0
        results.append((path, path.stat().st_size, label, action, before, after))

    print("file\tbytes\tclass\taction\tmojibake_before\tmojibake_after")
    for path, size, label, action, before, after in results:
        print(f"{path}\t{size}\t{label}\t{action}\t{before}\t{after}")

    class_counts = {}
    action_counts = {}
    for _, _, label, action, _, _ in results:
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
