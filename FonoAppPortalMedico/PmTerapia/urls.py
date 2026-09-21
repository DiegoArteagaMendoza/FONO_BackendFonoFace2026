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

    # =========================================================================
    # PLAN DE TERAPIA — lado del fonoaudiólogo
    # Un plan por par paciente–fono, activo a la vez. Todo con el token del
    # profesional; un plan ajeno responde 404.
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/terapia/planes/crear/
    # BODY (JSON):
    #   {
    #     "id_cita": 12,                      // una cita REALIZADA (estado RZ) del profesional
    #     "periodicidad": "SEMANAL",          // DIARIA | SEMANAL | QUINCENAL
    #     "indicaciones": "Texto general",    // opcional
    #     "ejercicios": [                     // de 1 a 3, del catálogo del profesional
    #       { "id_ejercicio": 4, "indicaciones": "3 veces al día" },
    #       { "id_ejercicio": 7 }
    #     ]
    #   }
    # ERRORES 400: cita no realizada, cita ajena, paciente sin cuenta (reservó
    #   como invitado), plan activo previo con ese paciente, ejercicios ajenos
    #   o repetidos, más de 3.
    # RESPUESTA ESPERADA: El plan creado (Status 201), con los ejercicios
    #   incrustados y 'periodo_actual' { numero, desde, hasta } en hora de Chile.
    # -------------------------------------------------------------------------
    path('planes/crear/', views.plan_crear, name='plan-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/planes/            (activos)
    #                    /api/pm/terapia/planes/?todos=true (incluye cerrados)
    # RESPUESTA: Arreglo de planes del profesional, con 'paciente_nombre'.
    # -------------------------------------------------------------------------
    path('planes/', views.planes_listar, name='planes-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/planes/5/
    # -------------------------------------------------------------------------
    path('planes/<int:id_plan>/', views.plan_detalle, name='plan-detalle'),

    # -------------------------------------------------------------------------
    # MÉTODO: PATCH | URL: /api/pm/terapia/planes/5/ajustar/
    # BODY (JSON): mismos campos que crear, todos opcionales, sin id_cita.
    #   Lo que no viene no cambia. OJO: cambiar 'periodicidad' reinicia el plan
    #   a hoy (fecha_inicio) y el contador de recordatorios.
    #   Los ejercicios que salen se desactivan, no se borran: conservan sus
    #   videos anteriores.
    # -------------------------------------------------------------------------
    path('planes/<int:id_plan>/ajustar/', views.plan_ajustar, name='plan-ajustar'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/terapia/planes/5/cerrar/
    # BODY: Ninguno. El plan pasa a CERRADO; queda como historial.
    # -------------------------------------------------------------------------
    path('planes/<int:id_plan>/cerrar/', views.plan_cerrar, name='plan-cerrar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/planes/de-cita/12/
    # El plan ACTIVO del paciente de esa cita con este profesional. La agenda
    # lo usa para mostrar "Asignar plan" o "Ajustar plan".
    # RESPUESTA (Status 200):
    #   { "plan": <el plan> | null, "paciente_nombre": "...",
    #     "paciente_tiene_cuenta": true|false, "cita_realizada": true|false }
    #   404 si la cita no es suya.
    # -------------------------------------------------------------------------
    path('planes/de-cita/<int:id_cita>/', views.plan_de_cita, name='plan-de-cita'),

    # =========================================================================
    # PLAN DE TERAPIA — lado del paciente
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/mis-planes/
    # HEADERS: { "Authorization": "Bearer <token del paciente>" }
    # RESPUESTA: Sus planes activos, con 'profesional_nombre', los ejercicios
    #   (nombre, instrucciones, video de ejemplo) y 'periodo_actual'.
    # -------------------------------------------------------------------------
    path('mis-planes/', views.mis_planes, name='mis-planes'),

    # =========================================================================
    # VIDEOS DE PROGRESO — lado del paciente
    # Un video por ejercicio en cada periodo. Viven 7 días; el registro y la
    # retroalimentación quedan. Todo con el token del paciente.
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: POST | URL: /api/pm/terapia/mis-planes/5/videos/subir/
    # BODY (IMPORTANTE): FormData (multipart/form-data), NO JSON.
    # EN EL FRONTEND (Angular):
    #   const formData = new FormData();
    #   formData.append('id_plan_ejercicio', idPlanEjercicio);  // de plan.ejercicios[i].id_plan_ejercicio
    #   formData.append('video', archivoVideo);
    #   formData.append('duracion_segundos', Math.round(video.duration));
    #   formData.append('comentario', 'Me costó la última serie');  // opcional
    #   -> El periodo y el dueño los pone el servidor.
    # REGLAS: 30 s, 50 MB, mp4/webm/mov. 400 si el plan está cerrado o el
    #         ejercicio ya no forma parte de él. Se admite más de un video por
    #         ejercicio y periodo (el paciente puede regrabarse).
    # RESPUESTA ESPERADA: El video creado (Status 201) con 'numero_periodo',
    #   'fecha_expiracion' y 'dias_restantes'.
    # -------------------------------------------------------------------------
    path('mis-planes/<int:id_plan>/videos/subir/', views.mi_plan_video_subir, name='mi-plan-video-subir'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET | URL: /api/pm/terapia/mis-planes/5/videos/
    # RESPUESTA: Historial del plan, del más nuevo al más viejo. Los vencidos
    #   vienen con 'video': null pero conservan fecha y retroalimentación.
    # -------------------------------------------------------------------------
    path('mis-planes/<int:id_plan>/videos/', views.mi_plan_videos, name='mi-plan-videos'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE | URL: /api/pm/terapia/mis-videos/12/eliminar/
    # Retira un video propio vigente (motivo RP). 404 si no es suyo o ya venció.
    # -------------------------------------------------------------------------
    path('mis-videos/<int:id_video>/eliminar/', views.mi_video_progreso_eliminar, name='mi-video-progreso-eliminar'),
]
