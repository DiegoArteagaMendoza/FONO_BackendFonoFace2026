from django.urls import path
from PmTerapia import views

# Todas las rutas cuelgan de /api/pm/terapia/ (ver FonoAppPM/urls.py).

urlpatterns = [
    # =========================================================================
    # CATÁLOGO DE EJERCICIOS DEL FONOAUDIÓLOGO
    # Privado: cada profesional ve y administra solo los suyos. El dueño sale
    # del token en todas las rutas; nunca se envía en el cuerpo.
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/ejercicios/
    # HEADERS: { "Authorization": "Bearer <token del profesional>" }
    # RESPUESTA: Arreglo con los ejercicios vigentes del profesional, del más
    #            nuevo al más antiguo. 'video_ejemplo' llega como URL https.
    # -------------------------------------------------------------------------
    path('ejercicios/', views.ejercicios_listar, name='ejercicios-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/terapia/ejercicios/crear/
    # HEADERS: { "Authorization": "Bearer <token del profesional>" }
    # BODY (IMPORTANTE): FormData (multipart/form-data), NO JSON.
    # EN EL FRONTEND (Angular):
    #   const formData = new FormData();
    #   formData.append('nombre', 'Vibración labial');
    #   formData.append('instrucciones', 'Sopla suave haciendo vibrar los labios...');
    #   formData.append('video_ejemplo', archivoVideo);
    #   formData.append('duracion_segundos', Math.round(video.duration));
    # REGLAS: el video es obligatorio, máximo 15 segundos y 30 MB, mp4/webm/mov.
    #         Es PERMANENTE: no vence a los 30 días como los de síntomas.
    # RESPUESTA ESPERADA: El ejercicio creado (Status 201).
    # -------------------------------------------------------------------------
    path('ejercicios/crear/', views.ejercicio_crear, name='ejercicio-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PATCH | URL: /api/pm/terapia/ejercicios/1/editar/
    # HEADERS: { "Authorization": "Bearer <token del profesional>" }
    # BODY: FormData con los campos a cambiar. Todos opcionales; si viene
    #       'video_ejemplo' debe venir también 'duracion_segundos'. Al cambiar
    #       el video, el anterior se borra de Cloudinary.
    # RESPUESTA ESPERADA: El ejercicio actualizado. 404 si no es del profesional.
    # -------------------------------------------------------------------------
    path('ejercicios/<int:id_ejercicio>/editar/', views.ejercicio_editar, name='ejercicio-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE | URL: /api/pm/terapia/ejercicios/1/eliminar/
    # HEADERS: { "Authorization": "Bearer <token del profesional>" }
    # Borrado lógico: sale del catálogo, pero los planes que lo tengan asignado
    # lo siguen mostrando. El video solo se borra de Cloudinary si ningún plan
    # lo usa.
    # RESPUESTA ESPERADA: { "mensaje": "Ejercicio eliminado del catálogo" }
    # -------------------------------------------------------------------------
    path('ejercicios/<int:id_ejercicio>/eliminar/', views.ejercicio_eliminar, name='ejercicio-eliminar'),
]
