# DOCUMENTACIÓN DEL PROYECTO FONOAPP (BACKEND)

> Nota de alcance: este documento cubre el proyecto **FonoApp** y todas sus aplicaciones **excepto `FonoAppPortalMedico`**, que tiene su propio documento: [`FonoAppPortalMedico/DOCUMENTACION.md`](../FonoAppPortalMedico/DOCUMENTACION.md). Para la guía de despliegue a producción (hosting, CI/CD, migración a MySQL) de ambos proyectos, ver [`DOCUMENTACION_DESPLIEGUE.md`](../DOCUMENTACION_DESPLIEGUE.md) en la raíz del repositorio.

> Nota de estructura: este repositorio aloja **dos proyectos Django independientes** como carpetas hermanas en la raíz: `FonoApp/` (este proyecto, documentado aquí) y `FonoAppPortalMedico/` (proyecto aparte, no cubierto por este documento). Cada uno tiene su propio `manage.py` y su propio paquete de configuración (`FonoApp/FonoApp/settings.py` y `FonoAppPortalMedico/FonoAppPM/settings.py` respectivamente). El entorno virtual (`.venv/`), `docker-compose.yml` y `requirements.txt` son compartidos y viven en la raíz del repositorio, un nivel por encima de esta carpeta.

## Índice

1. [Descripción general](#1-descripción-general)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura y estructura de una app](#3-arquitectura-y-estructura-de-una-app)
4. [Puesta en marcha del proyecto](#4-puesta-en-marcha-del-proyecto)
5. [Configuración relevante (`FonoApp/settings.py`)](#5-configuración-relevante-fonoappsettingspy)
6. [Autenticación y autorización](#6-autenticación-y-autorización)
7. [Mapa de rutas raíz (`FonoApp/urls.py`)](#7-mapa-de-rutas-raíz-fonoappurlspy)
8. [Módulo `FonoAppAdministracion`](#8-módulo-fonoappadministracion)
9. [Módulo `FonoAppCuidados`](#9-módulo-fonoappcuidados)
10. [Módulo `FonoAppDiagnostico`](#10-módulo-fonoappdiagnostico)
11. [Módulo `FonoAppInfoGeneral`](#11-módulo-fonoappinfogeneral)
12. [Módulo `FonoAppInformacion`](#12-módulo-fonoappinformacion)
13. [Módulo `FonoAppNoticias`](#13-módulo-fonoappnoticias)
14. [Módulo `FonoAppVoz`](#14-módulo-fonoappvoz)
15. [Módulo compartido `FonoAppFunciones`](#15-módulo-compartido-fonoappfunciones)
16. [Tabla resumen de endpoints](#16-tabla-resumen-de-endpoints)

---

## 1. Descripción general

**FonoApp** es el backend de una plataforma orientada a fonoaudiología / salud vocal. Expone una API REST (Django + Django REST Framework) consumida por un frontend (Angular, puerto `4200` en desarrollo) que permite:

- Gestionar usuarios administradores y su autenticación (JWT).
- Publicar y administrar contenido informativo: cuidados de la voz, información general, noticias, contenido educativo sobre la voz.
- Gestionar banners de inicio y suscripciones a un newsletter.
- (En desarrollo) Un módulo de diagnóstico.

Todas las apps de contenido comparten el mismo patrón de diseño: borrado lógico mediante el campo `estado`, trazabilidad del usuario que crea el registro, y separación estricta de responsabilidades en 5 archivos (`models.py`, `queryset.py`, `serializer.py`, `views.py`, `urls.py`).

## 2. Stack tecnológico

| Componente | Detalle |
|---|---|
| Lenguaje / Framework | Python + Django 6.0.6 |
| API | Django REST Framework 3.17.1 |
| Autenticación | `djangorestframework-simplejwt` 5.5.1 (JWT custom, ver [sección 6](#6-autenticación-y-autorización)) |
| Base de datos | PostgreSQL 15 (vía Docker) |
| Imágenes | `Pillow` (conversión a WebP en algunos módulos) |
| CORS | `django-cors-headers` |
| Servidor de producción | `gunicorn` + `whitenoise` |
| Driver DB | `psycopg2-binary` |
| Variables de entorno | `python-dotenv` + `dj-database-url` (ver [sección 5.1](#51-variables-de-entorno)) |

## 3. Arquitectura y estructura de una app

Cada aplicación de contenido (`FonoAppCuidados`, `FonoAppInformacion`, `FonoAppNoticias`, `FonoAppInfoGeneral`, `FonoAppVoz`) sigue el mismo esqueleto:

```
FonoApp<Nombre>/
├── models.py       # Modelo(s) Django + Enum de categorías (TextChoices) + FK al usuario que registra
├── queryset.py      # Manager/QuerySet personalizado: listar, filtrar, crear, editar, eliminar (lógico)
├── serializer.py    # ModelSerializer de DRF, delega la creación al QuerySet
├── views.py         # Vistas basadas en función (@api_view), una por operación
├── urls.py           # Rutas con comentarios de método/headers/body/respuesta esperada
├── admin.py          # Vacío por convención (no se usa el admin de Django para estos modelos)
└── migrations/
```

Convenciones comunes a todas las apps:

- **Borrado lógico**: nunca se hace `DELETE` real; se marca `estado=False` mediante `eliminar_logico(...)` en el `QuerySet`.
- **Autor del registro**: casi todos los modelos tienen una FK `FonoApp_Administracion` hacia `settings.AUTH_USER_MODEL`, asignada automáticamente desde `request.user` en el `create()` del serializer (nunca la envía el cliente — está en `read_only_fields`).
- **Categorías/Enums**: se modelan con `models.TextChoices` y se exponen en la respuesta como un campo adicional `..._display` de solo lectura (`source='get_<campo>_display'`).
- **Imágenes**:
  - 1 imagen por registro (`ImageField` directo en el modelo): `FonoAppCuidados`, `FonoAppVoz`, banners de `FonoAppAdministracion`.
  - 0 a 4 imágenes por registro (modelo relacionado `*_Imagen` con FK): `FonoAppInformacion`, `FonoAppNoticias`. `FonoAppInformacion` además convierte las imágenes subidas a formato **WebP** antes de guardarlas.
- **Optimización de consultas**: los QuerySets exponen métodos `con_detalles()` que aplican `select_related`/`prefetch_related` para evitar el problema N+1 al listar con imágenes anidadas.
- **Vistas públicas vs. protegidas**: los `GET` de listado suelen ser `AllowAny` (contenido público del portal); todo lo que crea/edita/elimina requiere `CustomJWTAuthentication` + `IsAuthenticated`.

## 4. Puesta en marcha del proyecto

Requisitos: Python 3.14 (venv en `.venv/`, en la raíz del repositorio), Docker (para PostgreSQL).

Todos los comandos de Docker y de `pip` se ejecutan desde la **raíz del repositorio**; los comandos de `manage.py` se ejecutan desde **dentro de esta carpeta (`FonoApp/`)**.

```bash
# 1. Levantar la base de datos (PostgreSQL + pgAdmin) con Docker (desde la raíz del repo)
docker-compose up -d

# 2. Activar el entorno virtual e instalar dependencias (desde la raíz del repo)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Entrar a la carpeta de este proyecto
cd FonoApp

# 4. Variables de entorno (solo la primera vez)
cp .env.example .env

# 5. Migraciones
python manage.py makemigrations
python manage.py migrate

# 6. Levantar el servidor de desarrollo
python manage.py runserver
```

- PostgreSQL queda expuesto en `localhost:5432` (`fonoDevDB` / usuario `admin` / password `secret`, ver `docker-compose.yml` en la raíz del repo y `FonoApp/.env.example`).
- pgAdmin queda disponible en `http://localhost:5050`.
- Los archivos subidos (imágenes) se sirven en desarrollo desde `/media/` (carpeta física `FonoApp/media/`), gracias a `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` en `FonoApp/urls.py` cuando `DEBUG=True`.

## 5. Configuración relevante (`FonoApp/settings.py`)

- `AUTH_USER_MODEL = 'FonoAppAdministracion.FonoApp_Administracion'`: el modelo de usuario personalizado reemplaza al `User` de Django.
- `INSTALLED_APPS` se compone de `DEV_APPS` (apps propias del proyecto) + `BASE_APPS` (apps nativas de Django) + `FRAMEWORKS` (DRF, CORS, SimpleJWT).
- `CORS_ALLOWED_ORIGINS`: viene de la variable de entorno `CORS_ALLOWED_ORIGINS` (por defecto `http://localhost:4200`, el frontend Angular en desarrollo).
- `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` apunta a `FonoAppFunciones.authentication.CustomJWTAuthentication` (no al backend estándar de SimpleJWT).
- `SIMPLE_JWT`: `ACCESS_TOKEN_LIFETIME` / `REFRESH_TOKEN_LIFETIME` configurables vía `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` (por defecto 60 min / 1 día), y usa un claim custom `user_id` mapeado al campo `id_usuario` del modelo (`USER_ID_FIELD` / `USER_ID_CLAIM`).
- `RECAPTCHA_SECRET_KEY`: viene de la variable de entorno del mismo nombre; definido para una validación de reCAPTCHA en el login que actualmente está **comentada/deshabilitada** en `FonoAppAdministracion/views.py`.

### 5.1 Variables de entorno

Desde este refactor, `FonoApp/settings.py` ya no tiene valores sensibles ni de infraestructura *hardcodeados*: los lee desde variables de entorno (vía `python-dotenv`, cargando `FonoApp/.env` si existe; en un hosting real esas variables normalmente se configuran en el panel del proveedor y `.env` ni siquiera hace falta).

| Archivo | Se versiona en git | Uso |
|---|---|---|
| `FonoApp/.env` | **No** (en `.gitignore`) | Copia de trabajo real para desarrollo local. Se crea con `cp .env.example .env`. |
| `FonoApp/.env.example` | Sí | Plantilla de desarrollo, con los mismos valores que usa `docker-compose.yml`. |
| `FonoApp/.env.production.example` | Sí | Plantilla de referencia para cuando exista un despliegue. **Aún no hay un entorno de producción activo**; este archivo documenta qué variables habrá que definir (en el panel del proveedor de hosting o en los secretos del pipeline de CI/CD) y no debe copiarse a `.env` ni contener valores reales. |

Variables soportadas:

| Variable | Desarrollo (default) | Producción | Descripción |
|---|---|---|---|
| `SECRET_KEY` | clave de desarrollo incluida | **obligatoria**, única y secreta | Clave criptográfica de Django. |
| `DEBUG` | `True` | `False` | Activa/desactiva el modo debug de Django. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | dominio(s) reales de la API | Lista separada por comas. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:4200` | dominio(s) reales del frontend | Lista separada por comas. |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | valores de `docker-compose.yml` | — | Usadas solo si `DATABASE_URL` no está definida. |
| `DATABASE_URL` | *(sin usar en dev)* | URL de conexión (`postgres://usuario:pass@host:puerto/nombre`) | Si está definida, **tiene prioridad** sobre las `DB_*` (vía `dj_database_url`). Pensado para el proveedor de hosting que se elija a futuro. |
| `DATABASE_SSL_REQUIRE` | `False` (implícito, `DEBUG=True`) | `True` | Fuerza SSL en la conexión a la base de datos cuando se usa `DATABASE_URL`. |
| `RECAPTCHA_SECRET_KEY` | clave de pruebas incluida | clave real de producción | Ver [sección 6](#6-autenticación-y-autorización). |
| `JWT_ACCESS_MINUTES` / `JWT_REFRESH_DAYS` | `60` / `1` | a definir según política de seguridad | Duración de los tokens JWT. |

> El proyecto `FonoAppPortalMedico` **no** comparte este mecanismo: sigue usando valores hardcodeados en su propio `settings.py` y queda fuera del alcance de este documento.

## 6. Autenticación y autorización

Toda la autenticación pasa por una clase custom en `FonoAppFunciones/authentication.py`:

- **`CustomJWTAuthentication`**: lee el header `Authorization: Bearer <token>`, decodifica el `AccessToken` de `simplejwt`, extrae el claim `user_id` y busca al usuario en `FonoApp_Administracion` por `id_usuario`. Si el usuario no existe o tiene `estado=False` (inactivo), rechaza la autenticación. Si no hay header, retorna `None` (permite que rutas `AllowAny` sigan funcionando sin token).
- **`reCaptcha.captcha_verification(token)`**: helper para validar un token de Google reCAPTCHA contra la API oficial (actualmente sin uso activo en el flujo de login).

Flujo de login (`FonoAppAdministracion`):
1. `POST /api/usuarios/login/` con `{ "correo", "password" }`.
2. Se valida contra `FonoApp_Administracion.objects.validar_credenciales(...)` (verifica hash de password y que `estado=True`).
3. Se actualiza `last_conection` y se retorna `{ "refresh", "access", "user": {...} }`.
4. El frontend debe enviar el `access` token en cada petición protegida: `Authorization: Bearer <access>`.

## 7. Mapa de rutas raíz (`FonoApp/urls.py`)

| Prefijo | App |
|---|---|
| `api/usuarios/` | `FonoAppAdministracion` (usuarios + banners) |
| `api/noticias/` | `FonoAppNoticias` (noticias + newsletter) |
| `api/informacion/` | `FonoAppInformacion` |
| `api/cuidados/` | `FonoAppCuidados` |
| `api/info-general/` | `FonoAppInfoGeneral` |
| `api/voz/` | `FonoAppVoz` |
| `admin/` | Panel de administración de Django |

`FonoAppDiagnostico` está declarada en `INSTALLED_APPS` pero **no tiene rutas registradas** (ver [sección 10](#10-módulo-fonoappdiagnostico)).

---

## 8. Módulo `FonoAppAdministracion`

Gestiona los usuarios administradores del sistema (modelo de autenticación) y los banners del portal de inicio.

### 8.1 Modelo `FonoApp_Administracion`
Extiende `AbstractBaseUser` + `PermissionsMixin` (reemplaza al `User` de Django, `USERNAME_FIELD = 'email'`).

| Campo | Tipo | Notas |
|---|---|---|
| `id_usuario` | AutoField (PK) | |
| `nombre` | CharField(50) | |
| `rut` | CharField(12) | único |
| `email` | EmailField | único, se normaliza a minúsculas al crear |
| `tipo` | Boolean | distingue tipo de cuenta |
| `estado` | Boolean (default `True`) | activo/inactivo (borrado lógico) |
| `is_staff` / `is_active` | Boolean | permisos Django estándar |
| `last_conection` | DateTime | se actualiza en cada login |

### 8.2 Modelo `FonoApp_Banner_Inicio` + `FonoApp_Banner_Inicio_Imagenes`
Banner del home del portal, con **1 imagen** asociada vía modelo relacionado (`related_name='imagenes'`). Campos: `titulo`, `descripcion`, `fecha_creacion`, `fecha_actualizacion`, `estado`, FK al usuario que lo registró.

### 8.3 Endpoints — Usuarios (base `api/usuarios/`)

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| POST | `crear/` | Público | Registra un nuevo usuario administrador |
| GET | `listar/` | JWT | Lista todos los usuarios |
| POST | `login/` | Público | `{ "correo", "password" }` → tokens JWT |
| GET | `me/` | JWT | Perfil del usuario autenticado |
| DELETE | `<rut>/eliminar/` | JWT | Borrado lógico (`estado=False`) |
| PUT | `<rut>/actualizar-password/` | JWT | Cambia y encripta la contraseña |
| PATCH | `<rut>/editar/` | JWT | Actualiza `estado`, `is_staff` y/o `password` |

**Ejemplo — Crear usuario (POST `crear/`):**
```json
{
    "nombre": "Juan Pérez",
    "rut": "12345678-9",
    "email": "juan@ejemplo.com",
    "password": "mi_clave_secreta",
    "tipo": false,
    "estado": true,
    "is_staff": false
}
```

**Ejemplo — Login (POST `login/`):**
```json
{ "correo": "juan@ejemplo.com", "password": "mi_clave_secreta" }
```
Respuesta (200):
```json
{
    "refresh": "<jwt_refresh>",
    "access": "<jwt_access>",
    "user": { "nombre": "Juan Pérez", "email": "juan@ejemplo.com", "rut": "12345678-9" }
}
```

### 8.4 Endpoints — Banners (base `api/usuarios/banners/`)

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| GET | `listar/` | Público | Lista banners activos con su imagen |
| POST | `crear/` | JWT | Crea banner (FormData, máx. **1** imagen vía `imagenes_subidas`) |
| PATCH/PUT | `<id_banner>/editar/` | JWT | Edición parcial |
| DELETE | `<id_banner>/eliminar/` | JWT | Borrado lógico |

**Ejemplo — salida GET `banners/listar/`:**
```json
[
    {
        "id_banner": 1,
        "titulo": "Bienvenidos al portal",
        "descripcion": "Texto descriptivo...",
        "fecha_creacion": "2026-06-26T10:00:00Z",
        "fecha_actualizacion": "2026-06-26T10:00:00Z",
        "estado": true,
        "FonoApp_Administracion": 1,
        "imagenes": [
            { "id": 1, "imagen": "/media/banner/imagenes/foto.jpg", "fecha_subida": "2026-06-26T10:00:05Z" }
        ]
    }
]
```

---

## 9. Módulo `FonoAppCuidados`

Guías de cuidado de la voz, segmentadas por público objetivo. Endpoint base: `api/cuidados/`.

### 9.1 Modelo `FonoApp_Cuidados`

| Campo | Tipo | Notas |
|---|---|---|
| `id_cuidado` | AutoField (PK) | |
| `publico` | Choice | `NIÑOS`, `PROFESORES`, `CANTANTES_ACTORES`, `LOCUTORES`, `PUBLICO_GENERAL` (default) |
| `titulo` | CharField(150) | |
| `contenido` | TextField | |
| `img` | ImageField (opcional) | `cuidados/imagenes/` |
| `fuente` | URLField (opcional) | fuente científica |
| `estado` | Boolean | borrado lógico |
| `FonoApp_Administracion` | FK | autor |

### 9.2 Endpoints

| Método | Endpoint | Acceso |
|---|---|---|
| GET | `listar/` | Público |
| GET | `publico/<tipo_publico>/` | Público |
| POST | `crear/` | JWT (FormData si incluye `img`) |
| PUT/PATCH | `<id_cuidado>/editar/` | JWT |
| DELETE | `<id_cuidado>/eliminar/` | JWT |

**Ejemplo — GET `listar/`:**
```json
[
    {
        "id_cuidado": 1,
        "publico": "PUBLICO_GENERAL",
        "publico_display": "Público General",
        "titulo": "Hidratación constante",
        "contenido": "Es fundamental beber al menos 2 litros de agua diarios...",
        "img": "http://tu-dominio.com/media/cuidados/imagenes/agua.jpg",
        "fuente": "https://www.nidcd.nih.gov/es/salud/cuidado-de-la-voz",
        "estado": true,
        "FonoApp_Administracion": 1
    }
]
```

**Ejemplo — POST `crear/` (FormData):**
```javascript
const formData = new FormData();
formData.append('titulo', 'Descanso vocal');
formData.append('publico', 'LOCUTORES');
formData.append('contenido', 'Tomar pausas de silencio absoluto de 10 minutos cada hora de locución continua.');
formData.append('fuente', 'https://ejemplo.com/salud-vocal');
formData.append('img', archivoImagen); // opcional
```

*(Documentación detallada previa disponible también en `documentation_cuidados.md`.)*

---

## 10. Módulo `FonoAppDiagnostico`

**Estado: en desarrollo / no implementado.** La app solo contiene el esqueleto generado por `startapp` (`models.py` y `views.py` vacíos, sin `serializer.py`, `queryset.py`, `urls.py` ni migraciones). Está declarada en `INSTALLED_APPS` pero **no tiene rutas montadas** en `FonoApp/urls.py`, por lo que actualmente no expone ningún endpoint.

Cuando se implemente, se recomienda seguir el mismo patrón que el resto de los módulos (ver [sección 3](#3-arquitectura-y-estructura-de-una-app)).

---

## 11. Módulo `FonoAppInfoGeneral`

Textos dinámicos y configurables del portal (banners de texto, secciones editables), identificados por una `clave` única. Endpoint base: `api/info-general/`.

### 11.1 Modelo `FonoApp_InfoGeneral`

| Campo | Tipo | Notas |
|---|---|---|
| `id_info` | AutoField (PK) | |
| `seccion` | CharField(50) | agrupador, ej. `inicio`, `portal_cliente`, `footer` |
| `clave` | CharField(50), **única** | identificador único, ej. `inicio_cuidados` |
| `titulo` / `descripcion` / `enlace` | opcionales | contenido a mostrar |
| `estado` | Boolean | borrado lógico |
| `fecha_creacion` / `fecha_actualizacion` | DateTime | automáticas |
| `usuario_registro` | FK (`SET_NULL`) | autor, se conserva el registro aunque se borre el usuario |

### 11.2 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| GET | `publico/` (query opcional `?seccion=`) | Público | Textos activos, filtrables por sección |
| GET | `listar/` | JWT | Todos los registros (incluye inactivos), para panel admin |
| POST | `crear/` | JWT | Crea un bloque de texto |
| PATCH/PUT | `<id_info>/editar/` | JWT | Edición parcial |
| DELETE | `<id_info>/eliminar/` | JWT | Borrado lógico |

**Ejemplo — POST `crear/`:**
```json
{
    "seccion": "inicio",
    "clave": "inicio_cuidados",
    "titulo": "Cuidados Vocales",
    "descripcion": "Recomendaciones específicas para profesores...",
    "enlace": "/portal/cuidados"
}
```

---

## 12. Módulo `FonoAppInformacion`

Contenido informativo general categorizado, con hasta 4 imágenes por registro (convertidas automáticamente a WebP). Endpoint base: `api/informacion/`.

### 12.1 Modelo `FonoApp_Informacion` + `FonoApp_Informacion_Imagen`

| Campo | Tipo | Notas |
|---|---|---|
| `id_informacion` | AutoField (PK) | |
| `titulo` | CharField(150) | |
| `categoria` | Choice (2 chars) | `PO` Promoción, `PE` Prevención, `GE` General, `FA` Fármacos |
| `contenido` | TextField | |
| `fecha_creacion` / `fecha_actualizacion` | DateTime | automáticas |
| `estado` | Boolean | borrado lógico |
| `FonoApp_Administracion` | FK | autor |
| `imagenes` | related (0–4) | `FonoApp_Informacion_Imagen`, convertidas a `.webp` al subirlas |

### 12.2 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| GET | `listar/` (query opcional `?categoria=`) | Público | Lista optimizada (`select_related`/`prefetch_related`) |
| POST | `crear/` | JWT | FormData, hasta 4 imágenes en `imagenes_subidas` (solo JPG/PNG) |
| PUT/PATCH | `<id_informacion>/editar/` | JWT | Solo campos de texto (no gestiona imágenes) |
| DELETE | `<id_informacion>/eliminar/` | JWT | Borrado lógico |

**Ejemplo — GET `listar/?categoria=PE`:**
```json
[
    {
        "id_informacion": 1,
        "titulo": "Prevención de disfonías",
        "categoria": "PE",
        "categoria_display": "Prevencion",
        "contenido": "...",
        "fecha_creacion": "2026-06-15T10:30:00Z",
        "fecha_actualizacion": "2026-06-15T10:30:00Z",
        "estado": true,
        "FonoApp_Administracion": 2,
        "imagenes": [
            { "id": 1, "imagen": "http://tu-dominio.com/media/informacion/imagenes/img1.webp", "fecha_subida": "2026-06-15T10:30:05Z" }
        ]
    }
]
```

*(Documentación detallada previa disponible también en `documentation_informacion.md`.)*

---

## 13. Módulo `FonoAppNoticias`

Noticias del portal (con imágenes) y suscripciones a un newsletter. Endpoint base: `api/noticias/`.

### 13.1 Modelo `FonoApp_Noticias` + `FonoApp_Noticia_Imagen`
Igual patrón que `FonoAppInformacion` pero sin categoría y **sin** conversión a WebP: `titulo`, `contenido`, `fecha_creacion`, `fecha_actualizacion`, `estado`, FK autor, hasta 4 imágenes relacionadas.

### 13.2 Modelo `FonoApp_Newsletter`
`email` (único), `fecha_suscripcion`, `estado` (permite reactivar una suscripción dada de baja en vez de duplicarla).

### 13.3 Endpoints

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| GET | `listar/` | Público | Noticias activas con imágenes |
| POST | `crear/` | JWT | FormData, hasta 4 imágenes |
| PUT/PATCH | `<id_noticia>/editar/` | JWT | Título y/o contenido |
| DELETE | `<id_noticia>/eliminar/` | JWT | Borrado lógico |
| POST | `<id_noticia>/imagenes/agregar/` | JWT | Agrega imágenes a una noticia existente (respeta el límite de 4) |
| DELETE | `imagenes/<id_imagen>/eliminar/` | JWT | Borra físicamente una imagen y su registro |
| POST | `newsletter/suscribir/` | Público | `{ "email": "..." }`, reactiva si ya existía inactiva |

**Ejemplo — POST `crear/` (FormData):**
```javascript
const formData = new FormData();
formData.append('titulo', 'Campaña de tamizaje auditivo');
formData.append('contenido', 'Este fin de semana estaremos realizando...');
formData.append('imagenes_subidas', archivoFile1); // opcional, hasta 4
```

**Ejemplo — POST `newsletter/suscribir/`:**
```json
{ "email": "visitante@correo.com" }
```
Respuesta (201): `{ "mensaje": "Suscripción registrada correctamente" }`

---

## 14. Módulo `FonoAppVoz`

Contenido educativo sobre qué es la voz (definición, anatomía, fisiología, trastornos), con imagen y fuente científica por registro. Endpoint base: `api/voz/`.

### 14.1 Modelo `FonoApp_Voz`

| Campo | Tipo | Notas |
|---|---|---|
| `id_voz` | AutoField (PK) | |
| `categoria` | Choice | `DEFINICION` (default), `ANATOMIA`, `FISIOLOGIA`, `TRASTORNOS`, `IMPORTANCIA`, `CURIOSIDADES` |
| `titulo` | CharField(150) | |
| `contenido` | TextField | |
| `img` | ImageField (opcional) | `voz/imagenes/` |
| `fuente` | URLField (opcional) | cita científica |
| `estado` | Boolean | borrado lógico |
| `FonoApp_Administracion` | FK | autor |

### 14.2 Endpoints

| Método | Endpoint | Acceso |
|---|---|---|
| GET | `listar/` | Público |
| GET | `categoria/<tipo_categoria>/` | Público |
| POST | `crear/` | JWT (FormData si incluye `img`) |
| PUT/PATCH | `<id_voz>/editar/` | JWT |
| DELETE | `<id_voz>/eliminar/` | JWT |

**Ejemplo — GET `categoria/anatomia/`:**
```json
[
    {
        "id_voz": 2,
        "categoria": "ANATOMIA",
        "categoria_display": "Anatomía",
        "titulo": "Las cuerdas vocales",
        "contenido": "Las cuerdas vocales son dos bandas de tejido muscular ubicadas en la laringe...",
        "img": "http://tu-dominio.com/media/voz/imagenes/laringe.jpg",
        "fuente": "https://www.nidcd.nih.gov/es/salud/voz",
        "estado": true,
        "FonoApp_Administracion": 1
    }
]
```

**Ejemplo — POST `crear/` (FormData):**
```javascript
const formData = new FormData();
formData.append('titulo', '¿Qué es la voz?');
formData.append('categoria', 'DEFINICION');
formData.append('contenido', 'La voz es el sonido producido por la vibración de las cuerdas vocales al paso del aire espirado.');
formData.append('fuente', 'https://ejemplo.com/definicion-voz');
formData.append('img', archivoImagen); // opcional
```

---

## 15. Módulo compartido `FonoAppFunciones`

No es una app de contenido: no tiene modelos, migraciones ni rutas propias. Contiene utilidades reutilizadas por el resto de las apps, en `authentication.py`:

- `CustomJWTAuthentication` (ver [sección 6](#6-autenticación-y-autorización)).
- `reCaptcha.captcha_verification(token)`.

---

## 16. Tabla resumen de endpoints

| App | Prefijo | Público (GET) | Requiere JWT |
|---|---|---|---|
| FonoAppAdministracion | `api/usuarios/` | `login/`, `banners/listar/` | `crear/`, `listar/`, `me/`, `<rut>/eliminar/`, `<rut>/actualizar-password/`, `<rut>/editar/`, `banners/crear/`, `banners/<id>/editar/`, `banners/<id>/eliminar/` |
| FonoAppCuidados | `api/cuidados/` | `listar/`, `publico/<tipo>/` | `crear/`, `<id>/editar/`, `<id>/eliminar/` |
| FonoAppDiagnostico | — | *(sin rutas montadas, módulo pendiente)* | — |
| FonoAppInfoGeneral | `api/info-general/` | `publico/` | `listar/`, `crear/`, `<id>/editar/`, `<id>/eliminar/` |
| FonoAppInformacion | `api/informacion/` | `listar/` | `crear/`, `<id>/editar/`, `<id>/eliminar/` |
| FonoAppNoticias | `api/noticias/` | `listar/`, `newsletter/suscribir/` (POST) | `crear/`, `<id>/editar/`, `<id>/eliminar/`, `<id>/imagenes/agregar/`, `imagenes/<id>/eliminar/` |
| FonoAppVoz | `api/voz/` | `listar/`, `categoria/<tipo>/` | `crear/`, `<id>/editar/`, `<id>/eliminar/` |

> Para el detalle de cada request/response, revisar la sección del módulo correspondiente más arriba (o los comentarios en cada `urls.py`, que documentan método, headers, body y respuesta esperada endpoint por endpoint).
