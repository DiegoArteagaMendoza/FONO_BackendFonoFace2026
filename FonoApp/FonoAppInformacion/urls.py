from django.urls import path
from FonoAppInformacion import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/informacion/listar/
    # URL CON FILTRO: /api/informacion/listar/?categoria=SA
    # HEADERS: Ninguno (Acceso público)
    # BODY: Ninguno
    # RESPUESTA ESPERADA:
    # [
    #   {
    #     "id_informacion": 1,
    #     "titulo": "Vacunas anuales",
    #     "categoria": "SA",
    #     "categoria_display": "Salud Animal",
    #     "contenido": "Las vacunas son importantes...",
    #     "fecha_creacion": "2026-05-23T10:00:00Z",
    #     "imagenes": [ { "id": 1, "imagen": "/media/...", "fecha_subida": "..." } ]
    #   }
    # ]
    # -------------------------------------------------------------------------
    path('listar/', views.informacion_listar, name='informacion-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/informacion/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (IMPORTANTE): Como recibe imágenes, DEBE ser un objeto "FormData" (multipart/form-data), NO un JSON.
    # EN EL FRONTEND (JS/TS):
    #   const formData = new FormData();
    #   formData.append('titulo', 'Nuevo tip');
    #   formData.append('categoria', 'TI');
    #   formData.append('contenido', 'Texto de prueba');
    #   formData.append('imagenes_subidas', archivoFile1); // Opcional, hasta 4
    # RESPUESTA ESPERADA: El objeto JSON recién creado (Status 201).
    # -------------------------------------------------------------------------
    path('crear/', views.informacion_crear, name='informacion-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PATCH (o PUT)
    # URL: /api/informacion/1/editar/   <-- Reemplazar '1' por el ID
    # HEADERS: 
    #   { 
    #     "Authorization": "Bearer <tu_access_token>",
    #     "Content-Type": "application/json"
    #   }
    # BODY (JSON): Como aquí NO editamos imágenes, el frontend manda un JSON normal.
    # {
    #   "titulo": "Título corregido",
    #   "categoria": "NU"
    # }
    # RESPUESTA ESPERADA: El objeto JSON actualizado (Status 200).
    # -------------------------------------------------------------------------
    path('<int:id_informacion>/editar/', views.informacion_editar, name='informacion-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/informacion/1/eliminar/  <-- Reemplazar '1' por el ID
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "mensaje": "Información eliminada correctamente"
    # }
    # -------------------------------------------------------------------------
    path('<int:id_informacion>/eliminar/', views.informacion_eliminar, name='informacion-eliminar'),
]