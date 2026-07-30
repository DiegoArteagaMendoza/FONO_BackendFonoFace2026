from django.urls import path
from FonoAppNoticias import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/noticias/listar/
    # HEADERS: Ninguno (Acceso público)
    # BODY: Ninguno
    # RESPUESTA ESPERADA: Un arreglo JSON con todas las noticias y sus imágenes.
    # [
    #   {
    #     "id_noticia": 1,
    #     "titulo": "Campaña de vacunación gratuita",
    #     "contenido": "Este fin de semana estaremos realizando...",
    #     "fecha_creacion": "2026-05-23T10:00:00Z",
    #     "FonoApp_Administracion": 1,
    #     "imagenes": [ 
    #        { "id": 1, "imagen": "/media/noticias/imagenes/foto1.jpg", "fecha_subida": "..." } 
    #     ]
    #   }
    # ]
    # -------------------------------------------------------------------------
    path('listar/', views.noticias_listar, name='noticias-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/noticias/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (IMPORTANTE): Como recibe imágenes, DEBE ser un objeto "FormData" (multipart/form-data), NO un JSON.
    # EN EL FRONTEND (Astro/JS):
    #   const formData = new FormData();
    #   formData.append('titulo', 'Nuevo título de noticia');
    #   formData.append('contenido', 'Cuerpo de la noticia...');
    #   formData.append('imagenes_subidas', archivoFile1); // Opcional, hasta 4 archivos
    # RESPUESTA ESPERADA: El objeto JSON de la noticia recién creada (Status 201).
    # -------------------------------------------------------------------------
    path('crear/', views.noticias_crear, name='noticias-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/noticias/1/eliminar/  <-- Reemplazar '1' por el ID de la noticia
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "mensaje": "Noticia eliminada correctamente"
    # }
    # -------------------------------------------------------------------------
    path('<int:id_noticia>/eliminar/', views.noticia_eliminar, name='noticia-eliminar'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/noticias/1/editar/  <-- Reemplazar '1' por el ID de la noticia
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON o FormData):
    # {
    #   "titulo": "Nuevo título corregido",
    #   "contenido": "Contenido actualizado de la noticia..."
    # }
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "mensaje": "Noticia actualizada correctamente"
    # }
    # -------------------------------------------------------------------------
    path('<int:id_noticia>/editar/', views.noticia_editar, name='noticia-editar'),
    
    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/noticias/1/imagenes/agregar/  <-- '1' es el id_noticia
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: FormData (multipart/form-data)
    #   formData.append('imagenes_subidas', archivoFile1);
    # -------------------------------------------------------------------------
    path('<int:id_noticia>/imagenes/agregar/', views.noticia_imagen_agregar, name='noticia-imagen-agregar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/noticias/imagenes/15/eliminar/  <-- '15' es el id de la IMAGEN a borrar
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY: Ninguno
    # -------------------------------------------------------------------------
    path('imagenes/<int:id_imagen>/eliminar/', views.noticia_imagen_eliminar, name='noticia-imagen-eliminar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/noticias/newsletter/suscribir/
    # HEADERS: Ninguno (Acceso público)
    # BODY (JSON): { "email": "visitante@correo.com" }
    # RESPUESTA ESPERADA (JSON):
    # { "mensaje": "Suscripción registrada correctamente" }  (Status 201)
    # Si el correo ya estaba suscrito:
    # { "mensaje": "Este correo ya se encuentra suscrito" }  (Status 200)
    # -------------------------------------------------------------------------
    path('newsletter/suscribir/', views.newsletter_suscribir, name='newsletter-suscribir'),
]