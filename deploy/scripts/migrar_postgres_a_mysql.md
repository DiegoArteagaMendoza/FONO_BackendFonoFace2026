# Migrar de PostgreSQL a MySQL

Hay dos escenarios muy distintos. Lee primero cuál te aplica — casi siempre es el primero.

## Escenario A — Base nueva, sin datos que conservar (el caso normal para el primer despliegue)

Hoy no existe un entorno de producción activo (ver `FonoApp/.env.production.example` y
`DOCUMENTACION_DESPLIEGUE.md`). Si vas a desplegar por primera vez, **no hay nada que migrar**:
solo necesitas crear una base MySQL vacía en cPanel y correr las migraciones de Django sobre ella.

```bash
# En el servidor (o localmente contra una BD MySQL de prueba), con el virtualenv activo
# y DB_ENGINE=mysql / DATABASE_URL apuntando a la base MySQL:
python manage.py migrate
python manage.py createsuperuser   # crea el primer administrador de FonoApp
```

Repetir para los dos proyectos (`FonoApp` y `FonoAppPortalMedico`), apuntando ambos a la
**misma** base de datos MySQL (igual que hoy comparten la misma base Postgres — ver
`FonoAppPortalMedico/DOCUMENTACION.md` §6). Basta con migrar `FonoApp` primero (crea
`FonoApp_Administracion`, la tabla que `PmMedico.Administrador` lee como no-gestionada) y
luego `FonoAppPortalMedico`.

Esto cubre el 100% de lo que necesitas para el primer despliegue en V2Networks.

## Escenario B — Ya sembraste datos de prueba en Postgres (dev) y quieres llevarlos a MySQL

Aplica si, por ejemplo, quieres conservar contenido cargado en desarrollo (noticias, cuidados,
profesionales de prueba, etc.) al pasar a la base MySQL de producción. Dos formas de hacerlo:

### Opción 1 — `dumpdata` / `loaddata` de Django (recomendada, sin herramientas externas)

1. Con la base Postgres de origen activa, exportar cada proyecto por separado (evita mezclar
   `contenttypes`/`auth.permission`, que Django regenera solo y que pueden chocar entre motores):

   ```bash
   # Dentro de FonoApp/
   python manage.py dumpdata \
     --natural-foreign --natural-primary \
     --exclude auth.permission --exclude contenttypes \
     -o fonoapp_dump.json

   # Dentro de FonoAppPortalMedico/ (ojo: PmMedico.Administrador es managed=False,
   # no se exporta ni se importa desde acá — viaja con el dump de FonoApp)
   python manage.py dumpdata \
     --natural-foreign --natural-primary \
     --exclude auth.permission --exclude contenttypes \
     -o portalmedico_dump.json
   ```

2. Cambiar la configuración de conexión a la base MySQL nueva (`DATABASE_URL` o `DB_*`, ver
   `deploy/mysql/env.production.*.mysql.example`) y correr `migrate` sobre ella (tabla vacía,
   Escenario A).

3. Cargar los dumps, **en orden** (`FonoApp` primero, porque `PmMedico`/`PmCita`/`PmVideo`
   tienen FKs lógicas hacia `FonoApp_Administracion`):

   ```bash
   # Dentro de FonoApp/
   python manage.py loaddata fonoapp_dump.json

   # Dentro de FonoAppPortalMedico/
   python manage.py loaddata portalmedico_dump.json
   ```

4. Verificar conteos (`python manage.py shell` → `Modelo.objects.count()` en origen vs. destino)
   y probar login/endpoints clave antes de dar por cerrada la migración.

5. Los archivos subidos (`media/`) no viajan en el dump: copiarlos aparte (rsync/scp) desde
   `FonoApp/media/` y `FonoAppPortalMedico/media/` hacia las mismas rutas en el servidor. Los
   registros en BD (`ImageField`/`FileField`) solo guardan la ruta relativa, así que basta con
   que el archivo físico exista en el mismo `MEDIA_ROOT` de destino.

### Opción 2 — `pgloader` (más rápida para volúmenes grandes, requiere instalar la herramienta)

[`pgloader`](https://github.com/dimitri/pgloader) migra directo de Postgres a MySQL a nivel de
filas SQL, sin pasar por Django. Es más veloz para datasets grandes, pero no es necesaria para
el tamaño de datos de este proyecto en esta etapa — se documenta como alternativa, no como
recomendación por defecto. Requiere correrla desde una máquina con acceso de red a ambas bases
(normalmente no es viable directo desde cPanel compartido; se corre en local o en un servidor
intermedio, y luego se sube el resultado). Si se opta por esta vía, seguir la documentación
oficial de pgloader para el modo `mysql-database` como destino.

## Cosas a verificar después de migrar (cualquiera de los dos escenarios)

- **Charset**: todas las tablas deben quedar en `utf8mb4` (ver `deploy/mysql/db_engine_snippet.py`,
  que ya fuerza `OPTIONS={'charset': 'utf8mb4'}`). Si una tabla quedó en `utf8` a secas, tildes/ñ
  en campos de texto libre (`contenido`, `descripcion`, etc.) pueden guardarse mal.
- **Login administrador**: probar `POST /api/usuarios/login/` en `FonoApp` y luego usar ese token
  para un endpoint admin de `FonoAppPortalMedico` (ej. `GET /api/pm/medicos/listar/`) — confirma
  que el `SECRET_KEY` compartido y la tabla `FonoApp_Administracion` migraron correctamente.
- **Secuencias/autoincrement**: Django + MySQL usan `AUTO_INCREMENT` nativo, no requiere el ajuste
  manual de secuencias que a veces hace falta al migrar *hacia* Postgres; no debería haber nada
  que hacer acá, pero si cargaste datos con `loaddata` y los IDs quedan "atascados" en el último
  valor cargado, es el comportamiento esperado (no es un bug).
- **No hay campos específicos de Postgres en este proyecto** (`ArrayField`, `JSONField`,
  `HStoreField`, etc. — verificado, ningún modelo los usa), así que no hay incompatibilidades de
  tipos de datos que resolver.
