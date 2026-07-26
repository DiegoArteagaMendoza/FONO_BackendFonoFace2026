from django.db import models

class FonoApp_InfoGeneral_Queryset(models.QuerySet):
    def activos(self):
        """Retorna todos los registros que están activos (para el portal público)."""
        return self.filter(estado=True)
        
    def por_seccion(self, nombre_seccion):
        """Filtra los registros activos pertenecientes a una sección específica (ej. 'inicio')."""
        return self.activos().filter(seccion=nombre_seccion)
        
    def eliminar_logico(self, id_info):
        """Realiza una baja lógica del registro cambiando el estado a False."""
        return self.filter(id_info=id_info).update(estado=False)