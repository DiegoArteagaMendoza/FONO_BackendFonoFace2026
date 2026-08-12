from django.urls import path
from PmCita import views

urlpatterns = [
    # =====================================================================
    # RESERVA Y GESTIÓN DEL LADO DEL CLIENTE
    # (sin sesión propia todavía; ver TODO en views.py)
    # =====================================================================

    # MÉTODO: POST | URL: /api/pm/citas/reservar/ | Acceso: público
    # BODY: {"id_cliente","id_profesional","fecha_hora" (ISO 8601, con
    #        anticipación mínima), "motivo_consulta" (opcional),
    #        "duracion_minutos" (opcional, por defecto 45)}
    # RESPUESTA: el objeto JSON de la cita creada (Status 201).
    path('reservar/', views.cita_reservar, name='cita-reservar'),

    # MÉTODO: GET | URL: /api/pm/citas/cliente/<id_cliente>/listar/
    #                     /api/pm/citas/cliente/<id_cliente>/listar/?proximas=true
    # Acceso: público (ver TODO). Sin el filtro, entrega todo el historial.
    path('cliente/<int:id_cliente>/listar/', views.citas_cliente_listar, name='citas-cliente-listar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/cliente/cancelar/ | Acceso: público (ver TODO)
    # BODY: {"id_cliente", "motivo" (opcional)}
    # RESPUESTA: la cita con estado "CC" (Cancelada por el cliente).
    path('<int:id_cita>/cliente/cancelar/', views.cita_cliente_cancelar, name='cita-cliente-cancelar'),

    # MÉTODO: PATCH | URL: /api/pm/citas/<id_cita>/cliente/posponer/ | Acceso: público (ver TODO)
    # BODY: {"id_cliente", "fecha_hora" (nueva, ISO 8601), "motivo" (opcional)}
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
    #                     /api/pm/citas/<id_cita>/?cliente=<id_cliente>  (acceso del propio cliente)
    # Requiere: Bearer <token profesional dueño o administrador>, EXCEPTO
    # cuando se accede con ?cliente=<id> (ver TODO en views.py).
    path('<int:id_cita>/', views.cita_detalle, name='cita-detalle'),

    # MÉTODO: GET | URL: /api/pm/citas/listar/?cliente=1&profesional=3&estado=RE
    # Requiere: Bearer <token administrador> | Todos los filtros son opcionales.
    path('listar/', views.citas_listar, name='citas-listar'),
]
