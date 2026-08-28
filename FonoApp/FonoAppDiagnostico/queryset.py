from django.db import models, transaction


class FonoApp_Diagnostico_Formulario_Queryset(models.QuerySet):

    def listar_todo(self):
        """Retorna todos los formularios activos junto a su estructura de preguntas."""
        return self.filter(estado=True).prefetch_related('subescalas__preguntas')

    def obtener_activo(self, id_formulario):
        """Retorna un formulario activo con su estructura completa, o None si no existe."""
        return self.filter(
            id_formulario=id_formulario, estado=True
        ).prefetch_related('subescalas__preguntas').first()

    def eliminar_logico(self, id_formulario):
        """Desactiva el formulario de forma lógica cambiando su estado a False."""
        filas_actualizadas = self.filter(id_formulario=id_formulario).update(estado=False)
        return filas_actualizadas > 0

    def editar_formulario(self, id_formulario, **datos_a_actualizar):
        """Actualiza campos simples del formulario protegiendo su estructura y autoría."""
        datos_a_actualizar.pop('FonoApp_Administracion', None)
        datos_a_actualizar.pop('subescalas', None)
        filas_actualizadas = self.filter(id_formulario=id_formulario, estado=True).update(**datos_a_actualizar)
        return filas_actualizadas > 0

    def crear_formulario(self, usuario, subescalas_data, interpretaciones_data=None, **datos_formulario):
        """Crea un formulario junto a sus subescalas, preguntas e interpretaciones de
        resultado en una única transacción.

        Este es el mecanismo por el cual "el usuario" (profesional autenticado) registra
        formularios como el Índice de Fatiga Vocal o el IDV-CH: no existen tests
        precargados por fixture/migración, todos se dan de alta por esta vía.

        'interpretaciones_data' son los rangos de puntaje que interpretan el resultado
        total del test (ej. 0-10 'Leve'); cada subescala puede traer además sus propios
        rangos anidados en 'subescala_data["interpretaciones"]' (ej. la parte 'Funcional'
        del IDV-CH interpretada por separado).
        """
        with transaction.atomic():
            formulario = self.create(FonoApp_Administracion=usuario, **datos_formulario)

            for orden_subescala, subescala_data in enumerate(subescalas_data, start=1):
                preguntas_data = subescala_data.pop('preguntas')
                interpretaciones_subescala_data = subescala_data.pop('interpretaciones', [])
                subescala_data.setdefault('orden', orden_subescala)
                subescala = formulario.subescalas.create(**subescala_data)

                for orden_pregunta, pregunta_data in enumerate(preguntas_data, start=1):
                    pregunta_data.setdefault('orden', orden_pregunta)
                    formulario.preguntas.create(subescala=subescala, **pregunta_data)

                for interpretacion_data in interpretaciones_subescala_data:
                    formulario.interpretaciones.create(subescala=subescala, **interpretacion_data)

            for interpretacion_data in (interpretaciones_data or []):
                formulario.interpretaciones.create(subescala=None, **interpretacion_data)

        return formulario


class FonoApp_Diagnostico_Respuesta_Queryset(models.QuerySet):

    def listar_por_formulario(self, id_formulario):
        """Retorna los resultados registrados para un formulario, del más reciente al más antiguo."""
        return self.filter(formulario_id=id_formulario).select_related('formulario')

    def registrar_respuesta(self, usuario, detalles_data, formulario, **datos_respuesta):
        """Registra la aplicación de un test a un paciente y calcula su puntaje.

        Suma el puntaje total y el puntaje por subescala (ej. Parte 1/2/3 del IFV,
        o Funcional/Física/Emocional del IDV-CH) a partir del detalle de respuestas
        ya validado por el serializer (una respuesta por cada pregunta del formulario),
        y adjunta la interpretación (rango de FonoApp_Diagnostico_Interpretacion) en la
        que cayó cada puntaje, si el formulario tiene rangos definidos. La interpretación
        queda "congelada" en la respuesta: si luego se editan los rangos del formulario,
        las respuestas ya registradas conservan la que se mostró en su momento.
        """
        from FonoAppDiagnostico.models import FonoApp_Diagnostico_RespuestaDetalle

        interpretaciones = list(formulario.interpretaciones.all())
        interpretaciones_totales = [i for i in interpretaciones if i.subescala_id is None]
        interpretaciones_por_subescala = {}
        for interpretacion in interpretaciones:
            if interpretacion.subescala_id:
                interpretaciones_por_subescala.setdefault(interpretacion.subescala_id, []).append(interpretacion)

        def _interpretar(candidatos, puntaje):
            for candidato in candidatos:
                if candidato.valor_minimo <= puntaje <= candidato.valor_maximo:
                    return {'etiqueta': candidato.etiqueta, 'descripcion': candidato.descripcion}
            return None

        with transaction.atomic():
            respuesta = self.create(
                formulario=formulario,
                FonoApp_Administracion=usuario,
                **datos_respuesta,
            )

            subescalas_puntaje = {}
            puntaje_total = 0
            detalles_a_crear = []

            for detalle in detalles_data:
                pregunta = detalle['pregunta']
                valor = detalle['valor']
                puntaje_total += valor

                if pregunta.subescala_id:
                    resumen = subescalas_puntaje.setdefault(pregunta.subescala_id, {
                        'id_subescala': pregunta.subescala_id,
                        'subescala': pregunta.subescala.nombre,
                        'puntaje': 0,
                    })
                    resumen['puntaje'] += valor

                detalles_a_crear.append(
                    FonoApp_Diagnostico_RespuestaDetalle(respuesta=respuesta, pregunta=pregunta, valor=valor)
                )

            FonoApp_Diagnostico_RespuestaDetalle.objects.bulk_create(detalles_a_crear)

            for resumen in subescalas_puntaje.values():
                candidatos = interpretaciones_por_subescala.get(resumen['id_subescala'], [])
                resumen['interpretacion'] = _interpretar(candidatos, resumen['puntaje'])

            respuesta.puntaje_total = puntaje_total
            respuesta.detalle_subescalas = sorted(
                subescalas_puntaje.values(), key=lambda item: item['id_subescala']
            )
            respuesta.interpretacion_total = _interpretar(interpretaciones_totales, puntaje_total)
            respuesta.save(update_fields=['puntaje_total', 'detalle_subescalas', 'interpretacion_total'])

        return respuesta
