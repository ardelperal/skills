# Skills

Este repo contiene skills para Codex.

## access-module-encoding

Revisa y normaliza la codificacion de modulos Access/VBA (.bas/.cls).

Instalar en otra maquina:
```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo ardelperal/skills --path access-module-encoding
```

Uso rapido:
```bash
# revisar
python ~/.codex/skills/access-module-encoding/scripts/check_access_module_encoding.py \
  --root C:\Proyectos\gestion-proyectos --extensions .bas .cls --strict

# normalizar a UTF-8 sin BOM
python ~/.codex/skills/access-module-encoding/scripts/normalize_access_module_encoding.py \
  --root C:\Proyectos\gestion-proyectos --extensions .bas .cls --backup
```