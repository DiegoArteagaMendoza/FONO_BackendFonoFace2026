# DOCUMENTACIÓN DEL PROYECTO FONOAPPPORTALMEDICO (BACKEND)

> Nota de alcance: este documento cubre el proyecto **`FonoAppPortalMedico`** (Portal Médico: registro/acreditación de fonoaudiólogos, pacientes, citas y videos de síntomas). El proyecto hermano **`FonoApp`** (portal público + panel de administradores) está documentado en [`FonoApp/DOCUMENTACION.md`](../FonoApp/DOCUMENTACION.md).

> Nota de estructura: el repositorio `Backend_Fono` aloja **dos proyectos Django independientes** como carpetas hermanas en la raíz: `FonoApp/` (proyecto principal) y `FonoAppPortalMedico/` (este proyecto). Cada uno tiene su propio `manage.py` y su propio paquete de configuración (`FonoApp/FonoApp/settings.py` y `FonoAppPortalMedico/FonoAppPM/settings.py`). El entorno virtual (`.venv/`), `docker-compose.yml` y `requirements.txt` son compartidos y viven en la raíz del repositorio, un nivel por encima de esta carpeta. **Ambos proyectos apuntan a la misma base de datos** y deben compartir el mismo `SECRET_KEY` — ver [sección 6](#6-autenticación-y-autorización).

## Índice

1. [Descripción general](#1-descripción-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Puesta en marcha del proyecto](#3-puesta-en-marcha-del-proyecto)
4. [Configuración relevante (`FonoAppPM/settings.py`)](#4-configuración-relevante-fonoapppmsettingspy)
5. [Mapa de rutas raíz (`FonoAppPM/urls.py`)](#5-mapa-de-rutas-raíz-fonoapppmurlspy)
6. [Autenticación y autorización](#6-autenticación-y-autorización)
7. [Módulo `PmMedico`](#7-módulo-pmmedico)
8. [Módulo `PmCliente`](#8-módulo-pmcliente)
9. [Módulo `PmCita`](#9-módulo-pmcita)
10. [Módulo `PmVideo`](#10-módulo-pmvideo)
11. [Relación entre `PmCliente`, `PmCita` y `PmVideo`](#11-relación-entre-pmcliente-pmcita-y-pmvideo)
12. [Deuda técnica conocida](#12-deuda-técnica-conocida)
13. [Tabla resumen de endpoints](#13-tabla-resumen-de-endpoints)

---

## 1. Descripción general

**FonoAppPortalMedico** es el backend del portal donde:

- Los **fonoaudiólogos** se registran, suben documentación de respaldo y son acreditados por un administrador de FonoApp antes de aparecer en el directorio público y poder atender.
- Se gestionan **pacientes** (`PmCliente`), **citas** (`PmCita`) entre paciente y profesional, y **videos de síntomas** (`PmVideo`) que el paciente puede adjuntar a una cita, con vigencia acotada a 30 días.

No tiene su propio panel de "super administrador": reutiliza a los administradores de `FonoApp` (misma tabla `FonoApp_Administracion`, misma base de datos) para todo lo que requiere rol administrativo (acreditar profesionales, validar documentos, gestionar especialidades, ver listados completos).

## 2. Stack tecnológico

| Componente | Detalle |
|---|---|
| Lenguaje / Framework | Python + Django 6.0.6 |
| API | Django REST Framework 3.17.1 |
| Autenticación | `djangorestframework-simplejwt` 5.5.1 vía una clase custom (`Security.authentication.PmMedicoJWTAuthentication`) |
| Base de datos | PostgreSQL 15 (vía Docker), **misma instancia física que `FonoApp`** |
| CORS | `django-cors-headers` |
| Variables de entorno | `python-dotenv` + `dj-database-url` |

## 3. Puesta en marcha del proyecto

Requisitos: Python 3.14 (venv compartido en `.venv/`, en la raíz del repositorio), Docker (para PostgreSQL).

```bash
# 1. Levantar la base de datos (PostgreSQL + pgAdmin) con Docker (desde la raíz del repo)
docker-compose up -d

# 2. Activar el entorno virtual e instalar dependencias (desde la raíz del repo)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Entrar a la carpeta de este proyecto
cd FonoAppPortalMedico

# 4. Variables de entorno (solo la primera vez)
cp .env.example .env
# IMPORTANTE: SECRET_KEY debe ser idéntico al de FonoApp/.env (ver sección 6)

# 5. Migraciones
python manage.py makemigrations
python manage.py migrate

# 6. Levantar el servidor de desarrollo (puerto 8001 por defecto, para no chocar con FonoApp en 8000)
python manage.py runserver
```

- Los archivos subidos (documentos de respaldo, videos) se sirven en desarrollo desde `/media/` (carpeta física `FonoAppPortalMedico/media/`) solo cuando `DEBUG=True` (`FonoAppPM/urls.py`).
- Para poder probar el flujo de acreditación necesitas al menos un usuario de `FonoApp` con `is_staff=True` (ver `Security/permissions.py:EsAdministrador` en [sección 6](#6-autenticación-y-autorización)) — créalo o edítalo desde el proyecto `FonoApp` (Django admin o shell), no desde este proyecto.

## 4. Configuración relevante (`FonoAppPM/settings.py`)

- `INSTALLED_APPS` = `DEV_APPS` (`PmMedico`, `PmCliente`, `PmCita`, `PmVideo`) + `BASE_APPS` (Django nativas) + `FRAMEWORKS` (DRF, CORS, SimpleJWT). No usa un `AUTH_USER_MODEL` propio: no tiene modelo de usuario Django nativo, la identidad se resuelve enteramente vía JWT (ver sección 6).
- `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = ('IsAuthenticated',)`: a diferencia de `FonoApp`, aquí **todo endpoint es privado por defecto**; cada vista pública debe declarar explícitamente `@permission_classes([AllowAny])`.
- `PM_MEDICO_DOCUMENTO_MAX_MB` (env, default `5`): tamaño máximo en MB para los documentos de respaldo de profesionales.
- `SIMPLE_JWT`: mismas variables `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` que `FonoApp` (default 60 min / 1 día).

### 4.1 Variables de entorno

| Archivo | Se versiona en git | Uso |
|---|---|---|
| `FonoAppPortalMedico/.env` | **No** | Copia de trabajo real para desarrollo local (`cp .env.example .env`). |
| `FonoAppPortalMedico/.env.example` | Sí | Plantilla de desarrollo. |

Variables soportadas (idénticas en espíritu a `FonoApp`, ver [`FonoApp/DOCUMENTACION.md` §5.1](../FonoApp/DOCUMENTACION.md#51-variables-de-entorno)): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `PORT`, `CORS_ALLOWED_ORIGINS`, `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`, `DATABASE_URL` (prioritaria sobre `DB_*`, vía `dj_database_url`), `DATABASE_SSL_REQUIRE`, `JWT_ACCESS_MINUTES`/`JWT_REFRESH_DAYS`, y además `PM_MEDICO_DOCUMENTO_MAX_MB` (propia de este proyecto).

> **`SECRET_KEY` compartido:** este proyecto y `FonoApp` deben usar exactamente el mismo `SECRET_KEY`. Un JWT de administrador se emite en `FonoApp` (login de `FonoAppAdministracion`) y se valida aquí para operaciones administrativas (acreditar profesionales, validar documentos, etc.); si las claves difieren, esos tokens dejan de ser válidos en este proyecto.

## 5. Mapa de rutas raíz (`FonoAppPM/urls.py`)

| Prefijo | App |
|---|---|
| `api/pm/medicos/` | `PmMedico` |
| `api/pm/clientes/` | `PmCliente` |
| `api/pm/citas/` | `PmCita` |
| `api/pm/videos/` | `PmVideo` |
| `admin/` | Panel de administración de Django |

## 6. Autenticación y autorización

Toda la autenticación pasa por `Security/authentication.py:PmMedicoJWTAuthentication`, la única clase de autenticación configurada en `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`. Lee el header `Authorization: Bearer <token>`, decodifica el `AccessToken` de SimpleJWT y resuelve la identidad según qué claim trae:

- Claim `user_id` (el que emite el login de `FonoAppAdministracion` en el proyecto **`FonoApp`**) → busca en `PmMedico.models.Administrador`, un modelo **reflejo de solo lectura** (`managed=False`, `db_table='FonoApp_Administracion'`) de la tabla real de `FonoApp`. Exige `is_active=True` y `estado=True`.
- Claim `id_profesional` (el que emite `PmMedico.views.profesional_login`, propio de este proyecto) → busca en `PM_Profesional`. Exige `estado_cuenta_profesional=True`.
- Sin header `Bearer` → `None` (permite que las rutas `AllowAny` sigan funcionando sin token).
- Token con un claim que no es ninguno de los dos, o usuario inexistente/inactivo → `AuthenticationFailed` (401).

No existe una tercera identidad autenticada por JWT para pacientes (`PmCliente`) — ver [sección 12](#12-deuda-técnica-conocida).

### Permisos custom (`Security/permissions.py`)

| Permiso | Regla | Cubre |
|---|---|---|
| `EsAdministrador` | `isinstance(usuario, Administrador) and usuario.is_staff` | Cualquier administrador de `FonoApp` con `is_staff=True`. **Admin y SuperAdmin tienen los mismos permisos en este backend** — no hay una acción reservada exclusivamente al rol máximo (`is_superuser`) dentro de `FonoAppPortalMedico`. |
| `EsProfesional` | `isinstance(request.user, PM_Profesional)` | Un fonoaudiólogo autenticado con su propio login. |
| `es_dueno_del_recurso(usuario, id_x)` | helper (no es `BasePermission`) | Se invoca dentro de una vista para verificar que el profesional autenticado sea el dueño del recurso pedido. |

> ⚠️ **Nota de precisión:** varios comentarios en `PmMedico/urls.py` (validar documento, resolver acreditación, gestionar especialidades) dicen *"requiere token administrador con rol máximo (`is_superuser`)"*, pero el código real de esas vistas usa `@permission_classes([EsAdministrador])`, que solo exige `is_staff`. Es decir, hoy **cualquier administrador** (no solo uno con `is_superuser=True`) puede acreditar profesionales, validar documentos y gestionar especialidades. Si en algún momento se quiere restringir esas acciones al rol máximo real, hay que introducir un permiso nuevo basado en `Administrador.es_rol_maximo` (propiedad ya definida en `PmMedico/models.py` pero sin uso actual) y aplicarlo en esas vistas — los comentarios del código son aspiracionales, no reflejan el comportamiento real.

Validadores reutilizables en `Security/validators.py`:

- `validar_rut_chileno(rut)`: normaliza y valida dígito verificador (módulo 11). Usado por `PM_Profesional.rut_profesional`. **No** se usa en `PmCliente.rut_cliente` (ver sección 8).
- `validar_telefono(telefono)`: formato chileno `(+56)?[2-9]\d{7,8}`. Usado por `PM_Profesional.telefono_profesional`. **No** se usa en `PmCliente.telefono_cliente`.
- `validar_archivo_documento(archivo)`: valida extensión (`.pdf .jpg .jpeg .png`) y tamaño máximo (`PM_MEDICO_DOCUMENTO_MAX_MB`, default 5MB) para los documentos de respaldo.

---

## 7. Módulo `PmMedico`

Registro, acreditación, especialidades y directorio público de fonoaudiólogos. Endpoint base: `api/pm/medicos/`.

### 7.1 Modelos

**`Administrador`** — espejo de solo lectura de `FonoApp_Administracion` (ver sección 6). No se crea ni edita desde este proyecto.

**`PM_Profesional`**

| Campo | Tipo | Notas |
|---|---|---|
| `id_profesional` | AutoField (PK) | |
| `nombres_profesional` / `apellidos_profesional` | CharField(100) | |
| `rut_profesional` | CharField(12), único | `validators=[validar_rut_chileno]` |
| `numero_registro_salud_profesional` | CharField(30), opcional | vacío hasta que se complete; obligatorio para que la acreditación pase a `APROBADO` |
| `email_profesional` | EmailField, único | |
| `telefono_profesional` | CharField(20) | `validators=[validar_telefono]` |
| `password_profesional` | CharField(128) | hash propio vía `set_password`/`check_password` (no usa `AbstractBaseUser`) |
| `estado_cuenta_profesional` | Boolean, default `True` | borrado lógico |
| `especialidades` | M2M (`through=PM_Profesional_especialidad`) | `related_name='profesionales'` |

**`PM_Acreditacion`** — una por profesional (o varias históricas, `related_name='acreditaciones'`), con `estado_verificacion_profesional` en `{PENDIENTE, EN_REVISION, APROBADO, RECHAZADO}` (default `PENDIENTE`). `id_administrador_resolutor` es FK a `Administrador` con `db_constraint=False` (la tabla vive en la BD de `FonoApp`, no se puede exigir una FK real entre motores/apps distintos gestionados por separado) y `on_delete=SET_NULL`.

**`PM_Documento_Respaldo`** — tipo en `{CEDULA_IDENTIDAD, CERTIFICADO_TITULO, CERTIFICADO_SUPERINTENDENCIA}`, archivo (`url_documento_profesional`, `upload_to='pm_medico/documentos/%Y/%m/'`) y bandera `documento_profesional_valido` (default `False`, la marca un administrador).

**`PM_Especialidad`** — catálogo (`nombre_especialidad_profesional` único) con bandera `especialidad_requiere_certificado`.

**`PM_Profesional_especialidad`** — tabla intermedia M:N, `unique_together=('id_profesional', 'id_especialidad')`.

### 7.2 Reglas de negocio

- **Registro público** (`crear_profesional`): valida fortaleza de la contraseña (`validate_password` de Django) antes de hashear, y **crea automáticamente una `PM_Acreditacion` en `PENDIENTE`** — intencional, para que el alta inicial sea ágil y el profesional pueda empezar a subir documentos de inmediato. Todo en una transacción atómica.
- **Login** (`autenticar`): busca por email o RUT; si las credenciales fallan o el usuario está inactivo, retorna el mismo error genérico (no revela cuál de los dos motivos aplicó, por seguridad).
- **Subir documento** → si la acreditación seguía en `PENDIENTE`, **la mueve automáticamente a `EN_REVISION`** en cuanto llega el primer documento.
- **Eliminar documento propio**: el profesional solo puede borrar un documento suyo si **todavía no fue validado** (`documento_profesional_valido=False`). Uno ya validado queda protegido como parte del expediente de auditoría; solo un administrador puede "invalidarlo" primero.
- **Resolver acreditación** (aprobar/rechazar), función central `resolver`:
  - Solo transiciona si el estado actual no es ya `APROBADO` ni `RECHAZADO` (evita resolver dos veces).
  - Para **aprobar** exige: `numero_registro_salud_profesional` no vacío **y** al menos un documento con `documento_profesional_valido=True`. Si falta cualquiera de los dos, la operación se rechaza sin cambiar el estado.
  - Al resolver, queda registrada la fecha (`fecha_resolucion_profesional`) y el administrador que resolvió (`id_administrador_resolutor`), para auditoría.
  - Solo `EsAdministrador` puede invocarla (ver nota de precisión en sección 6: no está restringido al rol máximo real, aunque el comentario del código lo sugiera).
- **Asignar especialidad**: si la especialidad tiene `especialidad_requiere_certificado=True`, el profesional debe tener **al menos un documento ya validado** antes de poder reclamarla (no se exige que el documento sea específicamente de esa especialidad, solo que exista al menos uno validado).
- **Directorio público** (`verificados()`): solo profesionales con `estado_cuenta_profesional=True` **y** al menos una acreditación en `APROBADO`.

### 7.3 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| POST | `registrar/` | Público | Crea profesional + acreditación `PENDIENTE` |
| POST | `login/` | Público | `{ email_o_rut, password }` → `{ refresh, access, profesional }` (claim `id_profesional`) |
| GET | `perfil/` | Profesional | Perfil propio completo |
| PATCH | `perfil/editar/` | Profesional | Edita datos de contacto (whitelist, nunca `password`/`estado_cuenta_profesional`) |
| PUT | `perfil/password/` | Profesional | Cambia contraseña (exige la actual + revalida fortaleza) |
| DELETE | `perfil/eliminar/` | Profesional | Baja lógica de la cuenta propia |
| GET | `listar/?estado_verificacion=` | Admin | Listado administrativo filtrable |
| GET | `<id_profesional>/` | Admin | Detalle administrativo |
| GET | `directorio/` | Público | Directorio de profesionales `verificados()` |
| POST | `documentos/subir/` | Profesional | Multipart; primer documento pasa la acreditación a `EN_REVISION` |
| DELETE | `documentos/<id_documento>/eliminar/` | Profesional | Solo si el documento propio no está validado |
| GET | `<id_profesional>/documentos/` | Admin | Lista documentos de un profesional |
| PATCH | `documentos/<id_documento>/validar/` | Admin | Marca/desmarca `documento_profesional_valido` |
| GET | `acreditaciones/pendientes/` | Admin | Cola `PENDIENTE`/`EN_REVISION` |
| GET | `acreditaciones/<id_profesional>/estado/` | Admin o Profesional dueño | Estado vigente |
| PATCH | `acreditaciones/<id_acreditacion>/resolver/` | Admin | Aprueba/rechaza (ver reglas 7.2) |
| GET | `especialidades/listar/` | Público | Catálogo |
| POST | `especialidades/crear/` | Admin | Crea especialidad |
| PUT/PATCH | `especialidades/<id>/editar/` | Admin | Edita |
| DELETE | `especialidades/<id>/eliminar/` | Admin | Eliminación **física** (no lógica) |
| POST | `especialidades/asignar/` | Profesional | Body `{ "id_especialidad": int }` |
| DELETE | `especialidades/<id_especialidad>/quitar/` | Profesional | Quita especialidad propia |
| GET | `<id_profesional>/especialidades/` | Público | Solo si el profesional está `verificados()` |

---

## 8. Módulo `PmCliente`

Datos de los pacientes. Endpoint base: `api/pm/clientes/`.

### 8.1 Modelo `PmCliente`

| Campo | Tipo | Notas |
|---|---|---|
| `id_cliente` | AutoField (PK) | |
| `nombres_cliente` / `apellidos_clientes` | CharField(100) | |
| `rut_cliente` | CharField(12), único | normalizado (sin puntos/espacios, minúsculas) en el serializer, **sin validación de dígito verificador** (a diferencia de `PM_Profesional.rut_profesional`) |
| `fecha_nacimiento_cliente` | DateField | |
| `email_cliente` | EmailField, único | normalizado a minúsculas |
| `telefono_cliente` | CharField(20) | **sin** validación de formato (a diferencia de `PM_Profesional.telefono_profesional`) |
| `estado` | Boolean, default `True` | borrado lógico |

### 8.2 Reglas de negocio

- `buscar(texto)`: búsqueda `icontains` combinada sobre nombres, apellidos, RUT y email.
- No existe login ni JWT propio para pacientes — es un modelo de datos administrado por profesionales/administradores (ver [sección 12](#12-deuda-técnica-conocida)).

### 8.3 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| POST | `registrar/` | Público | Alta de paciente |
| GET | `listar/?buscar=texto` | Profesional o Admin | Lista pacientes activos |
| GET | `<id_cliente>/` | Profesional o Admin | Detalle |
| PUT/PATCH | `<id_cliente>/editar/` | Admin | Edición (solo admin) |
| DELETE | `<id_cliente>/eliminar/` | Admin | Baja lógica |

---

## 9. Módulo `PmCita`

Agenda de citas entre paciente y profesional. Endpoint base: `api/pm/citas/`.

### 9.1 Modelo `PmCita` y constantes de negocio

```python
DURACION_MINUTOS_DEFECTO = 45
DURACION_MINUTOS_MINIMA = 15
DURACION_MINUTOS_MAXIMA = 120
HORAS_MINIMAS_ANTICIPACION = 2   # para reservar, cancelar y reprogramar
REPROGRAMACIONES_MAXIMAS = 3
```

Estados (`Estado`): `RE` Reservada (default), `CC` Cancelada por el cliente, `CM` Cancelada por el profesional, `RZ` Realizada.

| Campo | Tipo | Notas |
|---|---|---|
| `cliente` | FK `PmCliente`, `CASCADE` | `related_name='citas'` |
| `profesional` | FK `PM_Profesional`, `CASCADE` | `related_name='citas'` |
| `fecha_hora` | DateTimeField | |
| `duracion_minutos` | PositiveInteger, default `45` | |
| `estado` | Choice, default `RE` | |
| `permite_carga_video` | Boolean, default `True` | habilita que el paciente adjunte un video a esta cita |
| `veces_reprogramada` | Integer, default `0` | tope 3 |
| `motivo_cancelacion` / `fecha_cancelacion` / `cancelada_por` | | auditoría de cancelación |
| `fecha_hora_original` / `motivo_reprogramacion` / `reprogramada_por` / `fecha_ultima_reprogramacion` | | auditoría de reprogramación |

Propiedades: `esta_activa` (estado == `RE`), `ya_paso`, `hora_limite_cambio` (`fecha_hora - 2h`), `permite_cambios()` (activa **y** aún fuera del margen de 2h antes de la hora agendada).

### 9.2 Reglas de negocio

- **Reservar**: (1) el profesional debe estar `verificados()` (acreditación `APROBADO`); (2) la fecha/hora debe tener al menos 2 horas de anticipación desde ahora; (3) no debe solapar con otra cita activa del mismo profesional (intervalos `[inicio, fin)`).
- **Cancelar** (por cliente o por profesional): solo si la cita `esta_activa` y `permite_cambios()` (es decir, fuera del margen de 2 horas previas). Queda registrado el motivo, la fecha y quién canceló.
- **Reprogramar**: mismas condiciones que cancelar, más: tope de 3 reprogramaciones por cita; la nueva fecha también debe respetar las 2 horas de anticipación y no solapar con otra cita del profesional. Se conserva `fecha_hora_original` (solo la primera vez) para trazabilidad.
- **Marcar realizada**: solo el profesional dueño de la cita, y solo si aún está activa.

### 9.3 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| POST | `reservar/` | Paciente | Body: `id_profesional, fecha_hora, motivo_consulta?, duracion_minutos?` |
| GET | `cliente/<id_cliente>/listar/?proximas=true` | Paciente* | Historial o solo próximas activas |
| PATCH | `<id_cita>/cliente/cancelar/` | Paciente | Body: `motivo?` |
| PATCH | `<id_cita>/cliente/posponer/` | Paciente | Body: `fecha_hora, motivo?` |
| GET | `profesional/listar/?proximas=true` | Profesional | Citas del profesional autenticado |
| PATCH | `<id_cita>/profesional/cancelar/` | Profesional | Body: `motivo?` |
| PATCH | `<id_cita>/profesional/posponer/` | Profesional | Body: `fecha_hora, motivo?` |
| PATCH | `<id_cita>/profesional/marcar-realizada/` | Profesional | — |
| GET | `<id_cita>/` | Mixto | Paciente dueño, profesional que atiende o admin; si ninguno aplica, 403 |
| GET | `listar/?cliente=&profesional=&estado=` | Admin | Listado administrativo con filtros combinables |

Los cuatro endpoints de paciente exigen `Authorization: Bearer <token paciente>` y toman el dueño de la cita desde el token, nunca del cuerpo de la petición. El `id_cliente` dejó de viajar en el body al implementarse el login de `PmCliente`.

\* El `id_cliente` sigue en la ruta de `cliente/<id_cliente>/listar/` por compatibilidad, pero solo se acepta si coincide con el del token; en caso contrario responde 403.

---

## 10. Módulo `PmVideo`

Videos cortos de síntomas que un paciente adjunta, opcionalmente, a una cita. Endpoint base: `api/pm/videos/`.

### 10.1 Modelo `PmVideo` y constantes de negocio

```python
DURACION_MAXIMA_SEGUNDOS = 30
DIAS_VIGENCIA = 30
TAMANO_MAXIMO_MB = 50
EXTENSIONES_PERMITIDAS = ['mp4', 'webm', 'mov']
```

| Campo | Tipo | Notas |
|---|---|---|
| `cliente` | FK `PmCliente`, `CASCADE` | obligatorio, `related_name='videos'` |
| `cita` | FK `PmCita`, `SET_NULL`, `null=True, blank=True` | opcional, `related_name='videos'` |
| `video` | FileField | `upload_to='pm/videos/sintomas/'` |
| `duracion_segundos` | PositiveInteger | máx. 30s |
| `fecha_subida` | auto_now_add | |
| `fecha_expiracion` | DateTimeField | calculada automáticamente, ver 10.2 |
| `estado` | Boolean, default `True` | disponible/eliminado |
| `motivo_eliminacion` | Choice opcional | `VE` Vencimiento, `OM` Orden médica, `RP` Retirado por el paciente |

### 10.2 Lógica de vigencia (30 días)

- Al guardarse por primera vez (`PmVideo.save()`), si `fecha_expiracion` no está seteada, se calcula automáticamente como `timezone.now() + timedelta(days=30)` — **siempre a partir de la fecha de subida del video, no de la fecha de la cita asociada**.
- `esta_vigente`: `estado=True` y `fecha_expiracion` aún no pasó.
- `dias_restantes`: redondeado hacia arriba (un video recién subido muestra 30, no 29).
- Las consultas expuestas (`listar/`, detalle) usan siempre `vigentes()` (`estado=True, fecha_expiracion__gt=ahora`) — **nunca se entrega un video vencido**, aunque el archivo físico todavía no se haya purgado del disco.
- **Comando de limpieza**: `python manage.py limpiar_videos_vencidos` (soporta `--simular` para dry-run) recorre los videos vencidos (`vencidos()`), borra el archivo físico del disco y marca `estado=False`, `motivo_eliminacion='VE'`. **No se ejecuta solo**: hay que programarlo externamente (cron en desarrollo/producción — ver [`DOCUMENTACION_DESPLIEGUE.md`](../DOCUMENTACION_DESPLIEGUE.md) para la configuración del cron job en el hosting).
- Un profesional puede ordenar la eliminación **anticipada** de un video (antes de los 30 días) vía `DELETE .../eliminar/`, quedando registrado como `motivo_eliminacion='OM'` (orden médica) en vez de vencimiento.

### 10.3 Validaciones de subida

- `duracion_segundos`: debe ser `> 0` y `<= 30`.
- `video`: extensión debe estar en `{mp4, webm, mov}` y tamaño `<= 50MB`.
- Si se envía `cita`: (1) la cita debe pertenecer al mismo `cliente`; (2) la cita debe tener `permite_carga_video=True`; (3) la cita debe estar activa (`RE`, no cancelada ni realizada).

### 10.4 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| POST | `subir/` | Paciente | Multipart: `cita?, video, duracion_segundos, descripcion?` — el `cliente` se toma del token |
| GET | `listar/?cliente=&cita=` | Profesional o Admin | Solo vigentes; si filtra por `cita` y quien pregunta es profesional, exige ser el dueño de esa cita |
| GET | `<id_video>/` | Profesional o Admin | 404 si venció o fue eliminado |
| DELETE | `<id_video>/eliminar/` | Profesional o Admin | Eliminación anticipada (`motivo_eliminacion='OM'`) |
| GET | `mis-videos/` | Paciente | Los videos vigentes del paciente autenticado |
| DELETE | `mis-videos/<id_video>/eliminar/` | Paciente | El paciente retira un video propio (`motivo_eliminacion='RP'`) |

---

## 11. Relación entre `PmCliente`, `PmCita` y `PmVideo`

1. Un paciente (`PmCliente`) puede tener múltiples citas y múltiples videos. Una cita conecta un paciente con **un** profesional (`PmCita.cliente` + `PmCita.profesional`, ambos `CASCADE`).
2. Todo video pertenece obligatoriamente a un paciente (`PmVideo.cliente`, `CASCADE`); la cita asociada es **opcional** (`PmVideo.cita`, `SET_NULL`) — una cita puede tener varios videos, o ninguno; un video pertenece como máximo a una cita.
3. Para poder asociar un video a una cita, esa cita debe permitir carga (`permite_carga_video=True`, que es el valor por defecto de toda cita) y estar aún activa (reservada, no cancelada ni ya realizada).
4. El video expira siempre a los 30 días **de su propia fecha de subida**, sin importar cuándo sea o fue la cita asociada.
5. Solo el profesional asignado a la cita (o un administrador) puede ver los videos ligados a ella; un profesional no puede ver videos de citas ajenas.

---

## 12. Deuda técnica conocida

Documentada aquí para que quien retome el código sepa qué falta, no para "denunciar" nada:

- **Comentarios de "rol máximo" desactualizados.** Varios `urls.py` de `PmMedico` documentan (en comentarios) que ciertas acciones administrativas requieren `is_superuser`, pero el permiso real aplicado (`EsAdministrador`) solo exige `is_staff`. Ver nota en [sección 6](#6-autenticación-y-autorización).

### 12.1 Deuda ya resuelta

- ~~**`PmCliente` no tiene login/JWT propio.**~~ **Resuelto.** `PmCliente` tiene sesión propia (`POST api/pm/clientes/login/`, token con el claim `id_cliente`, reconocido por `Security.authentication`) y el permiso `Security.permissions.EsCliente`. Como parte del mismo cambio se endurecieron los endpoints que antes eran públicos: los cuatro de paciente en `PmCita` (`reservar/`, `cliente/<id>/listar/`, cancelar y posponer), `cita_detalle` y la subida de video en `PmVideo` ahora exigen token de paciente y toman el dueño de `request.user`. El `id_cliente` ya no se acepta desde el body ni desde `?cliente=`, por lo que **conocer el id de otro paciente ya no permite operar sobre sus citas ni sus videos**.
- ~~**`PmCliente.rut_cliente` y `PmCliente.telefono_cliente` no tienen validación de formato.**~~ **Resuelto.** Ambos campos usan `Security.validators.validar_rut_chileno` y `validar_telefono`, igual que sus equivalentes en `PM_Profesional`, y el RUT se normaliza a mayúsculas para que el dígito verificador `K` no impida el inicio de sesión.

---

## 13. Tabla resumen de endpoints

| App | Prefijo | Público | Requiere JWT (Paciente) | Requiere JWT (Profesional) | Requiere JWT (Admin) |
|---|---|---|---|---|---|
| `PmMedico` | `api/pm/medicos/` | `registrar/`, `login/`, `directorio/`, `especialidades/listar/`, `<id>/especialidades/` | — | `perfil/*`, `documentos/subir/`, `documentos/<id>/eliminar/`, `especialidades/asignar/`, `especialidades/<id>/quitar/` | `listar/`, `<id>/`, `<id>/documentos/`, `documentos/<id>/validar/`, `acreditaciones/*`, `especialidades/crear/ editar/ eliminar/` |
| `PmCliente` | `api/pm/clientes/` | `registrar/`, `login/` | `perfil/`, `perfil/editar/`, `perfil/password/` | `listar/`, `<id>/` (compartido con Admin) | `<id>/editar/`, `<id>/eliminar/` |
| `PmCita` | `api/pm/citas/` | — | `reservar/`, `cliente/<id>/listar/`, `<id>/cliente/cancelar\|posponer/` | `profesional/listar/`, `<id>/profesional/*` | `listar/` |
| `PmVideo` | `api/pm/videos/` | — | `subir/`, `mis-videos/`, `mis-videos/<id>/eliminar/` | `listar/`, `<id>/`, `<id>/eliminar/` (compartido con Admin) | ídem |

`<id_cita>/` (detalle de cita) acepta las tres identidades autenticadas, siempre que sean parte de esa cita.

> Para el detalle de cada request/response, revisar la sección del módulo correspondiente más arriba o los comentarios en cada `urls.py`.
