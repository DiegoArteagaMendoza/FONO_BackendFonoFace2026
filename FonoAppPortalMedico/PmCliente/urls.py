from django.urls import path
from PmCliente import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/pm/clientes/registrar/
    # HEADERS: Ninguno (Acceso público)
    # BODY (JSON):
    # {
    #   "nombres_cliente": "Sebastian",
    #   "apellidos_clientes": "Jouannet",
    #   "rut_cliente": "12345678-9",
    #   "fecha_nacimiento_cliente": "1998-05-20",   <-- formato AAAA-MM-DD
    #   "email_cliente": "sebastian@correo.cl",
    #   "telefono_cliente": "+56912345678",
    #   "password": "minimo 8 caracteres"
    # }
    # RESPUESTA ESPERADA: El objeto JSON del cliente creado (Status 201).
    # -------------------------------------------------------------------------
    path('registrar/', views.cliente_registrar, name='cliente-registrar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/clientes/login/ | Acceso: público
    # BODY: {"identificador": "<correo o rut>", "password": "..."}
    # RESPUESTA: {"refresh": "...", "access": "...", "cliente": {...}}
    # -------------------------------------------------------------------------
    path('login/', views.cliente_login, name='cliente-login'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/clientes/perfil/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # RESPUESTA: Los datos del paciente autenticado.
    # -------------------------------------------------------------------------
    path('perfil/', views.cliente_perfil, name='cliente-perfil'),

    # -------------------------------------------------------------------------
    # MÉTODO: PATCH | URL: /api/pm/clientes/perfil/editar/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # BODY (parcial): nombres/apellidos/fecha_nacimiento/email/telefono
    # -------------------------------------------------------------------------
    path('perfil/editar/', views.cliente_perfil_editar, name='cliente-perfil-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT | URL: /api/pm/clientes/perfil/password/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # BODY: {"password_actual": "...", "password_nueva": "..."}
    # -------------------------------------------------------------------------
    path('perfil/password/', views.cliente_cambiar_password, name='cliente-cambiar-password'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/pm/clientes/listar/           (todos los activos)
    #      /api/pm/clientes/listar/?buscar=juan   (búsqueda por nombre/rut/correo)
    # HEADERS: Requiere autenticación
    # RESPUESTA ESPERADA: Arreglo JSON con los clientes activos.
    # -------------------------------------------------------------------------
    path('listar/', views.clientes_listar, name='clientes-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/pm/clientes/1/   <-- Reemplazar '1' por el id_cliente
    # HEADERS: Requiere autenticación
    # RESPUESTA ESPERADA: El objeto JSON del cliente.
    # -------------------------------------------------------------------------
    path('<int:id_cliente>/', views.cliente_detalle, name='cliente-detalle'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/pm/clientes/1/editar/
    # HEADERS: Requiere autenticación
    # BODY (JSON): Los campos a modificar, por ejemplo:
    # { "telefono_cliente": "+56987654321" }
    # RESPUESTA ESPERADA:
    # { "mensaje": "Cliente actualizado correctamente", "data": { ... } }
    # -------------------------------------------------------------------------
    path('<int:id_cliente>/editar/', views.cliente_editar, name='cliente-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/pm/clientes/1/eliminar/
    # HEADERS: Requiere autenticación
    # BODY: Ninguno
    # RESPUESTA ESPERADA (JSON):
    # { "mensaje": "Cliente eliminado correctamente" }
    # -------------------------------------------------------------------------
    path('<int:id_cliente>/eliminar/', views.cliente_eliminar, name='cliente-eliminar'),
]
