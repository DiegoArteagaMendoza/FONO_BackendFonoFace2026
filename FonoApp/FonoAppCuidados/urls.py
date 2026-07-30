from django.urls import path
from FonoAppCuidados import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/cuidados/listar/
    # HEADERS: Ninguno (Acceso público)
    # USO: Retorna un arreglo JSON de todas las guías de cuidado con estado=True.
    # -------------------------------------------------------------------------
    path('listar/', views.cuidados_listar, name='cuidados-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/cuidados/publico/profesores/
    # HEADERS: Ninguno (Acceso público)
    # USO: Filtra cuidados vigentes de un segmento (NIÑOS, PROFESORES, LOCUTORES, etc.)
    # -------------------------------------------------------------------------
    path('publico/<str:tipo_publico>/', views.cuidados_filtrar_publico, name='cuidados-filtrar-publico'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/cuidados/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: FormData (Permite el envío de la clave 'img')
    # -------------------------------------------------------------------------
    path('crear/', views.cuidados_crear, name='cuidados-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/cuidados/1/editar/  <-- Reemplazar '1' por el ID del cuidado
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON o FormData):
    # {
    #   "titulo": "Nuevo título corregido",
    #   "contenido": "Contenido actualizado del cuidado..."
    # }
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "mensaje": "Cuidado actualizado correctamente"
    # }
    # -------------------------------------------------------------------------
    path('<int:id_cuidado>/editar/', views.cuidado_editar, name='cuidado-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/cuidados/1/eliminar/  <-- Reemplazar '1' por el ID del cuidado
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # USO: Desactiva de forma lógica la guía modificando su propiedad estado a False.
    # -------------------------------------------------------------------------
    path('<int:id_cuidado>/eliminar/', views.cuidado_eliminar, name='cuidado-eliminar'),
]