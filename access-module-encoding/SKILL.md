---
name: access-module-encoding
description: Check encoding consistency and mojibake risks for Access/VBA exported modules (.bas/.cls) and related files. Use when asked to review codificacion/encoding issues, to verify UTF-8 vs ANSI, or to detect BOM/UTF-16 problems before importing into Access.
---

# Access Module Encoding

## Quick use

Check encodings:
```bash
python scripts/check_access_module_encoding.py --root C:\Proyectos\gestion-proyectos --extensions .bas .cls
python scripts/check_access_module_encoding.py path\to\File.bas path\to\File.cls
python scripts/check_access_module_encoding.py --strict
```

Normalize to UTF-8 no BOM:
```bash
python scripts/normalize_access_module_encoding.py --root C:\Proyectos\gestion-proyectos --extensions .bas .cls
python scripts/normalize_access_module_encoding.py path\to\File.bas --dry-run
python scripts/normalize_access_module_encoding.py --root C:\Proyectos\gestion-proyectos --extensions .bas .cls --backup
```

## Interpret results

- ascii-only: safe everywhere.
- utf8: UTF-8 without BOM.
- utf8-bom: UTF-8 with BOM (risky for Access import).
- ansi-cp1252: typical Access export.
- utf16-le/utf16-be/binary: treat as problems.

## Normalize notes

- Writes in place; use --dry-run to preview or --backup to keep .bak copies.
- Use --strict to return exit code 1 if a file cannot be converted.