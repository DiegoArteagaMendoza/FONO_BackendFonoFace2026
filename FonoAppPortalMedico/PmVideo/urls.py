from django.urls import path
from PmVideo import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/pm/videos/subir/
    # HEADERS: Ninguno por ahora (ver TODO de autenticación en views.py)
    # BODY (IMPORTANTE): Como recibe un archivo DEBE ser "FormData"
    #                    (multipart/form-data), NO un JSON.
    # EN EL FRONTEND (Angular):
    #   const formData = new FormData();
    #   formData.append('cliente', idCliente);
    #   formData.append('cita', idCita); // opcional: vincula el video a una cita
    #   formData.append('video', archivoVideo);
    #   formData.append('duracion_segundos', Math.round(video.duration));
    #   formData.append('descripcion', 'Ronquera al hablar fuerte'); // opcional
    #
    # Si se envía 'cita', debe pertenecer al mismo cliente, admitir carga de
    # video (permite_carga_video) y seguir reservada (no cancelada/realizada).
    # REGLAS: máximo 30 segundos, hasta 50 MB, formatos mp4 / webm / mov.
    # RESPUESTA ESPERADA: El objeto JSON del video creado (Status 201), que
    # incluye "fecha_expiracion" y "dias_restantes".
    # -------------------------------------------------------------------------
    path('subir/', views.video_subir, name='video-subir'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/pm/videos/listar/            (todos los vigentes)
    #      /api/pm/videos/listar/?cliente=1  (los de un cliente puntual)
    #      /api/pm/videos/listar/?cita=5     (los de una cita puntual)
    # HEADERS: Requiere autenticación
    # RESPUESTA ESPERADA: Arreglo JSON con los videos vigentes.
    # -------------------------------------------------------------------------
    path('listar/', views.videos_listar, name='videos-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/pm/videos/1/   <-- Reemplazar '1' por el id_video
    # HEADERS: Requiere autenticación
    # RESPUESTA ESPERADA: El objeto JSON del video (404 si venció o se eliminó).
    # -------------------------------------------------------------------------
    path('<int:id_video>/', views.video_detalle, name='video-detalle'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/pm/videos/1/eliminar/
    # HEADERS: Requiere autenticación
    # BODY: Ninguno
    # RESPUESTA ESPERADA (JSON):
    # { "mensaje": "Video eliminado correctamente por orden médica" }
    # -------------------------------------------------------------------------
    path('<int:id_video>/eliminar/', views.video_eliminar, name='video-eliminar'),
]
