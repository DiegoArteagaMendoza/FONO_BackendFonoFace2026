from django.db import models
from django.contrib.auth.hashers import make_password

class FonoAPP_Queryset(models.QuerySet):
    def is_activo(self, rut):
        return self.filter(rut=rut).filter(estado=True)
    
    def crear_usuario(self, email, password=None, **extra_fields):
        """
        Crea un usuario encriptando la contraseña manualmente.
        """
        if not email:
            raise ValueError('El email es obligatorio')
        
        email = email.lower() # Normalización básica
        # Encriptamos la contraseña antes de crear el registro
        if password:
            password = make_password(password)
            
        return self.create(email=email, password=password, **extra_fields)
    
    def validar_credenciales(self, email, password):        
        try:
            usuario = self.get(email=email)
            print(usuario)
            if usuario.check_password(password): # posibilidad de agregar auth en 2 pasos con codigo a correo
                return usuario
        except models.ObjectDoesNotExist:
            return None
        return None
    
    def eliminar_logico(self, rut):
        return self.filter(rut=rut).update(estado=False)
    
    def actualizar_password(self, rut, nueva_password):
        """
        Actualiza y encripta la contraseña de un usuario buscando por su RUT.
        """
        # Encriptamos la contraseña en el formato que exige Django
        password_encriptada = make_password(nueva_password)
        
        # Filtramos por el rut y actualizamos directamente el campo 'password'
        # Retorna el número de filas afectadas (1 si el usuario existe, 0 si no)
        filas_actualizadas = self.filter(rut=rut).update(password=password_encriptada)
        
        return filas_actualizadas > 0
    
    def editar_usuario_parcial(self, rut, estado=None, is_staff=None, password=None):
        """
        Actualiza el estado (activo/inactivo), permisos (staff) y opcionalmente 
        la contraseña de un usuario buscando por su RUT.
        """
        usuario = self.filter(rut=rut).first()
        if not usuario:
            return False

        # Campos a actualizar para optimizar la consulta a la BDD
        campos_actualizar = []

        if estado is not None:
            usuario.estado = estado
            campos_actualizar.append('estado')
            
        if is_staff is not None:
            usuario.is_staff = is_staff
            campos_actualizar.append('is_staff')
            
        if password:
            usuario.password = make_password(password)
            campos_actualizar.append('password')

        # Guardamos solo los campos que sufrieron modificaciones
        if campos_actualizar:
            usuario.save(update_fields=campos_actualizar)
            
        return True
    
    # =======================================
    # BANNER QUERYSET
    # =======================================

class FonoApp_Banner_Queryset(models.QuerySet):
    def activos(self):
        """Retorna solo los banners vigentes."""
        return self.filter(estado=True)

    def con_detalles(self):
        """Optimiza la consulta de imágenes relacionales para evitar el problema N+1."""
        return self.select_related('FonoApp_Administracion').prefetch_related('imagenes')

    def crear_banner(self, usuario, titulo, descripcion, imagenes=None, **extra_fields):
        """Crea el banner y asocia su imagen validando el límite de negocio."""
        if imagenes and len(imagenes) > 1:
            raise ValueError("Solo se permite adjuntar una (1) imagen por banner.")

        banner = self.create(
            FonoApp_Administracion=usuario,
            titulo=titulo,
            descripcion=descripcion,
            **extra_fields
        )

        if imagenes:
            from .models import FonoApp_Banner_Inicio_Imagenes
            # Aunque sea una sola, mantenemos la estructura relacional limpia
            FonoApp_Banner_Inicio_Imagenes.objects.create(banner=banner, imagen=imagenes[0])

        return banner

    def eliminar_logico(self, id_banner):
        """Realiza la baja lógica cambiando el estado a False."""
        return self.filter(id_banner=id_banner).update(estado=False)

    def actualizar_imagen(self, id_banner, nueva_imagen):
        """
        Reemplaza la imagen de un banner: borra el archivo físico anterior y su
        registro, y guarda la nueva imagen. Mantiene el límite de 1 imagen por banner.
        Retorna una tupla (exito_booleano, mensaje_string).
        """
        try:
            banner = self.get(pk=id_banner, estado=True)
        except models.ObjectDoesNotExist:
            return False, "Banner no encontrado o inactivo."

        from .models import FonoApp_Banner_Inicio_Imagenes

        for imagen_anterior in banner.imagenes.all():
            imagen_anterior.imagen.delete(save=False)
            imagen_anterior.delete()

        FonoApp_Banner_Inicio_Imagenes.objects.create(banner=banner, imagen=nueva_imagen)

        return True, "Imagen del banner actualizada correctamente."
        