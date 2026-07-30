from django.urls import path
from . import views

urlpatterns = [
    # =========================================================================
    # ENDPOINT PÚBLICO
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/info-general/publico/ (Puede incluir query param: ?seccion=inicio)
    # HEADERS: Ninguno (Acceso libre / AllowAny)
    # BODY: Ninguno
    # USO: Retorna una lista JSON con los textos activos. Si se envía 
    #      el parámetro '?seccion=', filtrará solo los de esa sección.
    # RESPUESTA ESPERADA: Arreglo JSON con los registros (Status 200).
    # -------------------------------------------------------------------------
    path('publico/', views.info_publica_listar, name='info-publica-listar'),


    # =========================================================================
    # ENDPOINTS DE ADMINISTRACIÓN
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/info-general/listar/
    # HEADERS: 
    #   { 
    #     "Authorization": "Bearer <tu_access_token>" 
    #   }
    # BODY: Ninguno
    # USO: Retorna TODOS los textos registrados en la BDD, incluyendo los 
    #      inactivos, para cargar la tabla en el panel de administración.
    # RESPUESTA ESPERADA: Arreglo JSON con todos los registros (Status 200).
    # -------------------------------------------------------------------------
    path('listar/', views.info_admin_listar, name='info-admin-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/info-general/crear/
    # HEADERS: 
    #   { 
    #     "Authorization": "Bearer <tu_access_token>",
    #     "Content-Type": "application/json"
    #   }
    # BODY (JSON): 
    # {
    #   "seccion": "inicio",
    #   "clave": "inicio_cuidados",
    #   "titulo": "Cuidados Vocales",
    #   "descripcion": "Recomendaciones específicas para profesores...",
    #   "enlace": "/portal/cuidados"
    # }
    # USO: Registra un nuevo bloque de texto dinámico en el sistema.
    # RESPUESTA ESPERADA: El objeto JSON recién creado (Status 201).
    # -------------------------------------------------------------------------
    path('crear/', views.info_crear, name='info-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PATCH (o PUT)
    # URL: /api/info-general/1/editar/   <-- Reemplazar '1' por el ID
    # HEADERS: 
    #   { 
    #     "Authorization": "Bearer <tu_access_token>",
    #     "Content-Type": "application/json"
    #   }
    # BODY (JSON): Al ser PATCH, se puede enviar solo lo que se desea cambiar.
    # {
    #   "titulo": "Título corregido",
    #   "descripcion": "Nueva descripción actualizada..."
    # }
    # USO: Actualiza la información de un bloque de texto existente.
    # RESPUESTA ESPERADA: Mensaje de éxito y el JSON actualizado (Status 200).
    # -------------------------------------------------------------------------
    path('<int:id_info>/editar/', views.info_editar, name='info-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/info-general/1/eliminar/   <-- Reemplazar '1' por el ID
    # HEADERS: 
    #   { 
    #     "Authorization": "Bearer <tu_access_token>" 
    #   }
    # BODY: Ninguno
    # USO: Desactiva un bloque de información cambiando su estado a False (borrado lógico).
    # RESPUESTA ESPERADA (JSON): { "mensaje": "Registro eliminado correctamente" } (Status 200).
    # -------------------------------------------------------------------------
    path('<int:id_info>/eliminar/', views.info_eliminar, name='info-eliminar'),
]