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
    #   formData.append('cita', idCita); // opcional: vincula el video a una cita
    #   formData.append('video', archivoVideo);
    #   formData.append('duracion_segundos', Math.round(video.duration));
    #   formData.append('descripcion', 'Ronquera al hablar fuerte'); // opcional
    #   -> El dueño NO se envía: se toma del token del paciente.
    #
    # Si se envía 'cita', debe pertenecer al mismo cliente, admitir carga de
    # video (permite_carga_video) y seguir reservada (no cancelada/realizada).
    # REGLAS: máximo 30 segundos, hasta 50 MB, formatos mp4 / webm / mov.
    # RESPUESTA ESPERADA: El objeto JSON del video creado (Status 201), que
    # incluye "fecha_expiracion" y "dias_restantes".
    # -------------------------------------------------------------------------
    path('subir/', views.video_subir, name='video-subir'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/videos/mis-videos/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # RESPUESTA: Los videos vigentes del paciente autenticado.
    # -------------------------------------------------------------------------
    path('mis-videos/', views.mis_videos, name='mis-videos'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE | URL: /api/pm/videos/mis-videos/1/eliminar/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # El paciente retira un video propio antes de que venza.
    # -------------------------------------------------------------------------
    path('mis-videos/<int:id_video>/eliminar/', views.mi_video_eliminar, name='mi-video-eliminar'),

    # =========================================================================
    # QUIEN RESERVÓ SIN CUENTA: gestiona su video con el código del correo.
    # Ninguno de estos tres pide token ni acepta ids: la cita sale del código y
    # el dueño, de la cita.
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/videos/seguimiento/A1B2C3D4/
    # HEADERS: Ninguno. El código hace de credencial.
    # RESPUESTA: Arreglo con el video adjunto a esa hora (vacío si no hay).
    #            No incluye id_video, id_cita ni id_cliente.
    # ERRORES: 404 si el código no existe; 400 si la hora no admite video.
    # -------------------------------------------------------------------------
    path('seguimiento/<str:codigo>/', views.video_seguimiento_listar, name='video-seguimiento-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/videos/seguimiento/A1B2C3D4/subir/
    # BODY (IMPORTANTE): FormData (multipart/form-data), NO JSON.
    # EN EL FRONTEND (Angular):
    #   const formData = new FormData();
    #   formData.append('video', archivoVideo);
    #   formData.append('duracion_segundos', Math.round(video.duration));
    #   formData.append('descripcion', 'Ronquera al hablar fuerte'); // opcional
    #   -> Ni la cita ni el dueño se envían: salen del código de la URL.
    # REGLAS: las mismas de siempre (30 s, 50 MB, mp4/webm/mov) y además uno
    #         solo por hora: si ya hay uno vigente responde 409.
    # LÍMITE: 10 subidas por hora y por IP (ajustable con la variable de entorno
    #         PM_VIDEO_SUBIDA_POR_CODIGO). Supera eso y responde 429.
    # RESPUESTA ESPERADA: El video creado (Status 201), sin ids.
    # -------------------------------------------------------------------------
    path('seguimiento/<str:codigo>/subir/', views.video_seguimiento_subir, name='video-seguimiento-subir'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE | URL: /api/pm/videos/seguimiento/A1B2C3D4/eliminar/
    # BODY: Ninguno. No recibe el id del video: la hora ya lo determina.
    # RESPUESTA ESPERADA: { "mensaje": "Video retirado correctamente" }
    # ERRORES: 404 si la hora no tiene video; 409 si tiene más de uno (eso solo
    #          pasa si además usó su cuenta, y desde ahí puede elegir cuál).
    # -------------------------------------------------------------------------
    path('seguimiento/<str:codigo>/eliminar/', views.video_seguimiento_eliminar, name='video-seguimiento-eliminar'),

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
