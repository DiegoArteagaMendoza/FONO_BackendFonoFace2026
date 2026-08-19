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
    # Requiere: Bearer <token paciente>
    # BODY: {"id_profesional","fecha_hora" (ISO 8601, con anticipación
    #        mínima), "motivo_consulta" (opcional),
    #        "duracion_minutos" (opcional, por defecto 45)}
    # RESPUESTA: el objeto JSON de la cita creada (Status 201).
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
]
