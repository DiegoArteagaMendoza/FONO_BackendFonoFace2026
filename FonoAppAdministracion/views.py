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
@permission_classes([AllowAny]) # Permite acceso inicial (registro) sin token
def usuarios_create(request):
    serializer = FonoApp_Serializer(data=request.data)
    if serializer.is_valid():
        serializer.save() # Esto dispara el create() del serializer que llama a crear_usuario()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated]) # <-- Maneja la validación de acceso automáticamente
def usuarios_list(request):
    # Utilizamos el filtro estándar ya que "activos()" no está definido en el queryset
    usuarios = FonoApp_Administracion.objects.filter(estado=True)
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
    """
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
    """
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
    """
    estado = request.data.get('estado')
    is_staff = request.data.get('is_staff')
    password = request.data.get('password')

    # Llamamos al método especializado que creamos en el queryset
    actualizado = FonoApp_Administracion.objects.editar_usuario_parcial(
        rut=rut,
        estado=estado,
        is_staff=is_staff,
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