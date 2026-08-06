from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from FonoAppAdministracion.models import FonoApp_Administracion, FonoApp_Banner_Inicio, FonoApp_Banner_Inicio_Imagenes
from FonoAppAdministracion.serializer import FonoApp_Serializer, FonoApp_Banner_ImagenSerializer, FonoApp_Banner_InicioSerializer
from FonoAppFunciones.authentication import CustomJWTAuthentication, reCaptcha

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([AllowAny])  # Permite acceso inicial (registro) sin token
def usuarios_create(request):
    """
    Crea un usuario. Es AllowAny para servir como registro público inicial (el
    primer administrador del sistema no tiene forma de autenticarse todavía;
    ver FonoAPP_Manager.create_superuser / 'python manage.py createsuperuser'
    para ESE primer bootstrap), pero eso NO debe permitir que cualquiera se
    autoasigne permisos: los campos sensibles (is_staff, is_superuser) solo se
    respetan si quien hace la petición YA es superusuario. Si la petición es
    anónima o de alguien sin ese rol, esos campos se descartan antes de validar
    y la cuenta nace como 'Usuario' base (is_staff=False, is_superuser=False),
    sin importar lo que el cliente haya enviado.

    Modelo de roles (3 niveles, ver también usuario_editar_parcial):
    - Usuario   (is_staff=False, is_superuser=False): gestiona el contenido
      público (información, cuidados, la voz, noticias, carrusel, textos).
    - Admin     (is_staff=True,  is_superuser=False): todo lo de Usuario, más
      el Portal Médico (aprobar/rechazar acreditaciones, validar documentos,
      catálogo de especialidades). NO administra otras cuentas.
    - SuperAdmin(is_staff=True,  is_superuser=True):  todo lo anterior, más
      Gestión de Usuarios (crear/editar/activar/desactivar cuentas y asignar
      roles). Es el único nivel que puede otorgar is_staff/is_superuser.
    """
    solicitante = request.user if getattr(request.user, 'is_authenticated', False) else None
    puede_gestionar_usuarios = bool(solicitante and solicitante.is_superuser)

    datos = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

    if not puede_gestionar_usuarios:
        datos.pop('is_staff', None)
        datos.pop('is_superuser', None)

    serializer = FonoApp_Serializer(data=datos)
    if serializer.is_valid():
        serializer.save() # Esto dispara el create() del serializer que llama a crear_usuario()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def usuarios_list(request):
    """Lista el directorio completo de administradores. Gestión de Usuarios es exclusiva de SuperAdmin."""
    if not request.user.is_superuser:
        return Response({'error': 'Requiere rol SuperAdmin (is_superuser)'}, status=status.HTTP_403_FORBIDDEN)

    # Utilizamos el filtro estándar ya que "activos()" no está definido en el queryset
    usuarios = FonoApp_Administracion.objects
    serializer = FonoApp_Serializer(usuarios, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    # frontend debe enviar {"correo": "...", "password": "..."}
    email = request.data.get('correo')
    password = request.data.get('password')
    # captcha_token = request.data.get('captcha_token')

    # if not reCaptcha.captcha_verification(captcha_token):
    #     return Response(
    #         {'error': 'Fallo en la validacion de seguridad (reCAPTCHA). Por favor intente denuevo'},
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    if not email or not password:
        return Response({'error': 'Email y password requeridos'}, status=status.HTTP_400_BAD_REQUEST)

    # Llama al método personalizado del queryset
    usuario = FonoApp_Administracion.objects.validar_credenciales(email, password)

    if usuario:
        if not usuario.estado:
            return Response({'error': 'Cuenta inactiva'}, status=status.HTTP_401_UNAUTHORIZED)
        
        usuario.last_conection = timezone.now()
        usuario.save(update_fields=['last_conection'])

        refresh = RefreshToken.for_user(usuario)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {'nombre': usuario.nombre, 'email': usuario.email, 'rut': usuario.rut}
        })
    
    return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def usuario_perfil(request):
    usuario = request.user
    serializer = FonoApp_Serializer(usuario)
    return Response(serializer.data)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def usuario_eliminar(request, rut):
    """
    Endpoint para eliminar lógicamente a un usuario usando tu método del queryset.
    Gestión de Usuarios es exclusiva de SuperAdmin.
    """
    if not request.user.is_superuser:
        return Response({'error': 'Requiere rol SuperAdmin (is_superuser) para desactivar una cuenta'}, status=status.HTTP_403_FORBIDDEN)

    actualizado = FonoApp_Administracion.objects.eliminar_logico(rut)
    
    if actualizado:
        return Response({'mensaje': 'Usuario desactivado correctamente'}, status=status.HTTP_200_OK)
    
    return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def usuario_actualizar_password(request, rut):
    """
    Endpoint para cambiar la contraseña usando el método directo de tu queryset.
    Solo el dueño de la cuenta o un SuperAdmin pueden hacerlo; de lo contrario
    cualquier usuario autenticado podría secuestrar la cuenta de otro con solo
    conocer su RUT.
    """
    if request.user.rut != rut and not request.user.is_superuser:
        return Response(
            {'error': 'Solo puede cambiar su propia contraseña, salvo que sea SuperAdmin'},
            status=status.HTTP_403_FORBIDDEN,
        )

    nueva_password = request.data.get('password')

    if not nueva_password:
        return Response({'error': 'La nueva contraseña es obligatoria'}, status=status.HTTP_400_BAD_REQUEST)

    actualizado = FonoApp_Administracion.objects.actualizar_password(rut, nueva_password)
    
    if actualizado:
        return Response({'mensaje': 'Contraseña actualizada correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Usuario no encontrado o RUT incorrecto'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PATCH'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def usuario_editar_parcial(request, rut):
    """
    Endpoint para actualizar parcialmente los permisos, estado y contraseña
    de un usuario mediante su RUT.

    Reglas de autorización (modelo de 3 roles, ver usuarios_create):
    - Cambiar 'estado', 'is_staff' o 'is_superuser' (cualquier permiso) es
      Gestión de Usuarios y SIEMPRE requiere que quien hace la petición ya
      sea SuperAdmin (is_superuser), incluso sobre su propia cuenta (para que
      nadie pueda autoasignarse ni quitarse permisos).
    - Cambiar solo la propia 'password' no requiere ningún rol especial.
    - Editar la cuenta de OTRO usuario, en cualquier campo, requiere ser
      SuperAdmin.
    """
    estado = request.data.get('estado')
    is_staff = request.data.get('is_staff')
    is_superuser = request.data.get('is_superuser')
    password = request.data.get('password')

    quiere_cambiar_permisos = estado is not None or is_staff is not None or is_superuser is not None
    es_propia_cuenta = request.user.rut == rut

    if quiere_cambiar_permisos and not request.user.is_superuser:
        return Response(
            {'error': 'Requiere rol SuperAdmin (is_superuser) para modificar el estado o los permisos de una cuenta'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not es_propia_cuenta and not request.user.is_superuser:
        return Response({'error': 'Requiere rol SuperAdmin (is_superuser) para editar la cuenta de otro usuario'}, status=status.HTTP_403_FORBIDDEN)

    # Llamamos al método especializado que creamos en el queryset
    actualizado = FonoApp_Administracion.objects.editar_usuario_parcial(
        rut=rut,
        estado=estado,
        is_staff=is_staff,
        is_superuser=is_superuser,
        password=password
    )

    if actualizado:
        return Response({'mensaje': 'Usuario actualizado correctamente'}, status=status.HTTP_200_OK)
    
    return Response({'error': 'Usuario no encontrado o RUT incorrecto'}, status=status.HTTP_404_NOT_FOUND)

# ========================================
# BANNER
# ========================================

# -------------------------------------------------------------------------
# MÉTODO: GET
# USO: Lista todos los banners activos (Acceso público para el frontend)
# -------------------------------------------------------------------------
@api_view(['GET'])
@permission_classes([AllowAny])
def banner_listar(request):
    # Utilizamos el manager personalizado para traer activos y evitar el problema N+1 con las imágenes
    banners = FonoApp_Banner_Inicio.objects.activos().con_detalles()
    serializer = FonoApp_Banner_InicioSerializer(banners, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

# -------------------------------------------------------------------------
# MÉTODO: POST
# USO: Crea un nuevo banner con su imagen (Requiere Token JWT)
# -------------------------------------------------------------------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def banner_crear(request):
    # Pasamos el context={'request': request} para que el Serializer pueda extraer el usuario (request.user)
    serializer = FonoApp_Banner_InicioSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -------------------------------------------------------------------------
# MÉTODO: PUT / PATCH
# USO: Edita la información de un banner existente (Requiere Token JWT)
# -------------------------------------------------------------------------
@api_view(['PATCH', 'PUT'])
@permission_classes([IsAuthenticated])
def banner_editar(request, id_banner):
    try:
        banner = FonoApp_Banner_Inicio.objects.get(pk=id_banner, estado=True)
    except FonoApp_Banner_Inicio.DoesNotExist:
        return Response({'error': 'Banner no encontrado o inactivo'}, status=status.HTTP_404_NOT_FOUND)
    
    # partial=True permite actualizar solo los campos enviados en la petición (ej. cambiar solo el título)
    serializer = FonoApp_Banner_InicioSerializer(banner, data=request.data, partial=True, context={'request': request})
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'mensaje': 'Banner actualizado correctamente', 
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -------------------------------------------------------------------------
# MÉTODO: PUT / PATCH
# USO: Reemplaza la imagen de un banner existente (Requiere Token JWT)
# -------------------------------------------------------------------------
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def banner_imagen_actualizar(request, id_banner):
    # Un banner solo admite una (1) imagen, así que esta operación siempre reemplaza la existente
    nuevas_imagenes = request.FILES.getlist('imagenes_subidas')

    if not nuevas_imagenes:
        return Response({'error': 'Debe adjuntar una imagen'}, status=status.HTTP_400_BAD_REQUEST)

    if len(nuevas_imagenes) > 1:
        return Response({'error': 'Solo se permite adjuntar una (1) imagen por banner'}, status=status.HTTP_400_BAD_REQUEST)

    exito, mensaje = FonoApp_Banner_Inicio.objects.actualizar_imagen(id_banner, nuevas_imagenes[0])

    if exito:
        return Response({'mensaje': mensaje}, status=status.HTTP_200_OK)

    return Response({'error': mensaje}, status=status.HTTP_404_NOT_FOUND)

# -------------------------------------------------------------------------
# MÉTODO: DELETE
# USO: Realiza un borrado lógico del banner (Requiere Token JWT)
# -------------------------------------------------------------------------
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def banner_eliminar(request, id_banner):
    # Invocamos el método del QuerySet para hacer la baja lógica (estado = False)
    filas_actualizadas = FonoApp_Banner_Inicio.objects.eliminar_logico(id_banner=id_banner)
    
    if filas_actualizadas > 0:
        return Response({'mensaje': 'Banner eliminado correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Banner no encontrado'}, status=status.HTTP_404_NOT_FOUND)