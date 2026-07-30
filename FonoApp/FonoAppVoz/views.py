from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppVoz.models import FonoApp_Voz
from FonoAppVoz.serializer import FonoApp_VozSerializer
from FonoAppFunciones.authentication import CustomJWTAuthentication

@api_view(['GET'])
@permission_classes([AllowAny])
def voz_listar(request):
    """Retorna la lista global de contenido informativo de voz activo."""
    voz = FonoApp_Voz.objects.listar_todo()
    serializer = FonoApp_VozSerializer(voz, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def voz_filtrar_categoria(request, tipo_categoria):
    """Filtra contenido de voz vigente según el parámetro 'categoria' enviado en la URL."""
    voz = FonoApp_Voz.objects.filtrar_por_categoria(tipo_categoria.upper())
    serializer = FonoApp_VozSerializer(voz, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def voz_crear(request):
    """Registra un nuevo contenido informativo sobre la voz."""
    serializer = FonoApp_VozSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT', 'PATCH'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def voz_editar(request, id_voz):
    """Edita campos específicos de un registro de voz activo."""
    datos_a_actualizar = {}
    campos_validos = ['categoria', 'titulo', 'contenido', 'fuente']

    for campo in campos_validos:
        if campo in request.data:
            datos_a_actualizar[campo] = request.data[campo]

    if 'img' in request.FILES:
        datos_a_actualizar['img'] = request.FILES['img']

    if not datos_a_actualizar:
        return Response({'error': 'No se enviaron datos para actualizar'}, status=status.HTTP_400_BAD_REQUEST)

    actualizado = FonoApp_Voz.objects.editar_voz(id_voz, **datos_a_actualizar)
    if actualizado:
        return Response({'mensaje': 'Contenido de voz actualizado correctamente'}, status=status.HTTP_200_OK)

    return Response({'error': 'Contenido de voz no encontrado o inactivo'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def voz_eliminar(request, id_voz):
    """Ejecuta la baja lógica de un registro de voz."""
    actualizado = FonoApp_Voz.objects.eliminar_logico(id_voz)
    if actualizado:
        return Response({'mensaje': 'Contenido de voz eliminado correctamente'}, status=status.HTTP_200_OK)
    return Response({'error': 'Contenido de voz no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)
