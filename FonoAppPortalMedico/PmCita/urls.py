from django.urls import path
from PmCita import views

urlpatterns = [
    # =====================================================================
    # RESERVA Y GESTIÓN DEL LADO DEL CLIENTE
    # Todas requieren Bearer <token paciente> (PmCliente ya tiene sesión
    # propia). El dueño de la cita se toma del token, así que el id_cliente
    # ya NO viaja en el cuerpo de la petición.
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/citas/reservar/
    # Acceso: con o sin sesión de paciente.
    #   - Con Bearer <token paciente>: BODY {"id_disponibilidad",
    #     "motivo_consulta" (opcional)}. El dueño sale del token.
    #   - Sin sesión: además "paciente": {"nombres_cliente",
    #     "apellidos_clientes","rut_cliente","fecha_nacimiento_cliente",
    #     "email_cliente","telefono_cliente"}. Con esos datos se crea o se
    #     recupera su ficha; si el RUT ya tiene cuenta con contraseña, se
    #     responde 400 pidiendo iniciar sesión.
    # La fecha y la duración NO se envían: salen del bloque publicado.
    # RESPUESTA: el JSON de la cita creada más "reservada_sin_sesion" (201).
    path('reservar/', views.cita_reservar, name='cita-reservar'),

    # MÉTODO: GET | URL: /api/pm/citas/cliente/<id_cliente>/listar/
    #                     /api/pm/citas/cliente/<id_cliente>/listar/?proximas=true
    # Requiere: Bearer <token paciente>. El id_cliente de la URL debe ser el
    # del propio token; si no, responde 403. Sin el filtro, entrega todo el
    # historial (incluye canceladas y realizadas).
    path('cliente/<int:id_cliente>/listar/', views.citas_cliente_listar, name='citas-cliente-listar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/cliente/cancelar/
    # Requiere: Bearer <token paciente (dueño de la cita)>
    # BODY: {"motivo" (opcional)}
    # RESPUESTA: la cita con estado "CC" (Cancelada por el cliente).
    path('<int:id_cita>/cliente/cancelar/', views.cita_cliente_cancelar, name='cita-cliente-cancelar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/cliente/posponer/
    # Requiere: Bearer <token paciente (dueño de la cita)>
    # BODY: {"fecha_hora" (nueva, ISO 8601), "motivo" (opcional)}
    # RESPUESTA: la cita con la nueva fecha_hora.
    path('<int:id_cita>/cliente/posponer/', views.cita_cliente_posponer, name='cita-cliente-posponer'),

    # =====================================================================
    # GESTIÓN DEL LADO DEL PROFESIONAL
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/citas/profesional/listar/
    #                     /api/pm/citas/profesional/listar/?proximas=true
    # Requiere: Bearer <token profesional>
    path('profesional/listar/', views.citas_profesional_listar, name='citas-profesional-listar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/profesional/cancelar/
    # Requiere: Bearer <token profesional (dueño de la cita)>
    # BODY: {"motivo" (opcional)} | RESPUESTA: la cita con estado "CM".
    path('<int:id_cita>/profesional/cancelar/', views.cita_profesional_cancelar, name='cita-profesional-cancelar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/profesional/posponer/
    # Requiere: Bearer <token profesional (dueño de la cita)>
    # BODY: {"fecha_hora" (nueva, ISO 8601), "motivo" (opcional)}
    path('<int:id_cita>/profesional/posponer/', views.cita_profesional_posponer, name='cita-profesional-posponer'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/profesional/marcar-realizada/
    # Requiere: Bearer <token profesional (dueño de la cita)> | BODY: ninguno
    # RESPUESTA: la cita con estado "RZ".
    path(
        '<int:id_cita>/profesional/marcar-realizada/',
        views.cita_profesional_marcar_realizada,
        name='cita-profesional-marcar-realizada',
    ),

    # =====================================================================
    # DETALLE Y ADMINISTRACIÓN
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/citas/<id_cita>/
    # Requiere: Bearer <token del paciente dueño, del profesional que atiende
    # o de un administrador>. Cualquier otra identidad recibe 403.
    path('<int:id_cita>/', views.cita_detalle, name='cita-detalle'),

    # MÉTODO: GET | URL: /api/pm/citas/listar/?cliente=1&profesional=3&estado=RE
    # Requiere: Bearer <token administrador> | Todos los filtros son opcionales.
    path('listar/', views.citas_listar, name='citas-listar'),

    # =====================================================================
    # DISPONIBILIDAD
    # Horas que el profesional publica para que los pacientes las reserven.
    # El paciente ya no propone una fecha libre: elige uno de estos bloques.
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/citas/disponibilidad/publicar/
    # Requiere: Bearer <token profesional>
    # BODY: {"fechas_hora": ["2026-09-01T10:00:00Z", ...] (máx. 100),
    #        "duracion_minutos" (opcional, por defecto 45)}
    # RESPUESTA: {"creados": [...], "rechazados": [{"fecha_hora","motivo"}]}.
    # Cada bloque se evalúa por separado: uno rechazado no anula los demás.
    path('disponibilidad/publicar/', views.disponibilidad_publicar, name='disponibilidad-publicar'),

    # MÉTODO: GET | URL: /api/pm/citas/disponibilidad/mias/
    #                     /api/pm/citas/disponibilidad/mias/?todas=true
    # Requiere: Bearer <token profesional>. Sin el filtro entrega solo las
    # futuras; con ?todas=true incluye las que ya pasaron.
    path('disponibilidad/mias/', views.disponibilidad_mia, name='disponibilidad-mias'),

    # MÉTODO: DELETE | URL: /api/pm/citas/disponibilidad/<id>/retirar/
    # Requiere: Bearer <token profesional dueño del bloque>
    # Baja lógica. Un bloque ya reservado NO se puede retirar: responde 400
    # pidiendo cancelar la cita, que sí queda registrada con su motivo.
    path(
        'disponibilidad/<int:id_disponibilidad>/retirar/',
        views.disponibilidad_retirar,
        name='disponibilidad-retirar',
    ),

    # MÉTODO: GET | URL: /api/pm/citas/disponibilidad/profesional/<id>/
    # Acceso: público (se puede reservar sin cuenta). Entrega solo los bloques
    # reservables: libres y con la anticipación mínima por delante. No expone
    # qué horas están ocupadas ni por quién.
    path(
        'disponibilidad/profesional/<int:id_profesional>/',
        views.disponibilidad_de_profesional,
        name='disponibilidad-de-profesional',
    ),

    # =====================================================================
    # SEGUIMIENTO POR CÓDIGO
    # Para quien reservó sin cuenta: el código que recibió por correo hace de
    # credencial, por eso son públicas. Ver la nota en views.py.
    # =====================================================================

    # MÉTODO: GET | URL: /api/pm/citas/seguimiento/<codigo>/
    # Acceso: público (el código es la autorización).
    # RESPUESTA: detalle legible de la cita, sin ids internos. 404 si no existe.
    path('seguimiento/<str:codigo>/', views.cita_seguimiento, name='cita-seguimiento'),

    # MÉTODO: PATCH | URL: /api/pm/citas/seguimiento/<codigo>/cancelar/
    # BODY: {"motivo" (opcional)} | Cuenta como cancelación del cliente ("CC").
    path(
        'seguimiento/<str:codigo>/cancelar/',
        views.cita_seguimiento_cancelar,
        name='cita-seguimiento-cancelar',
    ),

    # MÉTODO: PATCH | URL: /api/pm/citas/seguimiento/<codigo>/posponer/
    # BODY: {"fecha_hora" (nueva, ISO 8601), "motivo" (opcional)}
    path(
        'seguimiento/<str:codigo>/posponer/',
        views.cita_seguimiento_posponer,
        name='cita-seguimiento-posponer',
    ),
]
