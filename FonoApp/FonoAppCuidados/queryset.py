from django.db import models

class FonoApp_Cuidados_Queryset(models.QuerySet):
    
    def listar_todo(self):
        """Retorna todos los cuidados activos."""
        return self.filter(estado=True)
        
    def filtrar_por_publico(self, tipo_publico):
        """Filtra los cuidados según el público objetivo asignado."""
        return self.filter(publico=tipo_publico, estado=True)
        
    def eliminar_logico(self, id_cuidado):
        """Desactiva el registro de forma lógica cambiando su estado a False."""
        filas_actualizadas = self.filter(id_cuidado=id_cuidado).update(estado=False)
        return filas_actualizadas > 0
        
    def crear_cuidado(self, usuario, titulo, contenido, publico, img=None, fuente=None, **extra_fields):
        """Crea un registro de cuidado asociándolo al usuario autenticado."""
        return self.create(
            FonoApp_Administracion=usuario,
            titulo=titulo,
            contenido=contenido,
            publico=publico,
            img=img,
            fuente=fuente,
            **extra_fields
        )
        
    def editar_cuidado(self, id_cuidado, **datos_a_actualizar):
        """Actualiza los campos del cuidado protegiendo relaciones críticas."""
        datos_a_actualizar.pop('FonoApp_Administracion', None)
        
        # Si se incluye un archivo de imagen, usamos el flujo con .save() 
        # para que Django gestione correctamente el almacenamiento en el servidor
        if 'img' in datos_a_actualizar and datos_a_actualizar['img']:
            try:
                instancia = self.get(id_cuidado=id_cuidado, estado=True)
                for campo, valor in datos_a_actualizar.items():
                    setattr(instancia, campo, valor)
                instancia.save()
                return True
            except models.ObjectDoesNotExist:
                return False
        
        # Si no hay imagen, realizamos un update masivo y veloz en la BD
        filas_actualizadas = self.filter(id_cuidado=id_cuidado, estado=True).update(**datos_a_actualizar)
        return filas_actualizadas > 0