# Backend_Fono

Backend de la plataforma FonoApp: dos proyectos Django independientes que comparten una misma
base de datos.

| Proyecto | Qué es | Documentación |
|---|---|---|
| [`FonoApp/`](FonoApp/) | API pública del portal + panel de administradores | [`FonoApp/DOCUMENTACION.md`](FonoApp/DOCUMENTACION.md) |
| [`FonoAppPortalMedico/`](FonoAppPortalMedico/) | Portal médico: registro/acreditación de fonoaudiólogos, pacientes, citas y videos de síntomas | [`FonoAppPortalMedico/DOCUMENTACION.md`](FonoAppPortalMedico/DOCUMENTACION.md) |

Para desplegar a producción (hosting, automatización con GitHub Actions, migración de la base de
datos de PostgreSQL a MySQL), ver [`DOCUMENTACION_DESPLIEGUE.md`](DOCUMENTACION_DESPLIEGUE.md) —
los archivos listos para ese despliegue viven en la carpeta aislada [`deploy/`](deploy/README.md).

## Puesta en marcha rápida (desarrollo local)

Las variables de entorno de desarrollo local están **centralizadas en un único `.env` en la raíz
del repo** (junto a este README): tanto `FonoApp/` como `FonoAppPortalMedico/` lo leen (comparten
base de datos y `SECRET_KEY`, ver `.env.example`). Por defecto apunta a la BDD MySQL "develop"
compartida — no requiere levantar nada localmente.

```bash
# 1. Variables de entorno (desde la raíz del repo)
cp .env.example .env
# completar los valores reales (pedir las credenciales de la BDD develop al equipo)

# 2. Entorno virtual compartido (desde la raíz del repo)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Por cada proyecto (FonoApp/ y FonoAppPortalMedico/):
cd FonoApp   # o FonoAppPortalMedico
python manage.py migrate
python manage.py runserver
```

`docker-compose.yml` (PostgreSQL + pgAdmin) queda disponible como alternativa si en vez de la BDD
develop compartida prefieres una base local propia: en ese caso, `docker-compose up -d` y define
`DB_ENGINE=postgresql` con las variables `DB_*` (en vez de `DATABASE_URL`) en el `.env` de la raíz.

Detalle completo de cada paso, variables de entorno y convenciones de código en la documentación
de cada proyecto (tabla de arriba).
