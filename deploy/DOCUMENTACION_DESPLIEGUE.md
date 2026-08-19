# DOCUMENTACIÓN DE DESPLIEGUE — Backend_Fono

Guía de extremo a extremo para llevar `FonoApp` y `FonoAppPortalMedico` a producción en el
**Plan Emprendedor de [V2Networks](https://v2networks.cl/hosting/)**, automatizar los despliegues
futuros con GitHub Actions, y migrar la base de datos de PostgreSQL a MySQL (requerido por ese
hosting compartido).

> Para las reglas de negocio y el uso de cada API, ver [`FonoApp/DOCUMENTACION.md`](FonoApp/DOCUMENTACION.md)
> y [`FonoAppPortalMedico/DOCUMENTACION.md`](FonoAppPortalMedico/DOCUMENTACION.md). Este documento
> es solo sobre **cómo desplegar**, no sobre qué hace cada endpoint.
>
> Todos los archivos "listos para copiar" que menciona esta guía viven en la carpeta
> aislada [`deploy/`](deploy/README.md) — no se aplican solos, están ahí para cuando decidas
> activarlos.

## Índice

1. [Arquitectura de despliegue](#1-arquitectura-de-despliegue)
2. [El hosting: Plan Emprendedor de V2Networks](#2-el-hosting-plan-emprendedor-de-v2networks)
3. [Antes de empezar: qué preparar](#3-antes-de-empezar-qué-preparar)
4. [Despliegue manual inicial en cPanel](#4-despliegue-manual-inicial-en-cpanel)
5. [Automatizar el despliegue con GitHub Actions](#5-automatizar-el-despliegue-con-github-actions)
6. [Migrar la base de datos de PostgreSQL a MySQL](#6-migrar-la-base-de-datos-de-postgresql-a-mysql)
7. [Checklist post-despliegue](#7-checklist-post-despliegue)
8. [Mantenimiento y monitoreo](#8-mantenimiento-y-monitoreo)

---

## 1. Arquitectura de despliegue

El repositorio contiene **dos proyectos Django independientes** que comparten una única base de
datos (ver [`FonoAppPortalMedico/DOCUMENTACION.md` §"Nota de estructura"](FonoAppPortalMedico/DOCUMENTACION.md)):

```
Backend_Fono/
├── FonoApp/                  → API pública + panel de administradores      (proyecto 1)
├── FonoAppPortalMedico/      → Portal médico (profesionales/citas/videos)  (proyecto 2)
├── requirements.txt          → dependencias compartidas por ambos proyectos
└── docker-compose.yml        → Postgres + pgAdmin, SOLO para desarrollo local
```

En producción, cada proyecto se despliega como una **aplicación cPanel independiente** ("Python
App" en la terminología de cPanel), típicamente detrás de su propio subdominio:

```
                        ┌─────────────────────────┐
        api.tudominio.cl│  FonoApp (Python App 1) │
                        └────────────┬────────────┘
                                     │
                          ┌──────────┴──────────┐
                          │   MySQL (una sola    │←── ambos comparten SECRET_KEY
                          │   base de datos)     │    para que un JWT de admin
                          └──────────┬──────────┘    emitido en uno sea válido
                                     │                en el otro
                        ┌────────────┴────────────┐
    portal.tudominio.cl │FonoAppPortalMedico (App2)│
                        └─────────────────────────┘
```

Puntos clave que condicionan todo el resto de esta guía:

- **Un solo hosting, dos "Python App"**: el Plan Emprendedor no distingue por proyecto, así que
  se configuran dos aplicaciones separadas dentro de la misma cuenta cPanel (dos Application
  roots, dos virtualenvs, típicamente dos subdominios).
- **Una sola base de datos** para ambas: no se crean dos bases MySQL, sino una, igual que hoy
  comparten `fonoDevDB` en Postgres.
- **Mismo `SECRET_KEY` en ambas apps**: es lo que hace que un token JWT de administrador emitido
  por el login de `FonoApp` sirva para aprobar acreditaciones en `FonoAppPortalMedico`.
- El frontend Angular consume ambas APIs desde dominios distintos → hay que configurar
  `CORS_ALLOWED_ORIGINS` en ambos proyectos apuntando al dominio real del frontend en producción.

## 2. El hosting: Plan Emprendedor de V2Networks

Características del plan al momento de escribir esta guía (verificar en
[v2networks.cl/hosting-emprendedores](https://v2networks.cl/hosting-emprendedores/) antes de
contratar, ya que los proveedores ajustan specs con el tiempo):

| Recurso | Detalle |
|---|---|
| Precio | $34.900 CLP + IVA al año |
| Almacenamiento | 50 GB NVMe |
| CPU / RAM | 2 núcleos / 4 GB |
| Bases de datos MySQL | Ilimitadas |
| Dominios/subdominios adicionales | Ilimitados |
| Cuentas de correo | Ilimitadas |
| Panel | cPanel |
| Soporte Python | Sí ("Setup Python App", vía Phusion Passenger) |
| SSL | Gratis e ilimitado |
| Backups | Automáticos |

Puntos a **confirmar con soporte de V2Networks antes de automatizar nada** (no están garantizados
por el plan y cambian la estrategia de CI/CD, ver [sección 5](#5-automatizar-el-despliegue-con-github-actions)):

- **¿Incluye acceso SSH?** Es lo ideal para automatizar (permite correr `pip install`,
  `migrate`, `collectstatic` remotamente). Si el plan no lo trae por defecto, suele poder
  pedirse como upgrade puntual.
- **Puerto SSH real** (cPanel suele exponerlo en un puerto no estándar, ej. `21098`, no `22`).
- **Versión(es) de Python disponibles en "Setup Python App".** Esto es un bloqueante real, no un
  detalle: **Django 6.0 (la versión que usa este proyecto) requiere Python 3.12 o superior**
  ([release notes de Django 6.0](https://docs.djangoproject.com/en/6.0/releases/6.0/)). Antes de
  contratar o de crear las apps en cPanel, confirmar que 3.12+ está disponible en el selector de
  "Setup Python App" — si el servidor solo ofrece hasta 3.11, hay que pedir la actualización a
  soporte antes de continuar.

## 3. Antes de empezar: qué preparar

1. **Dominio propio** apuntando a los DNS de V2Networks (o subdominios de uno ya existente, ej.
   `api.tudominio.cl` y `portal.tudominio.cl`).
2. **`SECRET_KEY` de producción único**, generado una sola vez y reutilizado en ambos proyectos:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
3. **Credenciales de reCAPTCHA de producción** (`RECAPTCHA_SECRET_KEY`, usado por `FonoApp`).
4. Decidir y documentar los **Application roots** en el servidor, ej.:
   - `/home/<usuario_cpanel>/fonoapp` → `FonoApp`
   - `/home/<usuario_cpanel>/portalmedico` → `FonoAppPortalMedico`
5. Revisar la carpeta [`deploy/`](deploy/README.md): todo lo que se referencia de acá en adelante
   vive ahí, listo para copiar cuando corresponda.

## 4. Despliegue manual inicial en cPanel

Este primer despliegue se hace **a mano, una sola vez por proyecto**. Las actualizaciones
posteriores sí se automatizan (sección 5).

### 4.1 Crear la aplicación Python

Para cada proyecto (repetir dos veces, una por `FonoApp` y otra por `FonoAppPortalMedico`):

1. cPanel → **Software → Setup Python App → Create Application**.
2. **Python version**: la mayor disponible ≥ 3.12 (ver [sección 2](#2-el-hosting-plan-emprendedor-de-v2networks)).
3. **Application root**: ej. `fonoapp` (queda en `/home/<usuario>/fonoapp`).
4. **Application URL**: el subdominio correspondiente (ej. `api.tudominio.cl`).
5. **Application startup file**: `passenger_wsgi.py` (cPanel puede generarlo solo con un
   `import imp` deprecado — lo vamos a reemplazar en el paso 4.3).
6. Click **Create**. cPanel crea el virtualenv en
   `/home/<usuario>/virtualenv/fonoapp/<version>/` — **anota esta ruta**, la vas a necesitar tanto
   ahora como en los secrets de GitHub Actions (sección 5).

### 4.2 Subir el código

Opciones, de más a menos recomendable:

- **Git (si cPanel ofrece "Git™ Version Control")**: clonar el repo (o el subárbol) directo desde
  GitHub. Simplifica los despliegues manuales siguientes a un `git pull`.
- **SFTP/FTP con un cliente (FileZilla, etc.)**: subir el contenido de `FonoApp/` (todo lo que
  está dentro de esa carpeta, no la carpeta misma) al Application root `fonoapp/`, y de
  `FonoAppPortalMedico/` a `portalmedico/`. En ambos casos, **sumar también `requirements.txt`**
  (vive un nivel más arriba en el repo) dentro de esa misma carpeta subida.
- **Terminal de cPanel + `git clone`**, si está disponible.

### 4.3 Configurar `passenger_wsgi.py`

Reemplazar el archivo autogenerado por el contenido de:
- [`deploy/cpanel/passenger_wsgi.fonoapp.py.example`](deploy/cpanel/passenger_wsgi.fonoapp.py.example) → subir como `passenger_wsgi.py` en el Application root de `FonoApp`.
- [`deploy/cpanel/passenger_wsgi.portalmedico.py.example`](deploy/cpanel/passenger_wsgi.portalmedico.py.example) → ídem para `FonoAppPortalMedico`.

Ajustar la ruta `PROJECT_ROOT` de cada archivo a la ruta absoluta real (`/home/<usuario>/fonoapp`
y `/home/<usuario>/portalmedico`, respectivamente) antes de subirlo.

### 4.4 Variables de entorno

En la pantalla de "Setup Python App" de cada aplicación hay una sección **Environment
variables**: ahí se cargan `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
`DATABASE_URL` (o `DB_*`), etc. — las mismas que `FonoApp/.env.production.example` /
`FonoAppPortalMedico/.env.example`, con valores reales de producción.

Si en este punto ya se migró a MySQL (sección 6), usar como base
[`deploy/mysql/env.production.fonoapp.mysql.example`](deploy/mysql/env.production.fonoapp.mysql.example)
y [`deploy/mysql/env.production.portalmedico.mysql.example`](deploy/mysql/env.production.portalmedico.mysql.example).

No hace falta un archivo `.env` físico en el servidor: `load_dotenv()` en `settings.py` no
sobreescribe variables ya presentes en el entorno real, así que basta con lo cargado acá.

### 4.5 Instalar dependencias y migrar

Desde el botón **"Run Pip Install"** de "Setup Python App" (lee `requirements.txt` del
Application root automáticamente), o por Terminal si está disponible:

```bash
source /home/<usuario>/virtualenv/fonoapp/<version>/bin/activate
cd /home/<usuario>/fonoapp
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # solo la primera vez, solo en FonoApp
```

Repetir para `portalmedico` (sin `createsuperuser`: los administradores viven en `FonoApp`).

### 4.6 Reiniciar y probar

Botón **Restart** en "Setup Python App", o `touch tmp/restart.txt` dentro del Application root
(convención de Passenger: reinicia al detectar un cambio en el `mtime` de ese archivo). Probar
`GET https://api.tudominio.cl/api/cuidados/listar/` y `GET https://portal.tudominio.cl/api/pm/medicos/directorio/`
(ambos son endpoints públicos, sirven para confirmar que la app levantó sin necesitar login).

## 5. Automatizar el despliegue con GitHub Actions

A partir de acá, los despliegues siguientes ya no son manuales: un push a una rama de producción
dispara un workflow que sincroniza el código y reinicia la app.

### 5.1 Elegir estrategia según si hay SSH disponible

| | Con acceso SSH (recomendado) | Solo FTP/SFTP |
|---|---|---|
| Archivo a activar | [`deploy/github-actions/deploy.yml`](deploy/github-actions/deploy.yml) | [`deploy/github-actions/deploy-sftp.yml`](deploy/github-actions/deploy-sftp.yml) |
| `pip install` / `migrate` / `collectstatic` automáticos | Sí | No — hay que correrlos a mano tras cada deploy que cambie dependencias o modelos |
| Reinicio de Passenger automático | Sí (`touch tmp/restart.txt` remoto) | Sí (se sube el archivo por SFTP) |

Activar copiando el archivo elegido a `.github/workflows/deploy.yml`:

```bash
cp deploy/github-actions/deploy.yml .github/workflows/deploy.yml
```

### 5.2 Generar la llave SSH dedicada (si se usa la opción con SSH)

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

- La **pública** (`deploy_key.pub`) se agrega en cPanel → **SSH Access → Manage SSH Keys → Import
  Key**, y luego **Authorize** esa llave.
- La **privada** (`deploy_key`, sin extensión) se guarda como secret `SSH_PRIVATE_KEY` en GitHub
  (nunca se commitea al repo).

### 5.3 Secrets a cargar en GitHub

Repositorio → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Ejemplo | Usado por |
|---|---|---|
| `SSH_HOST` | `servidor.v2networks.cl` | ambos workflows |
| `SSH_PORT` | `21098` (confirmar con soporte) | `deploy.yml` |
| `SSH_USERNAME` | usuario cPanel | `deploy.yml` |
| `SSH_PRIVATE_KEY` | contenido de `deploy_key` | `deploy.yml` |
| `FONOAPP_REMOTE_PATH` | `/home/usuario/fonoapp` | ambos |
| `FONOAPP_VENV_ACTIVATE` | `/home/usuario/virtualenv/fonoapp/3.12/bin/activate` | `deploy.yml` |
| `PORTALMEDICO_REMOTE_PATH` | `/home/usuario/portalmedico` | ambos |
| `PORTALMEDICO_VENV_ACTIVATE` | `/home/usuario/virtualenv/portalmedico/3.12/bin/activate` | `deploy.yml` |
| `SFTP_HOST` / `SFTP_PORT` / `SFTP_USERNAME` / `SFTP_PASSWORD` | — | solo `deploy-sftp.yml` |

Los detalles de cada paso (qué excluye el rsync, cómo se activa el virtualenv, cómo se marca el
reinicio) están comentados dentro del propio archivo `.yml` — está pensado para leerse de arriba
a abajo como documentación ejecutable.

### 5.4 Flujo de trabajo recomendado con ramas

- `develop` (o `main`): desarrollo normal, sin despliegue automático.
- `production`: rama protegida; el workflow se dispara con cada push a `production`. El pase de
  `develop`/`main` a `production` se hace vía Pull Request, dando un punto de revisión antes de
  que algo llegue a producción.
- El job `test` corre `python manage.py test` de ambos proyectos **antes** de desplegar; si falla,
  el deploy no se ejecuta (`needs: test` en los jobs de deploy).
- También se puede disparar manualmente desde la pestaña **Actions** de GitHub
  (`workflow_dispatch`), sin necesidad de un push.

### 5.5 Qué NO gestiona GitHub Actions

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, etc. se configuran **una sola vez** como
variables de entorno en "Setup Python App" (sección 4.4) y persisten entre despliegues — el
workflow no las toca ni las necesita conocer.

## 6. Migrar la base de datos de PostgreSQL a MySQL

**Por qué:** el Plan Emprendedor de V2Networks (como la mayoría del hosting compartido cPanel)
ofrece bases de datos **MySQL** ilimitadas; no ofrece PostgreSQL administrado. Para desplegar ahí,
la base de datos de producción tiene que ser MySQL — el entorno de **desarrollo local puede seguir
usando Postgres sin cambios** (ver más abajo, es justamente lo que permite `db_engine_snippet.py`).

### 6.1 Compatibilidad del modelo de datos

Se revisó todo el código de ambos proyectos: **ningún modelo usa tipos específicos de
PostgreSQL** (`ArrayField`, `JSONField`, `HStoreField`, búsqueda full-text, etc.). Todos los
campos (`CharField`, `TextField`, `DateTimeField`, `ImageField`/`FileField`, `BooleanField`,
`ForeignKey`, `ManyToManyField`...) son estándar de Django y migran a MySQL sin cambios de
esquema. Esto simplifica mucho la migración: es un cambio de configuración, no de modelos.

### 6.2 Aplicar el soporte de MySQL a `settings.py` (ambos proyectos)

1. Sumar el contenido de [`deploy/mysql/requirements-mysql.txt`](deploy/mysql/requirements-mysql.txt)
   a `requirements.txt` (raíz del repo). Se instala `PyMySQL` (driver 100% Python) en vez de
   `mysqlclient`, porque `mysqlclient` requiere compilar contra headers de MySQL en C, algo que
   normalmente **no está disponible** para el usuario en hosting compartido tipo cPanel.
2. Pegar el contenido de [`deploy/mysql/pymysql_shim_snippet.py`](deploy/mysql/pymysql_shim_snippet.py)
   al inicio de `FonoApp/FonoApp/__init__.py` y `FonoAppPortalMedico/FonoAppPM/__init__.py`
   (ambos están vacíos hoy). Este shim de 2 líneas hace que Django, que internamente busca el
   módulo `MySQLdb`, encuentre PyMySQL funcionando como si fuera ese driver.
3. Reemplazar el bloque `DATABASES` actual de `FonoApp/FonoApp/settings.py` y
   `FonoAppPortalMedico/FonoAppPM/settings.py` por el contenido de
   [`deploy/mysql/db_engine_snippet.py`](deploy/mysql/db_engine_snippet.py). Es un *superset*
   retrocompatible: selecciona el motor según la variable de entorno `DB_ENGINE`
   (`postgresql`, el default de siempre, o `mysql`) — **mientras no definas `DB_ENGINE=mysql` en
   ningún entorno, el comportamiento es idéntico al actual**, así que el `docker-compose.yml` y
   el flujo de desarrollo local con Postgres siguen funcionando sin tocar nada más.

### 6.3 Crear la base de datos en cPanel

1. cPanel → **Bases de Datos → MySQL® Databases**.
2. Crear una base (ej. `fonoapp`) — cPanel la nombra con el prefijo de tu cuenta:
   `<usuario_cpanel>_fonoapp`.
3. Crear un usuario MySQL y una contraseña fuerte — queda como `<usuario_cpanel>_fonouser`.
4. **Add User to Database**, marcando **ALL PRIVILEGES**. cPanel no vincula usuario↔base
   automáticamente al crear cada uno por separado, hay que hacer este paso explícito.
5. Usar esta misma base para ambos proyectos (`FonoApp` y `FonoAppPortalMedico` comparten base,
   ver [sección 1](#1-arquitectura-de-despliegue)) — no crear una segunda base para el portal médico.

### 6.4 Cargar las variables de entorno de MySQL

Usar como base [`deploy/mysql/env.production.fonoapp.mysql.example`](deploy/mysql/env.production.fonoapp.mysql.example)
y [`deploy/mysql/env.production.portalmedico.mysql.example`](deploy/mysql/env.production.portalmedico.mysql.example),
completando `DATABASE_URL` (o las variables `DB_*` + `DB_ENGINE=mysql`) con los datos reales del
paso anterior, y cargándolas en "Setup Python App" (sección 4.4) — **no** subir estos archivos
con valores reales al repositorio.

### 6.5 Migrar (y, si aplica, traer datos existentes)

- **Si es el primer despliegue (sin datos previos que conservar)**: solo hace falta correr
  `python manage.py migrate` sobre la base MySQL vacía, como en la sección 4.5. Es el caso más
  común — ver [`deploy/scripts/migrar_postgres_a_mysql.md` → Escenario A](deploy/scripts/migrar_postgres_a_mysql.md#escenario-a--base-nueva-sin-datos-que-conservar-el-caso-normal-para-el-primer-despliegue).
- **Si ya existen datos en la base Postgres de desarrollo que se quieren conservar** (contenido
  cargado de prueba, profesionales de prueba, etc.): seguir la guía completa en
  [`deploy/scripts/migrar_postgres_a_mysql.md` → Escenario B](deploy/scripts/migrar_postgres_a_mysql.md#escenario-b--ya-sembraste-datos-de-prueba-en-postgres-dev-y-quieres-llevarlos-a-mysql),
  que cubre `dumpdata`/`loaddata` (recomendado) y `pgloader` (alternativa para volúmenes grandes).

### 6.6 Probar antes de cortar producción

Se puede validar todo el cambio de motor **localmente antes de tocar el servidor**: levantar un
contenedor MySQL/MariaDB de prueba (no está en `docker-compose.yml` hoy, para no obligar a nadie
en el equipo a usar MySQL en desarrollo — se puede levantar aparte con
`docker run -e MYSQL_ROOT_PASSWORD=root -p 3306:3306 mariadb:11`), exportar `DB_ENGINE=mysql` y
las `DB_*` correspondientes, y correr `python manage.py migrate` + `python manage.py test` contra
esa base antes de aplicar el cambio en producción.

## 7. Checklist post-despliegue

- [ ] `DEBUG=False` en ambos proyectos.
- [ ] `ALLOWED_HOSTS` con los dominios reales (no `*`).
- [ ] `SECRET_KEY` único de producción, **idéntico** en `FonoApp` y `FonoAppPortalMedico`.
- [ ] `CORS_ALLOWED_ORIGINS` apuntando al dominio real del frontend (no `localhost`).
- [ ] `python manage.py migrate` corrido en ambos proyectos, en ese orden (`FonoApp` primero).
- [ ] `python manage.py collectstatic --noinput` corrido en ambos.
- [ ] Al menos un `FonoApp_Administracion` con `is_superuser=True` (necesario para poder resolver
      acreditaciones de profesionales en `FonoAppPortalMedico` — ver
      [`FonoAppPortalMedico/DOCUMENTACION.md` §6](FonoAppPortalMedico/DOCUMENTACION.md#6-autenticación-y-autorización)).
- [ ] Certificado SSL activo en ambos subdominios (gratis con V2Networks, pero hay que emitirlo
      desde cPanel → SSL/TLS Status si no se activó solo).
- [ ] Carpetas `media/` de ambos proyectos con permisos de escritura para el usuario de la app
      (necesario para subir banners, imágenes, documentos de respaldo y videos).
- [ ] Cron job de limpieza de videos vencidos activo — ver
      [`deploy/scripts/crontab_limpiar_videos.txt`](deploy/scripts/crontab_limpiar_videos.txt) y
      [`FonoAppPortalMedico/DOCUMENTACION.md` §10.2](FonoAppPortalMedico/DOCUMENTACION.md#102-lógica-de-vigencia-30-días).
- [ ] Probar un flujo completo de punta a punta: login admin en `FonoApp` → usar ese token en
      `FonoAppPortalMedico` para listar profesionales pendientes de acreditación.

## 8. Mantenimiento y monitoreo

- **Logs**: cPanel expone logs de error de Passenger por app en "Setup Python App" (o en
  `~/logs/` según configuración del hosting). Revisar ahí ante un 500 que no se explica solo con
  `DEBUG=False`.
- **Backups**: el plan incluye backups automáticos del hosting (archivos + bases MySQL), pero
  conviene no depender solo de eso para datos clínicos/sensibles (documentos de respaldo de
  profesionales, videos de síntomas) — evaluar un backup adicional propio si el volumen de datos
  lo justifica.
- **Rotación de `SECRET_KEY` / credenciales**: si alguna vez se necesita rotar el `SECRET_KEY` de
  producción, hay que actualizarlo en **ambas** apps al mismo tiempo (un reinicio con claves
  distintas invalida cruzadamente los JWT entre `FonoApp` y `FonoAppPortalMedico`).
- **Actualizar dependencias**: como `requirements.txt` es compartido por ambos proyectos, un
  `pip install -r requirements.txt` en cada Application root basta para mantenerlos alineados;
  los workflows de GitHub Actions ya lo hacen en cada deploy (sección 5).
