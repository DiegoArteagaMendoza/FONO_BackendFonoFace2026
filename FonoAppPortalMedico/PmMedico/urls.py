from django.urls import path
from PmMedico import views

urlpatterns = [
    # =====================================================================
    # PROFESIONAL — registro, sesión y perfil propio
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/medicos/registrar/ | Acceso: público
    # BODY: {"nombres_profesional","apellidos_profesional","rut_profesional",
    #        "email_profesional","telefono_profesional","password",
    #        "numero_registro_salud_profesional" (opcional)}
    # Crea el profesional y abre su acreditación en PENDIENTE.
    path('registrar/', views.profesional_registrar, name='profesional-registrar'),

    # MÉTODO: POST | URL: /api/pm/medicos/login/ | Acceso: público
    # BODY: {"identificador": "<email o rut>", "password": "..."}
    # RESPUESTA: {"refresh": "...", "access": "...", "profesional": {...}}
    path('login/', views.profesional_login, name='profesional-login'),

    # MÉTODO: GET | URL: /api/pm/medicos/perfil/ | Requiere: Bearer <token profesional>
    path('perfil/', views.profesional_perfil, name='profesional-perfil'),

    # MÉTODO: PATCH | URL: /api/pm/medicos/perfil/editar/ | Requiere: Bearer <token profesional>
    # BODY (parcial): nombres/apellidos/email/telefono/numero_registro_salud_profesional
    path('perfil/editar/', views.profesional_perfil_editar, name='profesional-perfil-editar'),

    # MÉTODO: PUT | URL: /api/pm/medicos/perfil/password/ | Requiere: Bearer <token profesional>
    # BODY: {"password_actual": "...", "password_nueva": "..."}
    path('perfil/password/', views.profesional_cambiar_password, name='profesional-cambiar-password'),

    # MÉTODO: DELETE | URL: /api/pm/medicos/perfil/eliminar/ | Requiere: Bearer <token profesional>
    # Baja lógica de la cuenta propia.
    path('perfil/eliminar/', views.profesional_eliminar, name='profesional-eliminar'),

    # =====================================================================
    # PROFESIONAL — consultas administrativas y directorio público
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/medicos/listar/?estado_verificacion=PENDIENTE
    # Requiere: Bearer <token administrador FonoApp>
    path('listar/', views.profesional_listar, name='profesional-listar'),

    # MÉTODO: GET | URL: /api/pm/medicos/<id_profesional>/ | Requiere: Bearer <token administrador>
    path('<int:id_profesional>/', views.profesional_detalle, name='profesional-detalle'),

    # MÉTODO: GET | URL: /api/pm/medicos/directorio/ | Acceso: público
    # Solo profesionales activos con acreditación APROBADA.
    path('directorio/', views.profesional_directorio, name='profesional-directorio'),

    # =====================================================================
    # DOCUMENTOS DE RESPALDO
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/medicos/documentos/subir/ | Requiere: Bearer <token profesional>
    # BODY (multipart/form-data): tipo_documeto_profesional, url_documento_profesional (archivo)
    path('documentos/subir/', views.documento_subir, name='documento-subir'),

    # MÉTODO: DELETE | URL: /api/pm/medicos/documentos/<id_documento>/eliminar/
    # Requiere: Bearer <token profesional> (dueño, y solo si aún no fue validado)
    path('documentos/<int:id_documento>/eliminar/', views.documento_eliminar, name='documento-eliminar'),

    # MÉTODO: GET | URL: /api/pm/medicos/<id_profesional>/documentos/
    # Requiere: Bearer <token administrador>
    path('<int:id_profesional>/documentos/', views.profesional_documentos_listar, name='profesional-documentos-listar'),

    # MÉTODO: PATCH | URL: /api/pm/medicos/documentos/<id_documento>/validar/
    # Requiere: Bearer <token administrador con rol máximo>
    # BODY: {"documento_profesional_valido": true|false}
    path('documentos/<int:id_documento>/validar/', views.documento_validar, name='documento-validar'),

    # =====================================================================
    # ACREDITACIÓN
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/medicos/acreditaciones/pendientes/
    # Requiere: Bearer <token administrador>
    path('acreditaciones/pendientes/', views.acreditacion_pendientes, name='acreditacion-pendientes'),

    # MÉTODO: GET | URL: /api/pm/medicos/acreditaciones/<id_profesional>/estado/
    # Requiere: Bearer <token del propio profesional o de un administrador>
    path('acreditaciones/<int:id_profesional>/estado/', views.acreditacion_estado, name='acreditacion-estado'),

    # MÉTODO: PATCH | URL: /api/pm/medicos/acreditaciones/<id_acreditacion>/resolver/
    # Requiere: Bearer <token administrador con rol máximo (is_superuser) de FonoApp>
    # BODY: {"estado_verificacion_profesional": "APROBADO" | "RECHAZADO"}
    path('acreditaciones/<int:id_acreditacion>/resolver/', views.acreditacion_resolver, name='acreditacion-resolver'),

    # =====================================================================
    # ESPECIALIDAD (catálogo)
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/medicos/especialidades/listar/ | Acceso: público
    path('especialidades/listar/', views.especialidad_listar, name='especialidad-listar'),

    # MÉTODO: POST | URL: /api/pm/medicos/especialidades/crear/
    # Requiere: Bearer <token administrador con rol máximo>
    path('especialidades/crear/', views.especialidad_crear, name='especialidad-crear'),

    # MÉTODO: PUT/PATCH | URL: /api/pm/medicos/especialidades/<id_especialidad>/editar/
    # Requiere: Bearer <token administrador con rol máximo>
    path('especialidades/<int:id_especialidad>/editar/', views.especialidad_editar, name='especialidad-editar'),

    # MÉTODO: DELETE | URL: /api/pm/medicos/especialidades/<id_especialidad>/eliminar/
    # Requiere: Bearer <token administrador con rol máximo>
    path('especialidades/<int:id_especialidad>/eliminar/', views.especialidad_eliminar, name='especialidad-eliminar'),

    # =====================================================================
    # ESPECIALIDADES DEL PROFESIONAL (autogestión N:M)
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/medicos/especialidades/asignar/ | Requiere: Bearer <token profesional>
    # BODY: {"id_especialidad": <int>}
    path('especialidades/asignar/', views.profesional_especialidad_asignar, name='profesional-especialidad-asignar'),

    # MÉTODO: DELETE | URL: /api/pm/medicos/especialidades/<id_especialidad>/quitar/
    # Requiere: Bearer <token profesional>
    path('especialidades/<int:id_especialidad>/quitar/', views.profesional_especialidad_quitar, name='profesional-especialidad-quitar'),

    # MÉTODO: GET | URL: /api/pm/medicos/<id_profesional>/especialidades/ | Acceso: público
    # (solo si el profesional ya está verificado)
    path('<int:id_profesional>/especialidades/', views.profesional_especialidades_listar, name='profesional-especialidades-listar'),
]
