# Carpeta `deploy/` — artefactos listos para el despliegue en producción

Esta carpeta es **aislada a propósito**: nada de lo que hay acá se aplica solo por existir en el repo.
Es una caja de piezas listas para copiar/pegar cuando decidas activar cada parte. La guía completa
(el "por qué" y el paso a paso) está en [`DOCUMENTACION_DESPLIEGUE.md`](../DOCUMENTACION_DESPLIEGUE.md),
en la raíz del repositorio. Esta carpeta es el complemento práctico de esa guía.

## Qué hay acá

```
deploy/
├── github-actions/
│   ├── deploy.yml           # Workflow recomendado (SSH + rsync). Copiar a .github/workflows/deploy.yml
│   └── deploy-sftp.yml      # Alternativa si V2Networks NO habilita acceso SSH en el plan contratado
├── cpanel/
│   ├── passenger_wsgi.fonoapp.py.example         # Va en la raíz de la app FonoApp dentro de cPanel
│   └── passenger_wsgi.portalmedico.py.example    # Va en la raíz de la app FonoAppPortalMedico dentro de cPanel
├── mysql/
│   ├── requirements-mysql.txt                    # Dependencias a sumar a requirements.txt para usar MySQL
│   ├── db_engine_snippet.py                       # Reemplazo del bloque DATABASES de settings.py (soporta Postgres Y MySQL vía env var)
│   ├── env.production.fonoapp.mysql.example       # Plantilla de variables de entorno de producción (FonoApp) apuntando a MySQL
│   └── env.production.portalmedico.mysql.example  # Igual, para FonoAppPortalMedico
└── scripts/
    ├── migrar_postgres_a_mysql.md    # Procedimiento paso a paso para migrar datos existentes (si algún día hace falta)
    └── crontab_limpiar_videos.txt    # Línea de cron para purgar videos vencidos de PmVideo en el hosting
```

## Orden sugerido de aplicación (cuando llegue el momento)

1. **Contratar y configurar el hosting** (Plan Emprendedor V2Networks): ver `DOCUMENTACION_DESPLIEGUE.md` §2-3.
2. **Pasar la base de datos a MySQL** (ver `DOCUMENTACION_DESPLIEGUE.md` §6):
   - Sumar `deploy/mysql/requirements-mysql.txt` a `requirements.txt`.
   - Reemplazar el bloque `DATABASES` de `FonoApp/FonoApp/settings.py` y `FonoAppPortalMedico/FonoAppPM/settings.py`
     por el contenido de `deploy/mysql/db_engine_snippet.py` (es un *superset* retrocompatible: si no defines
     `DB_ENGINE=mysql`, sigue usando Postgres exactamente igual que hoy — no rompe el entorno de desarrollo actual).
   - Crear las bases MySQL en cPanel y completar `deploy/mysql/env.production.*.mysql.example` con los datos reales
     (luego cargarlas como variables de entorno en "Setup Python App", **no** subir el archivo con valores reales al repo).
3. **Desplegar manualmente una vez en cPanel** ("Setup Python App" + subir código): ver `DOCUMENTACION_DESPLIEGUE.md` §4.
   Usar `deploy/cpanel/passenger_wsgi.*.example` como base para el `passenger_wsgi.py` de cada aplicación.
4. **Activar el cron de limpieza de videos**: pegar `deploy/scripts/crontab_limpiar_videos.txt` en "Cron Jobs" de cPanel.
5. **Automatizar despliegues futuros con GitHub Actions**: copiar `deploy/github-actions/deploy.yml` a
   `.github/workflows/deploy.yml` (o `deploy-sftp.yml` si no hay SSH disponible), y cargar los secrets que pide
   el archivo en GitHub → Settings → Secrets and variables → Actions.

Ningún paso es obligatorio para que el proyecto siga funcionando en desarrollo: todo lo de acá es exclusivamente
para cuando exista un entorno de producción real.
