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

```bash
# 1. Levantar PostgreSQL + pgAdmin (desde la raíz del repo)
docker-compose up -d

# 2. Entorno virtual compartido (desde la raíz del repo)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Por cada proyecto (FonoApp/ y FonoAppPortalMedico/):
cd FonoApp   # o FonoAppPortalMedico
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Detalle completo de cada paso, variables de entorno y convenciones de código en la documentación
de cada proyecto (tabla de arriba).
