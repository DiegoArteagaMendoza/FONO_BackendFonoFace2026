from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppFunciones.authentication import CustomJWTAuthentication
from .models import FonoApp_InfoGeneral
from .serializer import FonoApp_InfoGeneralSerializer

# ==========================================
# ENDPOINT PÚBLICO (Para el portal de clientes)
# ==========================================

@api_view(['GET'])
@permission_classes([AllowAny])
def info_publica_listar(request):
    """
    Retorna los textos activos. Puede filtrar por sección pasando el parámetro por la URL.
    Ejemplo: /api/info-general/publico/?seccion=inicio
    """
    seccion_param = request.query_params.get('seccion', None)
    
    if seccion_param:
        textos = FonoApp_InfoGeneral.objects.por_seccion(seccion_param)
    else:
        textos = FonoApp_InfoGeneral.objects.activos()
        
    serializer = FonoApp_InfoGeneralSerializer(textos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================================
# ENDPOINTS DE ADMINISTRACIÓN (Protegidos)
# ==========================================

@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def info_admin_listar(request):
    """Lista TODOS los textos, incluyendo los inactivos, para la tabla del administrador."""
    textos = FonoApp_InfoGeneral.objects.all()
    serializer = FonoApp_InfoGeneralSerializer(textos, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def info_crear(request):
    serializer = FonoApp_InfoGeneralSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PATCH', 'PUT'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def info_editar(request, id_info):
    try:
        texto = FonoApp_InfoGeneral.objects.get(pk=id_info, estado=True)
    except FonoApp_InfoGeneral.DoesNotExist:
        return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
    serializer = FonoApp_InfoGeneralSerializer(texto, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response({'mensaje': 'Información actualizada', 'data': serializer.data}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def info_eliminar(request, id_info):
    filas_actualizadas = FonoApp_InfoGeneral.objects.eliminar_logico(id_info)
    if filas_actualizadas > 0:
        return Response({'mensaje': 'Registro eliminado correctamente'}, status=status.HTTP_200_OK)
    return Response({'error': 'Registro no encontrado'}, status=status.HTTP_404_NOT_FOUND)