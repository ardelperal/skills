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

## Skills privadas

Si el repo es privado, necesitas un token de GitHub:

Windows (PowerShell):
```powershell
setx GITHUB_TOKEN "<token>"
```

Bash:
```bash
export GITHUB_TOKEN="<token>"
```

Instalacion:
```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <owner>/skills --path <nombre-skill>
```

Si el download falla, fuerza git:
```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <owner>/skills --path <nombre-skill> --method git
```

## Plantilla nueva skill

Estructura minima:
```
<nombre-skill>/
  SKILL.md
  scripts/           (opcional)
  references/        (opcional)
  assets/            (opcional)
```

SKILL.md debe incluir frontmatter con name y description.

Despues:
```bash
git add <nombre-skill>
git commit -m "feat: add <nombre-skill> skill"
git push
```