from django.urls import path
from FonoAppDiagnostico import views

urlpatterns = [
    # =========================================================================
    # FORMULARIOS (plantillas de test, ej. Índice de Fatiga Vocal / IDV-CH)
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/diagnostico/formularios/listar/
    # HEADERS: Ninguno (Acceso público)
    # USO: Retorna todos los formularios activos con su estructura de subescalas y preguntas.
    #      Es la lista que alimenta el desplegable "Autoevaluación" del portal de cliente.
    # -------------------------------------------------------------------------
    path('formularios/listar/', views.formulario_listar, name='diagnostico-formulario-listar'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/diagnostico/formularios/1/  <-- Reemplazar '1' por el id_formulario
    # HEADERS: Ninguno (Acceso público)
    # USO: Retorna un formulario activo listo para ser respondido.
    # -------------------------------------------------------------------------
    path('formularios/<int:id_formulario>/', views.formulario_detalle, name='diagnostico-formulario-detalle'),

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/diagnostico/formularios/crear/
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON):
    # {
    #   "nombre": "Índice de Fatiga Vocal",
    #   "descripcion": "0 = Nunca, 1 = Casi nunca, 2 = Algunas veces, 3 = Casi siempre, 4 = Siempre",
    #   "valor_minimo": 0,
    #   "valor_maximo": 4,
    #   "subescalas": [
    #     {
    #       "nombre": "Parte 1",
    #       "orden": 1,
    #       "preguntas": [
    #         {"texto": "No tengo ganas de hablar luego de usar mi voz por un tiempo", "orden": 1},
    #         {"texto": "Mi voz se siente cansada cuando hablo mucho", "orden": 2}
    #       ],
    #       # Opcional: interpretación del puntaje de ESTA subescala (rangos sin solape).
    #       "interpretaciones": [
    #         {"valor_minimo": 0, "valor_maximo": 3, "etiqueta": "Leve", "descripcion": "..."},
    #         {"valor_minimo": 4, "valor_maximo": 8, "etiqueta": "Moderado", "descripcion": "..."}
    #       ]
    #     },
    #     {
    #       "nombre": "Parte 2",
    #       "orden": 2,
    #       "preguntas": [
    #         {"texto": "Siento dolor en el cuello al final del día después de usar mi voz", "orden": 1}
    #       ]
    #     }
    #   ],
    #   # Opcional: interpretación del PUNTAJE TOTAL del test (rangos sin solape).
    #   "interpretaciones": [
    #     {"valor_minimo": 0, "valor_maximo": 10, "etiqueta": "Sin fatiga vocal", "descripcion": "..."},
    #     {"valor_minimo": 11, "valor_maximo": 20, "etiqueta": "Fatiga vocal moderada", "descripcion": "..."}
    #   ]
    # }
    # USO: Registra un formulario nuevo junto a sus subescalas, preguntas e
    #      interpretaciones de resultado en una sola operación.
    # -------------------------------------------------------------------------
    path('formularios/crear/', views.formulario_crear, name='diagnostico-formulario-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: PUT o PATCH
    # URL: /api/diagnostico/formularios/1/editar/  <-- Reemplazar '1' por el id_formulario
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # BODY (JSON): { "nombre": "Nuevo nombre", "estado": true }
    # USO: Actualiza campos simples del formulario (no su estructura de preguntas).
    # -------------------------------------------------------------------------
    path('formularios/<int:id_formulario>/editar/', views.formulario_editar, name='diagnostico-formulario-editar'),

    # -------------------------------------------------------------------------
    # MÉTODO: DELETE
    # URL: /api/diagnostico/formularios/1/eliminar/  <-- Reemplazar '1' por el id_formulario
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # USO: Desactiva de forma lógica el formulario modificando su propiedad estado a False.
    # -------------------------------------------------------------------------
    path('formularios/<int:id_formulario>/eliminar/', views.formulario_eliminar, name='diagnostico-formulario-eliminar'),

    # =========================================================================
    # RESPUESTAS (aplicación del test a un paciente) y resultado calculado
    # =========================================================================

    # -------------------------------------------------------------------------
    # MÉTODO: POST
    # URL: /api/diagnostico/respuestas/crear/
    # HEADERS: Ninguno (Acceso público; el cliente responde sin cuenta propia)
    # BODY (JSON):
    # {
    #   "formulario": 1,
    #   "paciente_nombre": "Juan Pérez",
    #   "paciente_fecha_nacimiento": "1990-05-10",
    #   "detalles": [
    #     {"pregunta": 1, "valor": 3},
    #     {"pregunta": 2, "valor": 2}
    #   ]
    # }
    # RESPUESTA ESPERADA (JSON):
    # {
    #   "id_respuesta": 1,
    #   "formulario": 1,
    #   "paciente_nombre": "Juan Pérez",
    #   "resultado": {
    #     "puntaje_total": 5,
    #     "interpretacion_total": {"etiqueta": "Sin fatiga vocal", "descripcion": "..."},
    #     "subescalas": [
    #       {
    #         "id_subescala": 1, "subescala": "Parte 1", "puntaje": 5,
    #         "interpretacion": {"etiqueta": "Leve", "descripcion": "..."}
    #       }
    #     ]
    #   }
    # }
    # NOTA: "interpretacion_total" e "interpretacion" (por subescala) quedan en null si el
    # formulario no definió rangos para ese puntaje, o si el puntaje no cayó en ninguno.
    # USO: Recibe la realización completa del test (una respuesta por cada pregunta del
    #      formulario) y entrega el resultado ya calculado: puntaje total y por subescala.
    # -------------------------------------------------------------------------
    path('respuestas/crear/', views.respuesta_crear, name='diagnostico-respuesta-crear'),

    # -------------------------------------------------------------------------
    # MÉTODO: GET
    # URL: /api/diagnostico/respuestas/formulario/1/  <-- Reemplazar '1' por el id_formulario
    # HEADERS: { "Authorization": "Bearer <tu_access_token>" }
    # USO: Retorna los resultados ya registrados para un formulario específico.
    # -------------------------------------------------------------------------
    path(
        'respuestas/formulario/<int:id_formulario>/',
        views.respuesta_listar_por_formulario,
        name='diagnostico-respuesta-listar-por-formulario',
    ),
]
