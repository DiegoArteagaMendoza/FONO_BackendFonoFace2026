from django.db import models

class FonoApp_Voz_Queryset(models.QuerySet):

    def listar_todo(self):
        """Retorna todo el contenido informativo de voz activo."""
        return self.filter(estado=True)

    def filtrar_por_categoria(self, tipo_categoria):
        """Filtra el contenido de voz según la categoría asignada."""
        return self.filter(categoria=tipo_categoria, estado=True)

    def eliminar_logico(self, id_voz):
        """Desactiva el registro de forma lógica cambiando su estado a False."""
        filas_actualizadas = self.filter(id_voz=id_voz).update(estado=False)
        return filas_actualizadas > 0

    def crear_voz(self, usuario, titulo, contenido, categoria, img=None, fuente=None, **extra_fields):
        """Crea un registro informativo de voz asociándolo al usuario autenticado."""
        return self.create(
            FonoApp_Administracion=usuario,
            titulo=titulo,
            contenido=contenido,
            categoria=categoria,
            img=img,
            fuente=fuente,
            **extra_fields
        )

    def editar_voz(self, id_voz, **datos_a_actualizar):
        """Actualiza los campos del registro de voz protegiendo relaciones críticas."""
        datos_a_actualizar.pop('FonoApp_Administracion', None)

        # Si se incluye un archivo de imagen, usamos el flujo con .save()
        # para que Django gestione correctamente el almacenamiento en el servidor
        if 'img' in datos_a_actualizar and datos_a_actualizar['img']:
            try:
                instancia = self.get(id_voz=id_voz, estado=True)
                if instancia.img:
                    instancia.img.delete(save=False)
                for campo, valor in datos_a_actualizar.items():
                    setattr(instancia, campo, valor)
                instancia.save()
                return True
            except models.ObjectDoesNotExist:
                return False

        # Si no hay imagen, realizamos un update masivo y veloz en la BD
        filas_actualizadas = self.filter(id_voz=id_voz, estado=True).update(**datos_a_actualizar)
        return filas_actualizadas > 0
