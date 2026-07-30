from django.urls import path
from FonoAppVoz import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/voz/listar/
    # HEADERS: Ninguno (Acceso público)
    # USO: Retorna un arreglo JSON de todo el contenido informativo de voz con estado=True.
    # -------------------------------------------------------------------------
    path('listar/', views.voz_listar, name='voz-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/voz/categoria/anatomia/
    # HEADERS: Ninguno (Acceso público)
    # USO: Filtra contenido vigente de una categoría (DEFINICION, ANATOMIA, FISIOLOGIA, etc.)
    # -------------------------------------------------------------------------
    path('categoria/<str:tipo_categoria>/', views.voz_filtrar_categoria, name='voz-filtrar-categoria'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/voz/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: FormData (Permite el envío de la clave 'img')
    # -------------------------------------------------------------------------
    path('crear/', views.voz_crear, name='voz-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/voz/1/editar/  <-- Reemplazar '1' por el ID del registro de voz
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON o FormData):
    # {
    #   "titulo": "Nuevo título corregido",
    #   "contenido": "Contenido actualizado sobre la voz..."
    # }
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "mensaje": "Contenido de voz actualizado correctamente"
    # }
    # -------------------------------------------------------------------------
    path('<int:id_voz>/editar/', views.voz_editar, name='voz-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/voz/1/eliminar/  <-- Reemplazar '1' por el ID del registro de voz
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # USO: Desactiva de forma lógica el registro modificando su propiedad estado a False.
    # -------------------------------------------------------------------------
    path('<int:id_voz>/eliminar/', views.voz_eliminar, name='voz-eliminar'),
]
