from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from FonoAppCuidados.models import FonoApp_Cuidados
from FonoAppCuidados.serializer import FonoApp_CuidadosSerializer
from FonoAppFunciones.authentication import CustomJWTAuthentication

@api_view(['GET'])
@permission_classes([AllowAny])
def cuidados_listar(request):
    """Retorna la lista global de cuidados de salud vocal activos."""
    cuidados = FonoApp_Cuidados.objects.listar_todo()
    serializer = FonoApp_CuidadosSerializer(cuidados, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def cuidados_filtrar_publico(request, tipo_publico):
    """Filtra cuidados activos según el parámetro 'publico' enviado en la URL."""
    cuidados = FonoApp_Cuidados.objects.filtrar_por_publico(tipo_publico.upper())
    serializer = FonoApp_CuidadosSerializer(cuidados, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def cuidados_crear(request):
    """Registra una nueva guía de cuidado."""
    serializer = FonoApp_CuidadosSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT', 'PATCH'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def cuidado_editar(request, id_cuidado):
    """Edita campos específicos de una guía de cuidado activa."""
    datos_a_actualizar = {}
    campos_validos = ['publico', 'titulo', 'contenido', 'fuente']
    
    for campo in campos_validos:
        if campo in request.data:
            datos_a_actualizar[campo] = request.data[campo]
            
    if 'img' in request.FILES:
        datos_a_actualizar['img'] = request.FILES['img']
        
    if not datos_a_actualizar:
        return Response({'error': 'No se enviaron datos para actualizar'}, status=status.HTTP_400_BAD_REQUEST)
        
    actualizado = FonoApp_Cuidados.objects.editar_cuidado(id_cuidado, **datos_a_actualizar)
    if actualizado:
        return Response({'mensaje': 'Cuidado actualizado correctamente'}, status=status.HTTP_200_OK)
        
    return Response({'error': 'Cuidado no encontrado o inactivo'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@authentication_classes([CustomJWTAuthentication])
@permission_classes([IsAuthenticated])
def cuidado_eliminar(request, id_cuidado):
    """Ejecuta la baja lógica de un registro de cuidado."""
    actualizado = FonoApp_Cuidados.objects.eliminar_logico(id_cuidado)
    if actualizado:
        return Response({'mensaje': 'Cuidado eliminado correctamente'}, status=status.HTTP_200_OK)
    return Response({'error': 'Cuidado no encontrado o ya eliminado'}, status=status.HTTP_404_NOT_FOUND)